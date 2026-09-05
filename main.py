import os
import threading
import webbrowser
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout

from core import (
    detect,
    mcdir,
    fabric_installer,
    modrinth,
    error_logging,
    i18n,
    client_mod,
    msa_login,
)

error_logging.install()  # catch unhandled exceptions everywhere, from app start

KV = """
<Header@Label>:
    size_hint_y: None
    height: '36dp'
    bold: True
    color: 0.17, 0.24, 0.31, 1

<FlatButton@Button>:
    background_normal: ''
    background_color: 0.17, 0.24, 0.31, 1
    color: 1, 1, 1, 1
    size_hint_y: None
    height: '48dp'

<AccentButton@Button>:
    background_normal: ''
    background_color: 0.09, 0.74, 0.61, 1
    color: 1, 1, 1, 1
    size_hint_y: None
    height: '52dp'
    bold: True

RootLayout:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: 0.97, 0.97, 0.97, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        size_hint_y: None
        height: '52dp'
        padding: '8dp', '4dp'
        Image:
            # Bundled locally now -- img/banner.png, no network needed to show it.
            source: root.BANNER_PATH
            allow_stretch: True
        Widget:
        FlatButton:
            text: 'EN/VI'
            size_hint_x: None
            width: '90dp'
            on_release: root.toggle_language()

    TabbedPanel:
        do_default_tab: False
        tab_width: self.width / 4

        TabbedPanelItem:
            text: 'Overview'
            BoxLayout:
                orientation: 'vertical'
                padding: '12dp'
                spacing: '8dp'
                Header:
                    text: root.t('device')
                Label:
                    text: root.device_text
                    size_hint_y: None
                    height: '90dp'
                    halign: 'left'
                    valign: 'top'
                    text_size: self.width, None
                Header:
                    text: root.t('minecraft_folder')
                Label:
                    text: root.mcdir_text
                    size_hint_y: None
                    height: '80dp'
                    halign: 'left'
                    valign: 'top'
                    text_size: self.width, None
                FlatButton:
                    text: root.t('choose_folder')
                    on_release: root.pick_minecraft_dir()
                FlatButton:
                    text: root.t('create_missing')
                    on_release: root.build_missing_dirs()
                Widget:

        TabbedPanelItem:
            text: 'Settings'
            BoxLayout:
                orientation: 'vertical'
                padding: '12dp'
                spacing: '8dp'
                Header:
                    text: root.t('mc_version')
                TextInput:
                    id: mc_version_input
                    text: '1.21.1'
                    multiline: False
                    size_hint_y: None
                    height: '44dp'
                Header:
                    text: root.t('ram_allocated')
                TextInput:
                    id: ram_input
                    text: str(root.suggested_ram)
                    multiline: False
                    input_filter: 'int'
                    size_hint_y: None
                    height: '44dp'
                Label:
                    text: root.t('suggested_ram') + str(root.suggested_ram) + ' MB'
                    size_hint_y: None
                    height: '28dp'
                    color: 0.4, 0.4, 0.4, 1

                Header:
                    text: 'Microsoft account'
                Label:
                    text: root.account_text
                    size_hint_y: None
                    height: '32dp'
                TextInput:
                    id: azure_client_id_input
                    hint_text: 'Azure App client ID (see README)'
                    multiline: False
                    size_hint_y: None
                    height: '40dp'
                FlatButton:
                    text: root.t('login_microsoft')
                    on_release: root.start_login()
                TextInput:
                    id: redirected_url_input
                    hint_text: 'Paste the URL the browser landed on after sign-in'
                    multiline: False
                    size_hint_y: None
                    height: '40dp'
                FlatButton:
                    text: 'Complete login'
                    on_release: root.complete_login()
                Widget:

        TabbedPanelItem:
            text: 'Optimize FPS'
            BoxLayout:
                orientation: 'vertical'
                padding: '12dp'
                spacing: '8dp'
                Label:
                    text: root.t('optimize_fps_desc')
                    size_hint_y: None
                    height: '90dp'
                    halign: 'left'
                    valign: 'top'
                    text_size: self.width, None
                AccentButton:
                    text: root.t('optimize_now')
                    on_release: root.optimize_fps()
                Widget:

        TabbedPanelItem:
            text: 'Console'
            BoxLayout:
                orientation: 'vertical'
                padding: '8dp'
                spacing: '6dp'
                ScrollView:
                    Label:
                        id: console_label
                        text: root.console_text
                        size_hint_y: None
                        height: max(self.texture_size[1], 400)
                        text_size: self.width, None
                        halign: 'left'
                        valign: 'top'
                        color: 0.1, 0.9, 0.2, 1
                FlatButton:
                    text: root.t('save_log')
                    size_hint_y: None
                    height: '44dp'
                    on_release: root.save_console_log()

    BoxLayout:
        size_hint_y: None
        height: '56dp'
        padding: '6dp'
        spacing: '6dp'
        FlatButton:
            text: root.t('install_fabric')
            on_release: root.install_fabric()
        AccentButton:
            text: root.t('play_now')
            on_release: root.play_now()
"""


class RootLayout(BoxLayout):
    device_text = ""
    mcdir_text = ""
    console_text = "Ready.\n"
    suggested_ram = 1536
    account_text = ""

    # Bundled locally in the project now -- see img/banner.png.
    BANNER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "banner.png")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.translator = i18n.Translator()
        self._login_session = None
        self.account_text = self.t("not_logged_in")
        self.refresh_device_info()
        self.refresh_mcdir_info()

    # ---------- i18n ----------

    def t(self, key):
        return self.translator.t(key)

    def toggle_language(self):
        self.translator.set_lang("vi" if self.translator.lang == "en" else "en")
        self.refresh_mcdir_info()
        if self.account_text in (i18n.STRINGS["en"]["not_logged_in"], i18n.STRINGS["vi"]["not_logged_in"]):
            self.account_text = self.t("not_logged_in")
        # KV bindings only re-evaluate on property change, so nudge the ones
        # driven purely by translator state (device_text has no dependency
        # on language, mcdir_text/account_text do).
        self.property("mcdir_text").dispatch(self)
        self.property("account_text").dispatch(self)

    # ---------- console ----------

    def log(self, message):
        def _update(_dt):
            self.console_text += message + "\n"
            if "console_label" in self.ids:
                self.ids.console_label.text = self.console_text
        Clock.schedule_once(_update, 0)

    def save_console_log(self):
        log_dir = os.path.join(os.path.expanduser("~"), ".archclient_mobile", "console_logs")
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(log_dir, f"console_{ts}.txt")
        with open(path, "w") as f:
            f.write(self.console_text)
        self.log(f"Saved console log to {path}")

    # ---------- overview tab ----------

    def refresh_device_info(self):
        info = detect.device_summary()
        self.suggested_ram = info["suggested_ram_mb"]
        pojav_line = "installed" if info["pojav_installed"] else "NOT installed - install it from its own release first"
        self.device_text = (
            f"ABI: {info['abi']}\n"
            f"Total RAM: {info['total_ram_mb']} MB\n"
            f"PojavLauncher: {pojav_line}"
        )

    def refresh_mcdir_info(self):
        path = mcdir.get_minecraft_dir()
        if not path:
            self.mcdir_text = self.t("not_set")
            return
        report = mcdir.inspect(path)
        status = self.t("all_present") if not report["missing"] else self.t("missing_prefix") + ", ".join(report["missing"])
        self.mcdir_text = f"{path}\n{status}"

    def pick_minecraft_dir(self):
        # Stub file chooser for desktop testing -- swap for Android's Storage
        # Access Framework document picker (via plyer/jnius) in the real build,
        # see README.
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup

        chooser = FileChooserListView(path=os.path.expanduser("~"), dirselect=True)
        popup = Popup(title=self.t("choose_folder"), content=chooser, size_hint=(0.9, 0.9))

        def _chosen(_instance, selection, _touch=None):
            if selection:
                mcdir.set_minecraft_dir(selection[0])
                self.refresh_mcdir_info()
                popup.dismiss()

        chooser.bind(on_submit=_chosen)
        popup.open()

    def build_missing_dirs(self):
        path = mcdir.get_minecraft_dir()
        if not path:
            self.log(self.t("pick_folder_first"))
            return
        mcdir.build_missing(path, log=self.log)
        client_mod.sync_client_mod(path, log=self.log)
        self.refresh_mcdir_info()

    # ---------- background task helper ----------

    def _run_in_background(self, fn, *args):
        threading.Thread(target=fn, args=args, daemon=True).start()

    # ---------- fabric ----------

    def install_fabric(self):
        path = mcdir.get_minecraft_dir()
        if not path:
            self.log(self.t("pick_folder_first"))
            return
        mc_version = self.ids.mc_version_input.text.strip()
        self.log(f"Installing Fabric for Minecraft {mc_version}...")
        self._run_in_background(self._install_fabric_worker, path, mc_version)

    def _install_fabric_worker(self, path, mc_version):
        try:
            fabric_installer.install(path, mc_version, log=self.log)
        except Exception as e:
            self.log(f"Fabric install failed: {e}")

    # ---------- optimize fps ----------

    def optimize_fps(self):
        path = mcdir.get_minecraft_dir()
        if not path:
            self.log(self.t("pick_folder_first"))
            return
        mc_version = self.ids.mc_version_input.text.strip()
        self.log(f"Fetching optimized FPS mod set for {mc_version}...")
        self._run_in_background(self._optimize_fps_worker, path, mc_version)

    def _optimize_fps_worker(self, path, mc_version):
        try:
            modrinth.install_fps_pack(path, mc_version, log=self.log)
        except Exception as e:
            self.log(f"FPS pack install failed: {e}")

    # ---------- microsoft login ----------

    def start_login(self):
        client_id = self.ids.azure_client_id_input.text.strip()
        if not client_id:
            self.log("Enter your Azure App client ID first (see README for how to get one).")
            return
        self._login_session = msa_login.LoginSession(client_id)
        try:
            login_url = self._login_session.start()
        except Exception as e:
            self.log(f"Could not start login: {e}")
            return
        self.log("Opening browser to sign in with Microsoft...")
        try:
            if detect.ON_ANDROID:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                intent = Intent(Intent.ACTION_VIEW, Uri.parse(login_url))
                PythonActivity.mActivity.startActivity(intent)
            else:
                webbrowser.open(login_url)
        except Exception as e:
            self.log(f"Open this URL manually: {login_url} ({e})")

    def complete_login(self):
        if not self._login_session:
            self.log("Tap 'Log in with Microsoft' first.")
            return
        redirected_url = self.ids.redirected_url_input.text.strip()
        if not redirected_url:
            self.log("Paste the redirected URL from the browser first.")
            return
        try:
            account = self._login_session.complete(redirected_url)
        except Exception as e:
            self.log(f"Login failed: {e}")
            return
        self.account_text = self.t("logged_in_as") + account["name"]
        self.log(
            f"Signed in as {account['name']}. Note: this doesn't log you into "
            f"PojavLauncher automatically -- you still sign in inside Pojav once "
            f"to actually play online (see README)."
        )

    # ---------- play ----------

    def play_now(self):
        path = mcdir.get_minecraft_dir()
        if not path:
            self.log(self.t("pick_folder_first"))
            return
        if not detect.is_pojav_installed():
            self.log("PojavLauncher isn't installed on this device -- install it first, this app hands off to it.")
            return
        self.log("Handing off to PojavLauncher...")
        ok = detect.launch_pojav()
        if not ok:
            self.log("Could not launch PojavLauncher automatically. Open it manually.")


class ArchClientMobileApp(App):
    def build(self):
        return Builder.load_string(KV)


if __name__ == "__main__":
    ArchClientMobileApp().run()
