import os
import threading
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout

from core import (
    bedrock_detect,
    xbox_login,
    addon_manager,
    server_list,
    error_logging,
    i18n,
)

error_logging.install()  # catch unhandled exceptions everywhere, from app start

KV = """
<Header@Label>:
    size_hint_y: None
    height: '36dp'
    bold: True
    color: 0.17, 0.24, 0.31, 1

<Small@Label>:
    size_hint_y: None
    height: self.texture_size[1] + dp(8)
    halign: 'left'
    valign: 'top'
    text_size: self.width, None
    color: 0.35, 0.35, 0.35, 1

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

<ServerRow@BoxLayout>:
    size_hint_y: None
    height: '44dp'
    spacing: '6dp'

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
        tab_width: self.width / 5

        TabbedPanelItem:
            text: root.t('tab_overview')
            ScrollView:
                BoxLayout:
                    orientation: 'vertical'
                    padding: '12dp'
                    spacing: '8dp'
                    size_hint_y: None
                    height: self.minimum_height
                    Header:
                        text: root.t('device')
                    Label:
                        text: root.device_text
                        size_hint_y: None
                        height: '60dp'
                        halign: 'left'
                        valign: 'top'
                        text_size: self.width, None
                    Header:
                        text: root.t('bedrock_status')
                    Label:
                        text: root.bedrock_status_text
                        size_hint_y: None
                        height: '32dp'
                        halign: 'left'
                        valign: 'top'
                        text_size: self.width, None
                        color: (0.09, 0.6, 0.3, 1) if root.bedrock_installed else (0.75, 0.25, 0.2, 1)
                    AccentButton:
                        text: root.t('open_bedrock') if root.bedrock_installed else root.t('open_play_store')
                        on_release: root.open_bedrock_or_store()
                    Small:
                        text: root.t('what_this_does_not_do')

        TabbedPanelItem:
            text: root.t('tab_account')
            ScrollView:
                BoxLayout:
                    orientation: 'vertical'
                    padding: '12dp'
                    spacing: '8dp'
                    size_hint_y: None
                    height: self.minimum_height
                    Small:
                        text: root.t('account_intro')
                    TextInput:
                        id: client_id_input
                        hint_text: root.t('client_id_label')
                        multiline: False
                        size_hint_y: None
                        height: '44dp'
                    Label:
                        text: root.account_text
                        size_hint_y: None
                        height: '32dp'
                    FlatButton:
                        text: root.t('step1_open_browser')
                        on_release: root.start_login(client_id_input.text)
                    Small:
                        text: root.t('step2_paste_url')
                    TextInput:
                        id: redirected_url_input
                        hint_text: 'https://login.microsoftonline.com/common/oauth2/nativeclient?code=...'
                        multiline: False
                        size_hint_y: None
                        height: '44dp'
                    AccentButton:
                        text: root.t('step3_complete')
                        on_release: root.complete_login(redirected_url_input.text)

        TabbedPanelItem:
            text: root.t('tab_addons')
            ScrollView:
                BoxLayout:
                    orientation: 'vertical'
                    padding: '12dp'
                    spacing: '8dp'
                    size_hint_y: None
                    height: self.minimum_height
                    Small:
                        text: root.t('addons_intro')
                    TextInput:
                        id: addon_url_input
                        hint_text: root.t('addon_url_hint')
                        multiline: False
                        size_hint_y: None
                        height: '44dp'
                    AccentButton:
                        text: root.t('download_import')
                        on_release: root.download_and_import(addon_url_input.text)

        TabbedPanelItem:
            text: root.t('tab_servers')
            BoxLayout:
                orientation: 'vertical'
                padding: '12dp'
                spacing: '8dp'
                Small:
                    text: root.t('servers_intro')
                BoxLayout:
                    size_hint_y: None
                    height: '44dp'
                    spacing: '6dp'
                    TextInput:
                        id: server_name_input
                        hint_text: root.t('server_name')
                        multiline: False
                    TextInput:
                        id: server_addr_input
                        hint_text: root.t('server_address')
                        multiline: False
                FlatButton:
                    text: root.t('add_server')
                    size_hint_y: None
                    height: '40dp'
                    on_release: root.add_server(server_name_input.text, server_addr_input.text)
                ScrollView:
                    BoxLayout:
                        id: server_list_box
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: '4dp'

        TabbedPanelItem:
            text: root.t('tab_console')
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
"""


class RootLayout(BoxLayout):
    device_text = StringProperty("")
    bedrock_status_text = StringProperty("")
    bedrock_installed = BooleanProperty(False)
    console_text = StringProperty("Ready.\n")
    account_text = StringProperty("")

    BANNER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "banner.png")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.translator = i18n.Translator()
        self._login_session = None
        self.bedrock_installed = False
        self.account_text = self.t("not_logged_in")
        self.refresh_device_info()
        self.refresh_server_list()

    # ---------- i18n ----------

    def t(self, key):
        return self.translator.t(key)

    def toggle_language(self):
        self.translator.set_lang("vi" if self.translator.lang == "en" else "en")
        self.refresh_device_info()
        self.account_text = self.t("logged_in_as") + self._last_gamertag if getattr(self, "_last_gamertag", None) else self.t("not_logged_in")
        # force KV to re-read every root.t(...) binding
        for prop in ("device_text", "bedrock_status_text", "account_text", "console_text"):
            self.property(prop).dispatch(self)

    # ---------- console ----------

    def log(self, message):
        def _update(_dt):
            self.console_text += message + "\n"
            if "console_label" in self.ids:
                self.ids.console_label.text = self.console_text
        Clock.schedule_once(_update, 0)

    def save_console_log(self):
        log_dir = os.path.join(os.path.expanduser("~"), ".archclient_bedrock", "console_logs")
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(log_dir, f"console_{ts}.txt")
        with open(path, "w") as f:
            f.write(self.console_text)
        self.log(f"Log saved to {path}")

    # ---------- overview ----------

    def refresh_device_info(self):
        info = bedrock_detect.device_summary()
        self.bedrock_installed = info["bedrock_installed"]
        self.device_text = f"{self.t('device')}: {info['abi']}, {info['total_ram_mb']} MB RAM"
        self.bedrock_status_text = (
            self.t("bedrock_installed") if info["bedrock_installed"] else self.t("bedrock_missing")
        )

    def open_bedrock_or_store(self):
        if self.bedrock_installed:
            bedrock_detect.launch_bedrock()
        else:
            bedrock_detect.open_play_store()

    # ---------- account (Xbox Live profile) ----------

    def start_login(self, client_id):
        client_id = (client_id or "").strip()
        if not client_id:
            self.log("Enter your Azure App client ID first (see README).")
            return
        import webbrowser
        self._login_session = xbox_login.LoginSession(client_id)
        url = self._login_session.start()
        webbrowser.open(url)
        self.log("Opened the Microsoft sign-in page in your browser.")

    def complete_login(self, redirected_url):
        if not self._login_session:
            self.log("Tap 'Open sign-in page' first.")
            return
        redirected_url = (redirected_url or "").strip()
        if not redirected_url:
            self.log("Paste the URL the browser landed on after you signed in.")
            return

        def _worker():
            try:
                profile = self._login_session.complete(redirected_url)
                self._last_gamertag = profile["gamertag"]

                def _update(_dt):
                    self.account_text = self.t("logged_in_as") + profile["gamertag"]
                Clock.schedule_once(_update, 0)
                self.log(f"Signed in as {profile['gamertag']} (XUID {profile['xuid']})")
            except xbox_login.XboxLoginError as e:
                self.log(f"Sign-in failed: {e}")
            except Exception as e:
                self.log(f"Sign-in failed: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    # ---------- addons ----------

    def download_and_import(self, url):
        url = (url or "").strip()
        if not url:
            self.log("Paste an addon URL first.")
            return

        def _worker():
            try:
                addon_manager.download_and_import(url, log=self.log)
            except addon_manager.AddonError as e:
                self.log(f"Addon error: {e}")
            except Exception as e:
                self.log(f"Addon error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    # ---------- servers ----------

    def refresh_server_list(self):
        if "server_list_box" not in self.ids:
            return
        box = self.ids.server_list_box
        box.clear_widgets()
        servers = server_list.load_servers()
        for i, srv in enumerate(servers):
            row = BoxLayout(size_hint_y=None, height="44dp", spacing="6dp")
            from kivy.uix.label import Label
            from kivy.uix.button import Button
            row.add_widget(Label(text=f"{srv['name']}\n{srv['address']}", halign="left"))
            copy_btn = Button(text=self.t("copy"), size_hint_x=None, width="70dp")
            copy_btn.bind(on_release=lambda _b, addr=srv["address"]: self._copy_server(addr))
            remove_btn = Button(text=self.t("remove"), size_hint_x=None, width="80dp")
            remove_btn.bind(on_release=lambda _b, idx=i: self._remove_server(idx))
            row.add_widget(copy_btn)
            row.add_widget(remove_btn)
            box.add_widget(row)

    def add_server(self, name, address):
        name, address = (name or "").strip(), (address or "").strip()
        if not name or not address:
            self.log("Enter both a name and an address (host:port).")
            return
        server_list.add_server(name, address)
        self.refresh_server_list()
        self.log(f"Added server: {name} ({address})")

    def _remove_server(self, index):
        server_list.remove_server(index)
        self.refresh_server_list()

    def _copy_server(self, address):
        if server_list.copy_to_clipboard(address):
            self.log(f"Copied {address} to clipboard -- paste it into Minecraft's Add Server screen.")


class ArchClientBedrockApp(App):
    def build(self):
        self.title = i18n.Translator().t("app_title")
        return Builder.load_string(KV)


if __name__ == "__main__":
    ArchClientBedrockApp().run()
