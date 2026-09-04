#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fabric Launcher Pro - CachyOS / KDE Plasma
============================================
Launcher Minecraft Fabric gọn nhẹ, giao diện đẹp (ttkbootstrap, dark theme),
tối ưu FPS, đọc trực tiếp mods/resourcepacks/schematics/shaderpacks từ .minecraft.

Tự động nhận diện hệ điều hành (Windows 10/11, Ubuntu, Debian, Arch, các distro
dựa trên Arch/Debian) và tự cài các gói còn thiếu, đồng thời tự khởi tạo thư mục
.minecraft nếu chưa tồn tại.

Cài đặt thủ công (nếu cần):
    pip install minecraft-launcher-lib requests ttkbootstrap --break-system-packages

Chạy:
    python3 fabric_launcher_pro.py
"""

import os
import sys
import json
import shutil
import platform
import threading
import importlib
import subprocess
import urllib.request
import webbrowser
import traceback
import datetime
from pathlib import Path

# ==========================================================================
# BOOTSTRAP: nhận diện hệ điều hành + tự cài gói còn thiếu
# ==========================================================================

REQUIRED_PIP_PACKAGES = {
    # tên module python -> tên gói pip
    "ttkbootstrap": "ttkbootstrap",
    "minecraft_launcher_lib": "minecraft-launcher-lib",
    "requests": "requests",
    "PIL": "pillow",
}


def _bprint(msg):
    print(msg, flush=True)


def detect_os():
    """Nhận diện hệ điều hành và trình quản lý gói phù hợp.

    Hỗ trợ: Windows 10/11, Arch Linux + các distro dựa trên Arch
    (Manjaro, EndeavourOS, Garuda, CachyOS, ...), Debian/Ubuntu + các
    distro dựa trên Debian (Mint, Pop!_OS, Zorin, ...).
    """
    system = platform.system()  # 'Windows', 'Linux', 'Darwin'
    info = {"system": system, "distro_id": "", "distro_like": "",
            "pkg_manager": None, "pretty": system}

    if system == "Windows":
        build = 0
        try:
            build = sys.getwindowsversion().build
        except Exception:
            pass
        if build >= 22000:
            info["pretty"] = "Windows 11"
        elif build:
            info["pretty"] = "Windows 10"
        else:
            info["pretty"] = "Windows"
        info["pkg_manager"] = None  # trên Windows chỉ cần pip

    elif system == "Linux":
        os_release = {}
        try:
            for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    os_release[k] = v.strip().strip('"')
        except Exception:
            pass
        distro_id = os_release.get("ID", "").lower()
        distro_like = os_release.get("ID_LIKE", "").lower()
        info["distro_id"] = distro_id
        info["distro_like"] = distro_like
        info["pretty"] = os_release.get("PRETTY_NAME", "Linux")

        if distro_id == "arch" or "arch" in distro_like:
            info["pkg_manager"] = "pacman"
        elif distro_id in ("debian", "ubuntu") or "debian" in distro_like or "ubuntu" in distro_like:
            info["pkg_manager"] = "apt"
        elif shutil.which("pacman"):
            info["pkg_manager"] = "pacman"
        elif shutil.which("apt-get") or shutil.which("apt"):
            info["pkg_manager"] = "apt"

    else:
        info["pretty"] = system or "Không xác định"

    return info


def _run(cmd, use_sudo=False):
    if use_sudo and os.name != "nt":
        try:
            if os.geteuid() != 0:
                cmd = ["sudo"] + cmd
        except AttributeError:
            pass
    _bprint("  $ " + " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        _bprint(f"  ⚠ Lệnh thất bại: {e}")
        return False


def ensure_system_packages(osinfo):
    """Cài gói hệ thống cần thiết (chủ yếu là Tk cho tkinter) nếu thiếu, theo từng distro."""
    if osinfo["system"] != "Linux":
        return
    try:
        import tkinter  # noqa: F401
        return  # đã có sẵn, không cần làm gì
    except ImportError:
        pass

    pm = osinfo["pkg_manager"]
    _bprint("⏳ Thiếu tkinter (Tk) trên hệ thống — đang tự động cài đặt...")
    if pm == "pacman":
        _run(["pacman", "-Sy", "--needed", "--noconfirm", "tk"], use_sudo=True)
    elif pm == "apt":
        _run(["apt-get", "update"], use_sudo=True)
        _run(["apt-get", "install", "-y", "python3-tk"], use_sudo=True)
    else:
        _bprint("⚠ Không nhận diện được trình quản lý gói (pacman/apt).")
        _bprint("  Hãy tự cài thủ công: gói 'tk' (Arch) hoặc 'python3-tk' (Debian/Ubuntu).")


def _pip_install(packages):
    base = [sys.executable, "-m", "pip", "install"] + packages
    _bprint("  $ " + " ".join(base))
    result = subprocess.run(base, capture_output=True, text=True)
    if result.returncode == 0:
        return True
    combined = (result.stdout or "") + (result.stderr or "")
    if "externally-managed-environment" in combined or "break-system-packages" in combined:
        base2 = base + ["--break-system-packages"]
        _bprint("  ↳ Môi trường Python 'externally-managed' — thử lại với --break-system-packages")
        _bprint("  $ " + " ".join(base2))
        result2 = subprocess.run(base2, capture_output=True, text=True)
        if result2.returncode == 0:
            return True
        _bprint(result2.stdout)
        _bprint(result2.stderr)
        return False
    _bprint(combined)
    return False


def ensure_python_packages():
    """Kiểm tra & tự động cài các thư viện Python còn thiếu."""
    missing = []
    for mod_name, pip_name in REQUIRED_PIP_PACKAGES.items():
        try:
            importlib.import_module(mod_name)
        except ImportError:
            missing.append(pip_name)
    if not missing:
        return
    _bprint(f"⏳ Thiếu thư viện Python: {', '.join(missing)} — đang tự động cài đặt qua pip...")
    ok = _pip_install(missing)
    if ok:
        _bprint("✅ Đã cài xong thư viện Python.")
        importlib.invalidate_caches()
    else:
        _bprint("❌ Cài tự động thất bại. Hãy cài thủ công bằng lệnh:")
        _bprint(f"   {sys.executable} -m pip install {' '.join(missing)} --break-system-packages")
        sys.exit(1)


def bootstrap_environment():
    osinfo = detect_os()
    _bprint(f"🖥  Hệ điều hành phát hiện được: {osinfo['pretty']}")
    ensure_system_packages(osinfo)
    ensure_python_packages()
    return osinfo


OS_INFO = bootstrap_environment()

# ==========================================================================

import tkinter as tk
from tkinter import filedialog

try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *
    from ttkbootstrap import ScrolledText
except ImportError:
    import traceback
    print("Lỗi import ttkbootstrap — chi tiết:")
    traceback.print_exc()
    print("\nNếu dòng lỗi trên nhắc tới 'tkinter': cài gói hệ thống 'sudo pacman -S tk' (Arch) "
          "hoặc 'sudo apt install python3-tk' (Debian/Ubuntu).")
    print("Nếu nhắc tới thư viện khác (vd PIL/Pillow): pip install --force-reinstall pillow --break-system-packages")
    sys.exit(1)

try:
    import minecraft_launcher_lib as mll
except ImportError:
    mll = None

try:
    import requests
except ImportError:
    requests = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

APP_DIR = Path(__file__).resolve().parent
ICON_PATH = APP_DIR / "img" / "icon.png"
BANNER_PATH = APP_DIR / "img" / "banner.png"
WEBSITE_URL = "https://archclient.netlify.app"


def _load_image(path, size=None):
    if Image is None or not path.exists():
        return None
    try:
        img = Image.open(path).convert("RGBA")
        if size:
            img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def load_icon_image(size=None):
    """Tải img/icon.png, trả về ImageTk.PhotoImage hoặc None nếu thiếu file/thư viện."""
    return _load_image(ICON_PATH, size)


def load_banner_image(max_width=None):
    """Tải img/banner.png, tự co giãn theo max_width (giữ tỉ lệ) nếu truyền vào."""
    if Image is None or not BANNER_PATH.exists():
        return None
    try:
        img = Image.open(BANNER_PATH).convert("RGBA")
        if max_width and img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

# ==========================================================================
# I18N: đa ngôn ngữ (VI/EN, tự động phát hiện theo vị trí máy qua IP)
# ==========================================================================

LANG_STRINGS = {
    "vi": {
        "app_subtitle": "Minecraft {ver} · Fabric · Tối ưu FPS tối đa",
        "status_ready": "Sẵn sàng",
        "tab_overview": "  📊 Tổng quan  ",
        "tab_settings": "  ⚙️ Cài đặt  ",
        "tab_optimize": "  🚀 Tối ưu FPS  ",
        "tab_console": "  💻 Console  ",
        "tab_log": "  📜 Log  ",
        "mc_dir_label": "Thư mục .minecraft:",
        "btn_choose": "Chọn...",
        "btn_install_fabric": "⬇ Cài / Cập nhật Fabric",
        "btn_play": "▶  CHƠI NGAY",
        "btn_website": "🌐 Website",
        "btn_shortcut": "📌 Tạo shortcut Desktop",
        "splash_detect": "Đang xác định vị trí & ngôn ngữ...",
        "splash_load": "Đang tải cấu hình...",
    },
    "en": {
        "app_subtitle": "Minecraft {ver} · Fabric · Max FPS optimization",
        "status_ready": "Ready",
        "tab_overview": "  📊 Overview  ",
        "tab_settings": "  ⚙️ Settings  ",
        "tab_optimize": "  🚀 FPS Optimize  ",
        "tab_console": "  💻 Console  ",
        "tab_log": "  📜 Log  ",
        "mc_dir_label": ".minecraft folder:",
        "btn_choose": "Browse...",
        "btn_install_fabric": "⬇ Install / Update Fabric",
        "btn_play": "▶  PLAY",
        "btn_website": "🌐 Website",
        "btn_shortcut": "📌 Create Desktop shortcut",
        "splash_detect": "Detecting location & language...",
        "splash_load": "Loading configuration...",
    },
}


def detect_language():
    """Tự động chọn 'vi' nếu máy đang ở Việt Nam (qua IP), ngược lại 'en'.
    Không có mạng thì fallback theo locale hệ thống, cuối cùng fallback 'en'."""
    if requests is not None:
        for url in ("https://ipapi.co/json/", "https://ipwho.is/"):
            try:
                r = requests.get(url, timeout=4)
                r.raise_for_status()
                data = r.json()
                country = (data.get("country_code") or data.get("country") or "").upper()
                if country:
                    return "vi" if country == "VN" else "en"
            except Exception:
                continue
    try:
        import locale
        loc = locale.getdefaultlocale()[0] or ""
        if loc.lower().startswith("vi"):
            return "vi"
    except Exception:
        pass
    return "en"


# --------------------------------------------------------------------------
MC_VERSION = "1.21.11"
DEFAULT_MC_DIR = Path.home() / ".minecraft"
CONFIG_DIR = Path.home() / ".config" / "arch-client-launcher"
CONFIG_FILE = CONFIG_DIR / "config.json"
ERROR_LOG_DIR = CONFIG_DIR / "error_logs"


def write_error_log(context, exc):
    """Ghi traceback đầy đủ ra file .txt trong ~/.config/arch-client-launcher/error_logs/.
    Trả về đường dẫn file đã ghi (hoặc None nếu ghi thất bại)."""
    try:
        ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fp = ERROR_LOG_DIR / f"error_{ts}.txt"
        content = (
            f"Arch Client Launcher — Error Log\n"
            f"Thời gian: {datetime.datetime.now().isoformat()}\n"
            f"Ngữ cảnh: {context}\n"
            f"{'-' * 60}\n"
            f"{traceback.format_exc()}\n"
        )
        fp.write_text(content, encoding="utf-8")
        return fp
    except Exception:
        return None


def create_desktop_shortcut(log_func=_bprint):
    """Tự tạo shortcut khởi động nhanh, hỗ trợ cả 3 hệ điều hành:
    Linux -> file .desktop (menu ứng dụng + Desktop),
    Windows -> file .lnk trên Desktop (qua PowerShell/WScript.Shell),
    macOS -> file .command trên Desktop.
    """
    system = platform.system()
    script_path = str(APP_DIR / Path(__file__).name)
    workdir = str(APP_DIR)
    try:
        if system == "Linux":
            apps_dir = Path.home() / ".local" / "share" / "applications"
            apps_dir.mkdir(parents=True, exist_ok=True)
            desktop_file = apps_dir / "arch-client-launcher.desktop"
            icon_line = f"Icon={ICON_PATH}" if ICON_PATH.exists() else "Icon=applications-games"
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Arch Client Launcher\n"
                "Comment=Launcher Minecraft Fabric toi uu FPS\n"
                f'Exec="{sys.executable}" "{script_path}"\n'
                f"{icon_line}\n"
                "Terminal=false\n"
                "Categories=Game;\n"
                "StartupWMClass=ArchClientLauncher\n"
            )
            desktop_file.write_text(content, encoding="utf-8")
            os.chmod(desktop_file, 0o755)
            log_func(f"✅ Đã tạo shortcut ứng dụng: {desktop_file}")

            desk = Path.home() / "Desktop"
            if desk.exists():
                desk_file = desk / "arch-client-launcher.desktop"
                shutil.copy(desktop_file, desk_file)
                os.chmod(desk_file, 0o755)
                try:
                    subprocess.run(["gio", "set", str(desk_file), "metadata::trusted", "true"],
                                    check=False, capture_output=True)
                except Exception:
                    pass
                log_func(f"✅ Đã tạo shortcut trên Desktop: {desk_file}")
            return True

        elif system == "Windows":
            desk = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
            desk.mkdir(parents=True, exist_ok=True)
            shortcut_path = desk / "Arch Client Launcher.lnk"

            ico_path = APP_DIR / "img" / "icon.ico"
            if Image is not None and ICON_PATH.exists() and not ico_path.exists():
                try:
                    img = Image.open(ICON_PATH).convert("RGBA")
                    img.save(ico_path, format="ICO",
                              sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
                except Exception:
                    ico_path = None

            pyw = Path(sys.executable).with_name("pythonw.exe")
            python_exec = str(pyw) if pyw.exists() else sys.executable
            icon_target = str(ico_path) if ico_path and Path(ico_path).exists() else python_exec

            ps_script = (
                '$WshShell = New-Object -ComObject WScript.Shell\n'
                f'$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")\n'
                f'$Shortcut.TargetPath = "{python_exec}"\n'
                f'$Shortcut.Arguments = \'"{script_path}"\'\n'
                f'$Shortcut.WorkingDirectory = "{workdir}"\n'
                f'$Shortcut.IconLocation = "{icon_target}"\n'
                '$Shortcut.Save()\n'
            )
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                            check=True, capture_output=True)
            log_func(f"✅ Đã tạo shortcut trên Desktop: {shortcut_path}")
            return True

        elif system == "Darwin":
            desk = Path.home() / "Desktop"
            desk.mkdir(parents=True, exist_ok=True)
            cmd_path = desk / "Arch Client Launcher.command"
            content = f'#!/bin/bash\ncd "{workdir}"\n"{sys.executable}" "{script_path}"\n'
            cmd_path.write_text(content, encoding="utf-8")
            os.chmod(cmd_path, 0o755)
            log_func(f"✅ Đã tạo shortcut trên Desktop: {cmd_path}")
            return True

        else:
            log_func("⚠ Không nhận diện được hệ điều hành để tạo shortcut.")
            return False
    except Exception as e:
        write_error_log("Tạo desktop shortcut", e)
        log_func(f"❌ Lỗi khi tạo shortcut: {e}")
        return False

OPTIMIZATION_MODS = {
    "sodium":       "Render engine siêu nhanh — bắt buộc cho FPS cao",
    "lithium":      "Tối ưu logic game, giảm tick lag",
    "starlight":    "Tối ưu ánh sáng, giảm lag chunk",
    "ferrite-core": "Giảm RAM sử dụng",
    "krypton":      "Tối ưu mạng, giảm lag khi chơi server",
    "lazydfu":      "Giảm thời gian khởi động game",
    "iris":         "Hỗ trợ shader, tương thích Sodium",
}

OPTIMIZED_OPTIONS = {
    "maxFps": "260", "renderDistance": "8", "simulationDistance": "6",
    "particles": "1", "ao": "1", "graphicsMode": "0", "clouds": "0",
    "biomeBlendRadius": "0", "entityShadows": "false", "vsync": "false",
    "guiScale": "2", "mipmapLevels": "0", "fboEnable": "true", "enableVsync": "false",
}

CATEGORIES = [
    ("mods", {".jar"}, "🧩", "Mods"),
    ("resourcepacks", {".zip"}, "🎨", "Resource Packs"),
    ("shaderpacks", {".zip"}, "✨", "Shaderpacks"),
    ("schematics", {".litematic", ".schem", ".nbt", ".schematic"}, "🧱", "Schematics"),
]


def default_config():
    return {
        "mc_dir": str(DEFAULT_MC_DIR), "java_path": "java", "ram_mb": 3072,
        "username": "Player", "azure_client_id": "", "shortcut_created": False,
    }


def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            cfg = default_config()
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
            return cfg
        except Exception:
            pass
    return default_config()


def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_minecraft_dir(mc_dir: Path) -> bool:
    """Tự động khởi tạo cấu trúc thư mục .minecraft cơ bản nếu chưa tồn tại.

    Trả về True nếu thư mục .minecraft là mới được tạo (lần đầu chạy).
    """
    first_time = not mc_dir.exists()
    mc_dir.mkdir(parents=True, exist_ok=True)
    subdirs = [
        "mods", "resourcepacks", "shaderpacks", "schematics",
        "saves", "screenshots", "config", "logs", "crash-reports",
    ]
    for d in subdirs:
        (mc_dir / d).mkdir(parents=True, exist_ok=True)
    return first_time


def _snapshot_mc_files(mc_dir: Path):
    """Trả về tập hợp đường dẫn tương đối các file trong versions/libraries/assets,
    dùng để so sánh trước/sau khi tải nhằm biết đã bù được bao nhiêu file còn thiếu."""
    snap = set()
    for sub in ("versions", "libraries", "assets"):
        p = mc_dir / sub
        if p.exists():
            for fp in p.rglob("*"):
                if fp.is_file():
                    snap.add(str(fp.relative_to(mc_dir)))
    return snap


# --------------------------------------------------------------------------
class SplashScreen(tb.Window):
    """Màn hình chờ khi khởi động, giống launcher thương mại thật."""

    def __init__(self):
        super().__init__(themename="cosmo")
        self.overrideredirect(True)
        w, h = 460, 380
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(bg="#ffffff")

        self._icon_full = load_icon_image()
        if self._icon_full:
            self.iconphoto(True, self._icon_full)

        outer = tb.Frame(self, bootstyle="light")
        outer.pack(fill="both", expand=True)

        self._logo_img = load_icon_image(size=(72, 72))
        if self._logo_img:
            tb.Label(outer, image=self._logo_img, bootstyle="inverse-light").pack(pady=(24, 0))
        else:
            tb.Label(outer, text="⚡", font=("", 40), bootstyle="primary-inverse-light").pack(pady=(24, 0))
        tb.Label(outer, text="ARCH CLIENT LAUNCHER", font=("", 16, "bold"),
                  bootstyle="primary-inverse-light").pack(pady=(4, 2))
        tb.Label(outer, text=f"Minecraft {MC_VERSION} · Fabric", font=("", 9),
                  bootstyle="secondary-inverse-light").pack()

        self._banner_img = load_banner_image(max_width=340)
        if self._banner_img:
            tb.Label(outer, image=self._banner_img, bootstyle="inverse-light").pack(pady=(10, 0))

        self.status_lbl = tb.Label(outer, text="Đang khởi động...", font=("", 9),
                                     bootstyle="secondary-inverse-light")
        self.status_lbl.pack(pady=(16, 6))

        self.bar = tb.Progressbar(outer, bootstyle="info-striped",
                                    mode="indeterminate", length=340)
        self.bar.pack(pady=(0, 16))
        self.bar.start(12)

    def set_status(self, text):
        self.status_lbl.config(text=text)
        self.update_idletasks()


class App(tb.Window):
    def __init__(self, lang="vi"):
        super().__init__(themename="cosmo")
        self.lang = lang
        self.LANG = LANG_STRINGS[lang]
        self.title("⚡ Arch Client Launcher — Minecraft " + MC_VERSION)
        self.geometry("880x640")
        self.minsize(760, 560)

        self._icon_full = load_icon_image()
        if self._icon_full:
            self.iconphoto(True, self._icon_full)

        self.cfg = load_config()
        self.mc_dir = Path(self.cfg["mc_dir"])
        self.access_token = None
        self.uuid = None
        self.game_proc = None

        mc_dir_created = ensure_minecraft_dir(self.mc_dir)

        if not self.cfg.get("shortcut_created"):
            threading.Thread(target=self._first_run_create_shortcut, daemon=True).start()

        self._build_header()
        self._build_body()
        self._build_footer()

        self.refresh_all()

        self.log(f"🖥 Hệ điều hành: {OS_INFO['pretty']}")
        if mc_dir_created:
            self.log(f"📁 Chưa có .minecraft — đã tự động tạo tại: {self.mc_dir}")
            self.log("   (kèm các thư mục con: mods, resourcepacks, shaderpacks, schematics, saves, ...)")
        if mll is None:
            self.log("⚠ Thiếu 'minecraft-launcher-lib' — pip install minecraft-launcher-lib --break-system-packages")
        if requests is None:
            self.log("⚠ Thiếu 'requests' — pip install requests --break-system-packages")

    # ---------------------------------------------------------------- header
    def _build_header(self):
        header = tb.Frame(self, bootstyle="primary", padding=18)
        header.pack(fill="x")

        left = tb.Frame(header, bootstyle="primary")
        left.pack(side="left")
        title_row = tb.Frame(left, bootstyle="primary")
        title_row.pack(anchor="w")
        self._header_logo = load_icon_image(size=(28, 28))
        if self._header_logo:
            tb.Label(title_row, image=self._header_logo, bootstyle="inverse-primary").pack(
                side="left", padx=(0, 8))
            tb.Label(title_row, text="ARCH CLIENT LAUNCHER", font=("", 20, "bold"),
                      bootstyle="inverse-primary").pack(side="left")
        else:
            tb.Label(title_row, text="⚡ ARCH CLIENT LAUNCHER", font=("", 20, "bold"),
                      bootstyle="inverse-primary").pack(side="left")
        tb.Label(left, text=self.LANG["app_subtitle"].format(ver=MC_VERSION),
                  font=("", 10), bootstyle="inverse-primary").pack(anchor="w")

        right = tb.Frame(header, bootstyle="primary")
        right.pack(side="right")
        self.status_badge = tb.Label(right, text=f"● {self.LANG['status_ready']}",
                                      bootstyle="success-inverse-primary",
                                      font=("", 10, "bold"))
        self.status_badge.pack(anchor="e")

    # ------------------------------------------------------------------ body
    def _build_body(self):
        self.nb = tb.Notebook(self, bootstyle="primary")
        self.nb.pack(fill="both", expand=True, padx=14, pady=(10, 4))

        self.tab_overview = tb.Frame(self.nb, padding=14)
        self.tab_settings = tb.Frame(self.nb, padding=14)
        self.tab_optimize = tb.Frame(self.nb, padding=14)
        self.tab_console = tb.Frame(self.nb, padding=10)
        self.tab_log = tb.Frame(self.nb, padding=10)

        self.nb.add(self.tab_overview, text=self.LANG["tab_overview"])
        self.nb.add(self.tab_settings, text=self.LANG["tab_settings"])
        self.nb.add(self.tab_optimize, text=self.LANG["tab_optimize"])
        self.nb.add(self.tab_console, text=self.LANG["tab_console"])
        self.nb.add(self.tab_log, text=self.LANG["tab_log"])

        self._build_overview_tab()
        self._build_settings_tab()
        self._build_optimize_tab()
        self._build_console_tab()
        self._build_log_tab()

    # --------------------------------------------------------------- footer
    def _build_footer(self):
        bar = tb.Frame(self, padding=(14, 8))
        bar.pack(fill="x")

        tb.Button(bar, text=self.LANG["btn_install_fabric"], bootstyle="info-outline",
                   command=self.install_fabric_thread).pack(side="left")

        tb.Button(bar, text=self.LANG["btn_website"], bootstyle="link",
                   command=self.open_website).pack(side="left", padx=(10, 0))

        self.play_btn = tb.Button(bar, text=self.LANG["btn_play"], bootstyle="success",
                                    width=20, command=self.launch_game_thread)
        self.play_btn.pack(side="right", ipady=6)

    def open_website(self):
        webbrowser.open(WEBSITE_URL)

    def _first_run_create_shortcut(self):
        ok = create_desktop_shortcut(self.log)
        self.cfg["shortcut_created"] = True
        save_config(self.cfg)
        if ok:
            self.log("📌 Đã tự động tạo shortcut Desktop cho lần chạy đầu tiên.")

    def create_shortcut_thread(self):
        threading.Thread(target=lambda: create_desktop_shortcut(self.log), daemon=True).start()

    # ---------------------------------------------------------- overview tab
    def _build_overview_tab(self):
        f = self.tab_overview

        self._overview_banner = load_banner_image(max_width=760)
        if self._overview_banner:
            tb.Label(f, image=self._overview_banner).pack(anchor="w", pady=(0, 12))

        dirbar = tb.Frame(f)
        dirbar.pack(fill="x", pady=(0, 12))
        tb.Label(dirbar, text=self.LANG["mc_dir_label"], font=("", 9, "bold")).pack(side="left")
        self.dir_var = tk.StringVar(value=str(self.mc_dir))
        tb.Entry(dirbar, textvariable=self.dir_var).pack(
            side="left", fill="x", expand=True, padx=8)
        tb.Button(dirbar, text=self.LANG["btn_choose"], bootstyle="secondary-outline",
                   command=self.choose_dir).pack(side="left", padx=2)
        tb.Button(dirbar, text="⟳", bootstyle="secondary-outline", width=3,
                   command=self.refresh_all).pack(side="left")

        # Cards
        self.card_frame = tb.Frame(f)
        self.card_frame.pack(fill="x", pady=(0, 14))
        self.card_labels = {}
        styles = ["info", "success", "warning", "danger"]
        for i, (key, exts, icon, label) in enumerate(CATEGORIES):
            card = tb.Frame(self.card_frame, bootstyle=f"{styles[i % 4]}", padding=14)
            card.grid(row=0, column=i, sticky="nsew", padx=6)
            self.card_frame.columnconfigure(i, weight=1)
            tb.Label(card, text=icon, font=("", 22), bootstyle=f"inverse-{styles[i % 4]}").pack()
            count_lbl = tb.Label(card, text="0", font=("", 22, "bold"),
                                   bootstyle=f"inverse-{styles[i % 4]}")
            count_lbl.pack()
            tb.Label(card, text=label, font=("", 9), bootstyle=f"inverse-{styles[i % 4]}").pack()
            self.card_labels[key] = count_lbl

        # File list
        list_wrap = tb.Labelframe(f, text="Chi tiết file", padding=8, bootstyle="secondary")
        list_wrap.pack(fill="both", expand=True)

        cols = ("loai", "ten")
        self.tree = tb.Treeview(list_wrap, columns=cols, show="headings",
                                  bootstyle="primary", height=12)
        self.tree.heading("loai", text="Loại")
        self.tree.heading("ten", text="Tên file")
        self.tree.column("loai", width=140, anchor="w")
        self.tree.column("ten", width=560, anchor="w")
        self.tree.pack(fill="both", expand=True, side="left")

        sb = tb.Scrollbar(list_wrap, orient="vertical", command=self.tree.yview, bootstyle="round-primary")
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

    def choose_dir(self):
        d = filedialog.askdirectory(initialdir=str(self.mc_dir))
        if d:
            self.mc_dir = Path(d)
            created = ensure_minecraft_dir(self.mc_dir)
            self.dir_var.set(str(self.mc_dir))
            self.cfg["mc_dir"] = str(self.mc_dir)
            save_config(self.cfg)
            self.refresh_all()
            if created:
                self.log(f"📁 Đã tự động khởi tạo thư mục .minecraft mới tại: {self.mc_dir}")

    def refresh_all(self):
        if hasattr(self, "dir_var"):
            self.mc_dir = Path(self.dir_var.get())
        self.tree.delete(*self.tree.get_children())
        totals = {}
        for key, exts, icon, label in CATEGORIES:
            p = self.mc_dir / key
            items = []
            if p.exists():
                for item in p.iterdir():
                    if item.is_dir():
                        items.append(item.name + "/")
                    elif item.suffix.lower() in exts:
                        items.append(item.name)
            items.sort()
            totals[key] = len(items)
            self.card_labels[key].config(text=str(len(items)))
            for it in items:
                self.tree.insert("", "end", values=(f"{icon} {label}", it))
        installed = set()
        mods_dir = self.mc_dir / "mods"
        if mods_dir.exists():
            installed = {f.name.split("-")[0].lower() for f in mods_dir.glob("*.jar")}
        self._installed_mods = installed

    # --------------------------------------------------------- settings tab
    def _build_settings_tab(self):
        f = self.tab_settings
        pad = {"pady": 8}

        tb.Label(f, text="Java", font=("", 11, "bold")).grid(row=0, column=0, sticky="w", **pad)
        self.java_var = tk.StringVar(value=self.cfg["java_path"])
        tb.Entry(f, textvariable=self.java_var, width=45).grid(
            row=0, column=1, sticky="w", **pad)
        tb.Button(f, text="Chọn file...", bootstyle="secondary-outline",
                   command=self.choose_java).grid(row=0, column=2, sticky="w", padx=6)

        tb.Label(f, text="RAM cấp cho game", font=("", 11, "bold")).grid(
            row=1, column=0, sticky="w", **pad)
        ram_wrap = tb.Frame(f)
        ram_wrap.grid(row=1, column=1, columnspan=2, sticky="w", **pad)
        self.ram_var = tk.IntVar(value=self.cfg["ram_mb"])
        self.ram_scale = tb.Scale(ram_wrap, from_=1024, to=16384, orient="horizontal",
                                    variable=self.ram_var, length=320, bootstyle="info",
                                    command=self._on_ram_change)
        self.ram_scale.pack(side="left")
        self.ram_lbl = tb.Label(ram_wrap, text=f"{self.ram_var.get()} MB", width=10,
                                  font=("", 10, "bold"))
        self.ram_lbl.pack(side="left", padx=10)

        tb.Label(f, text="Tên người chơi", font=("", 11, "bold")).grid(
            row=2, column=0, sticky="w", **pad)
        self.user_var = tk.StringVar(value=self.cfg["username"])
        tb.Entry(f, textvariable=self.user_var, width=25).grid(
            row=2, column=1, sticky="w", **pad)

        tb.Label(f, text="Azure client_id\n(login Microsoft)", font=("", 11, "bold")).grid(
            row=3, column=0, sticky="w", **pad)
        self.client_id_var = tk.StringVar(value=self.cfg["azure_client_id"])
        tb.Entry(f, textvariable=self.client_id_var, width=45).grid(
            row=3, column=1, sticky="w", **pad)
        tb.Button(f, text="🔑 Login Microsoft", bootstyle="warning-outline",
                   command=self.login_microsoft_thread).grid(row=3, column=2, sticky="w", padx=6)

        tb.Button(f, text="💾 Lưu cài đặt", bootstyle="success",
                   command=self.save_settings).grid(row=4, column=1, sticky="w", pady=18)

        tb.Button(f, text=self.LANG["btn_shortcut"], bootstyle="primary-outline",
                   command=self.create_shortcut_thread).grid(row=4, column=2, sticky="w", pady=18)

        note = ("Để trống Azure client_id → chạy chế độ offline/dev "
                "(chơi singleplayer hoặc server online-mode=false).")
        tb.Label(f, text=note, bootstyle="secondary", wraplength=520,
                  justify="left").grid(row=5, column=0, columnspan=3, sticky="w", pady=6)

    def _on_ram_change(self, val):
        self.ram_lbl.config(text=f"{int(float(val))} MB")

    def choose_java(self):
        p = filedialog.askopenfilename(title="Chọn java executable")
        if p:
            self.java_var.set(p)

    def save_settings(self):
        self.cfg.update({
            "java_path": self.java_var.get(), "ram_mb": int(self.ram_var.get()),
            "username": self.user_var.get(), "azure_client_id": self.client_id_var.get(),
            "mc_dir": str(self.mc_dir),
        })
        save_config(self.cfg)
        self.log("✅ Đã lưu cài đặt.")

    # -------------------------------------------------------- optimize tab
    def _build_optimize_tab(self):
        f = self.tab_optimize
        tb.Label(f, text="🚀 Tối ưu FPS / hiệu năng", font=("", 14, "bold")).pack(anchor="w")
        tb.Label(f, text="Ghi options.txt tối ưu + tải mod tối ưu còn thiếu từ Modrinth",
                  bootstyle="secondary").pack(anchor="w", pady=(0, 12))

        self.mod_vars = {}
        box = tb.Labelframe(f, text="Mod tối ưu hoá", padding=10, bootstyle="secondary")
        box.pack(fill="x", pady=(0, 14))
        for slug, desc in OPTIMIZATION_MODS.items():
            var = tk.BooleanVar(value=True)
            self.mod_vars[slug] = var
            row = tb.Frame(box)
            row.pack(fill="x", pady=2)
            tb.Checkbutton(row, variable=var, bootstyle="success-round-toggle").pack(side="left")
            tb.Label(row, text=f"  {slug}", font=("", 10, "bold")).pack(side="left")
            tb.Label(row, text=f" — {desc}", bootstyle="secondary").pack(side="left")

        self.opt_progress = tb.Progressbar(f, mode="indeterminate", bootstyle="success-striped")
        self.opt_progress.pack(fill="x", pady=(4, 10))

        tb.Button(f, text="🚀 Áp dụng tối ưu FPS ngay", bootstyle="success",
                   command=self.apply_optimization_thread).pack(anchor="w")

    # ---------------------------------------------------------- console tab
    def _build_console_tab(self):
        f = self.tab_console
        tb.Label(f, text="💻 Console — theo dõi & gửi lệnh khi game đang chạy",
                  bootstyle="secondary").pack(anchor="w", pady=(0, 6))

        self.console_widget = ScrolledText(f, autohide=True, height=16)
        self.console_widget.pack(fill="both", expand=True)
        self.console_widget.text.configure(bg="#0d1117", fg="#58a6ff", insertbackground="#58a6ff")

        cmd_bar = tb.Frame(f)
        cmd_bar.pack(fill="x", pady=(8, 0))
        self.console_cmd_var = tk.StringVar()
        entry = tb.Entry(cmd_bar, textvariable=self.console_cmd_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda e: self.send_console_command())
        tb.Button(cmd_bar, text="Gửi ▶", bootstyle="primary",
                   command=self.send_console_command).pack(side="left", padx=(6, 0))

    def send_console_command(self):
        cmd = self.console_cmd_var.get().strip()
        if not cmd:
            return
        self.console_cmd_var.set("")
        if self.game_proc and self.game_proc.poll() is None and self.game_proc.stdin:
            try:
                self.game_proc.stdin.write(cmd + "\n")
                self.game_proc.stdin.flush()
                self.log(f"» {cmd}")
            except Exception as e:
                self.log(f"⚠ Không gửi được lệnh tới game: {e}")
        else:
            self.log("⚠ Game chưa chạy — không có tiến trình để gửi lệnh.")

    # -------------------------------------------------------------- log tab
    def _build_log_tab(self):
        self.log_widget = ScrolledText(self.tab_log, autohide=True, height=18)
        self.log_widget.pack(fill="both", expand=True)
        self.log_widget.text.configure(bg="#0d1117", fg="#3fb950", insertbackground="#3fb950")

    def log(self, msg):
        def _do():
            line = str(msg) + "\n"
            self.log_widget.text.insert("end", line)
            self.log_widget.text.see("end")
            if hasattr(self, "console_widget"):
                self.console_widget.text.insert("end", line)
                self.console_widget.text.see("end")
        self.after(0, _do)

    def set_status(self, text, style="success-inverse-primary"):
        self.after(0, lambda: self.status_badge.config(text=f"● {text}", bootstyle=style))

    # ------------------------------------------------------- Fabric install
    def install_fabric_thread(self):
        if mll is None:
            self.log("❌ Cần cài minecraft-launcher-lib")
            return
        threading.Thread(target=self._install_fabric, daemon=True).start()

    def _install_fabric(self):
        try:
            self.set_status("Đang cài Fabric...", "warning-inverse-primary")
            self.mc_dir.mkdir(parents=True, exist_ok=True)

            before = _snapshot_mc_files(self.mc_dir)
            jar_path = self.mc_dir / "versions" / MC_VERSION / f"{MC_VERSION}.jar"
            if not jar_path.exists():
                if before:
                    self.log(f"🔍 Phát hiện thiếu file gốc Minecraft {MC_VERSION} — đang tải bù...")
                else:
                    self.log(f"📦 Chưa có file Minecraft nào — đang tự tạo & tải toàn bộ từ đầu...")
                vanilla_cb = {
                    "setStatus": lambda text: self.log(f"  {text}"),
                    "setProgress": lambda value: None,
                    "setMax": lambda value: None,
                }
                mll.install.install_minecraft_version(MC_VERSION, str(self.mc_dir), callback=vanilla_cb)
            else:
                self.log(f"✅ Đã có đủ file gốc Minecraft {MC_VERSION}.")

            self.log(f"⏳ Đang cài Fabric Loader cho Minecraft {MC_VERSION}...")
            callback = {
                "setStatus": lambda text: self.log(f"  {text}"),
                "setProgress": lambda value: None,
                "setMax": lambda value: None,
            }
            mll.fabric.install_fabric(MC_VERSION, str(self.mc_dir), callback=callback)

            after = _snapshot_mc_files(self.mc_dir)
            new_files = after - before
            if new_files:
                self.log(f"📥 Đã tải mới {len(new_files)} file còn thiếu (versions/libraries/assets).")
            self.log("✅ Cài Fabric thành công!")
            self.set_status("Sẵn sàng")
        except Exception as e:
            write_error_log("Cài Fabric", e)
            self.log(f"❌ Lỗi khi cài Fabric: {e}")
            self.set_status("Lỗi", "danger-inverse-primary")

    # ------------------------------------------------------- Microsoft auth
    def login_microsoft_thread(self):
        if mll is None:
            self.log("❌ Cần cài minecraft-launcher-lib")
            return
        client_id = self.client_id_var.get().strip()
        if not client_id:
            self.log("⚠ Điền Azure client_id trước khi login Microsoft.")
            return
        threading.Thread(target=self._login_microsoft, args=(client_id,), daemon=True).start()

    def _login_microsoft(self, client_id):
        try:
            redirect_uri = "https://login.microsoftonline.com/consumers/oauth2/nativeclient"
            login_url, state, code_verifier = mll.microsoft_account.get_secure_login_data(
                client_id, redirect_uri)
            self.log("👉 Mở trình duyệt và đăng nhập tại:")
            self.log(login_url)
            self.log("Sau khi đăng nhập, copy URL redirect cuối cùng, dán vào terminal đang chạy launcher.")
            redirect_url = input("Dán URL redirect vào đây rồi Enter: ").strip()
            auth_code = mll.microsoft_account.parse_auth_code_url(redirect_url, state)
            token = mll.microsoft_account.complete_login(
                client_id, None, redirect_uri, auth_code, code_verifier)
            self.access_token = token["access_token"]
            self.uuid = token["id"]
            self.user_var.set(token["name"])
            self.log(f"✅ Đăng nhập thành công: {token['name']}")
        except Exception as e:
            write_error_log("Đăng nhập Microsoft", e)
            self.log(f"❌ Lỗi đăng nhập Microsoft: {e}")

    # ------------------------------------------------------------- Launch
    def launch_game_thread(self):
        if mll is None:
            self.log("❌ Cần cài minecraft-launcher-lib")
            return
        threading.Thread(target=self._launch_game, daemon=True).start()

    def _launch_game(self):
        try:
            self.set_status("Đang khởi chạy...", "warning-inverse-primary")
            versions = [
                v["id"] for v in mll.utils.get_installed_versions(str(self.mc_dir))
                if v["id"].startswith("fabric-loader") and MC_VERSION in v["id"]
            ]
            if not versions:
                self.log("⚠ Chưa cài Fabric cho phiên bản này. Bấm 'Cài / Cập nhật Fabric' trước.")
                self.set_status("Chưa cài Fabric", "danger-inverse-primary")
                return
            version_id = versions[0]
            self.log(f"🚀 Chuẩn bị chạy: {version_id}")

            ram = int(self.ram_var.get())
            jvm_args = [
                f"-Xms{ram}M", f"-Xmx{ram}M",
                "-XX:+UseG1GC", "-XX:+ParallelRefProcEnabled",
                "-XX:MaxGCPauseMillis=200", "-XX:+UnlockExperimentalVMOptions",
                "-XX:+DisableExplicitGC", "-XX:+AlwaysPreTouch",
                "-XX:G1NewSizePercent=30", "-XX:G1MaxNewSizePercent=40",
                "-XX:G1HeapRegionSize=8M", "-XX:G1ReservePercent=20",
                "-XX:G1HeapWastePercent=5", "-XX:G1MixedGCCountTarget=4",
                "-XX:InitiatingHeapOccupancyPercent=15",
                "-XX:G1MixedGCLiveThresholdPercent=90",
                "-XX:G1RSetUpdatingPauseTimePercent=5",
                "-XX:SurvivorRatio=32", "-XX:+PerfDisableSharedMem",
                "-XX:MaxTenuringThreshold=1",
            ]
            options = {
                "username": self.user_var.get() or "Player",
                "uuid": self.uuid or "00000000-0000-0000-0000-000000000000",
                "token": self.access_token or "0",
                "jvmArguments": jvm_args,
                "launcherName": "FabricLauncherPro",
                "launcherVersion": "2.0",
            }
            command = mll.command.get_minecraft_command(version_id, str(self.mc_dir), options)
            java_path = self.java_var.get().strip() or "java"
            command[0] = java_path

            self.log("▶ Đang khởi chạy Minecraft...")
            proc = subprocess.Popen(command, cwd=str(self.mc_dir),
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, bufsize=1)
            self.game_proc = proc
            self.set_status("Đang chơi", "success-inverse-primary")

            def stream_output():
                tail_lines = []
                for line in proc.stdout:
                    self.log(line.rstrip())
                    tail_lines.append(line.rstrip())
                    if len(tail_lines) > 200:
                        tail_lines.pop(0)
                ret = proc.wait()
                self.game_proc = None
                if ret != 0:
                    self.log(f"❌ Minecraft thoát với mã lỗi {ret}.")
                    self.set_status("Crash", "danger-inverse-primary")
                    try:
                        ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        fp = ERROR_LOG_DIR / f"error_{ts}_Minecraft_crash_(mã_lỗi_{ret}).txt"
                        content = (
                            "=" * 70 + "\n"
                            "ARCH CLIENT — BÁO CÁO LỖI\n" + "=" * 70 + "\n"
                            f"Thời gian     : {datetime.datetime.now().isoformat(sep=' ', timespec='seconds')}\n"
                            f"Ngữ cảnh      : Minecraft crash (mã lỗi {ret})\n"
                            f"Hệ điều hành  : {OS_INFO['pretty']}\n"
                            f"Python        : {platform.python_version()}\n"
                            + "-" * 70 + "\n"
                            "--- 200 dòng cuối của game log ---\n"
                            + "\n".join(tail_lines) + "\n"
                            + "-" * 70 + "\n"
                            "Traceback đầy đủ:\n(không có traceback — lỗi được báo cáo thủ công)\n"
                            + "=" * 70 + "\n"
                        )
                        fp.write_text(content, encoding="utf-8")
                        self.log(f"📝 Đã ghi log lỗi ra: {fp}")
                    except Exception as log_err:
                        self.log(f"⚠ Không ghi được file lỗi: {log_err}")
                else:
                    self.log("ℹ Minecraft đã đóng.")
                    self.set_status("Sẵn sàng")

            threading.Thread(target=stream_output, daemon=True).start()
        except Exception as e:
            write_error_log("Khởi chạy Minecraft", e)
            self.log(f"❌ Lỗi khi khởi chạy: {e}")
            self.set_status("Lỗi", "danger-inverse-primary")

    # -------------------------------------------------------- Optimization
    def apply_optimization_thread(self):
        threading.Thread(target=self._apply_optimization, daemon=True).start()

    def _write_optimized_options(self):
        opt_path = self.mc_dir / "options.txt"
        existing = {}
        if opt_path.exists():
            for line in opt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    existing[k] = v
        existing.update(OPTIMIZED_OPTIONS)
        opt_path.write_text("\n".join(f"{k}:{v}" for k, v in existing.items()) + "\n",
                             encoding="utf-8")
        self.log(f"✅ Đã cập nhật {opt_path} với thiết lập tối ưu FPS.")

    def _download_modrinth_mod(self, slug):
        if requests is None:
            self.log("⚠ Thiếu 'requests', bỏ qua tải mod tự động.")
            return
        mods_dir = self.mc_dir / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        if any(slug in fp.name.lower() for fp in mods_dir.glob("*.jar")):
            self.log(f"  ⏭ {slug}: đã có, bỏ qua.")
            return
        try:
            api = (f"https://api.modrinth.com/v2/project/{slug}/version"
                   f'?loaders=["fabric"]&game_versions=["{MC_VERSION}"]')
            r = requests.get(api, timeout=15)
            r.raise_for_status()
            versions = r.json()
            if not versions:
                self.log(f"  ⚠ {slug}: không có bản cho {MC_VERSION} + Fabric.")
                return
            file_info = versions[0]["files"][0]
            dest = mods_dir / file_info["filename"]
            self.log(f"  ⬇ Đang tải {slug}...")
            urllib.request.urlretrieve(file_info["url"], dest)
            self.log(f"  ✅ Đã tải: {file_info['filename']}")
        except Exception as e:
            write_error_log(f"Tải mod tối ưu ({slug})", e)
            self.log(f"  ❌ Lỗi tải {slug}: {e}")

    def _apply_optimization(self):
        self.after(0, self.opt_progress.start)
        self.set_status("Đang tối ưu...", "warning-inverse-primary")
        self.log("🚀 Bắt đầu tối ưu FPS...")
        self._write_optimized_options()
        for slug, var in self.mod_vars.items():
            if var.get():
                self._download_modrinth_mod(slug)
        self.log("🎉 Hoàn tất tối ưu! Khởi động lại game để áp dụng.")
        self.after(0, self.opt_progress.stop)
        self.set_status("Sẵn sàng")
        self.after(0, self.refresh_all)


def run_with_splash():
    splash = SplashScreen()

    def worker():
        splash.after(0, lambda: splash.set_status(LANG_STRINGS["vi"]["splash_detect"]))
        lang = detect_language()
        strings = LANG_STRINGS[lang]
        splash.after(0, lambda: splash.set_status(strings["splash_load"]))
        import time
        time.sleep(0.3)
        splash.after(0, lambda: finish(lang))

    def finish(lang):
        splash.bar.stop()
        splash.destroy()
        App(lang=lang).mainloop()

    threading.Thread(target=worker, daemon=True).start()
    splash.mainloop()


if __name__ == "__main__":
    run_with_splash()
