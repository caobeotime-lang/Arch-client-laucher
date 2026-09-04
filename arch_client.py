#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Arch Client - launcher Minecraft Fabric (ttkbootstrap, theme flatly)
# Tự nhận diện OS + cài gói thiếu, tự tạo .minecraft, log lỗi ra file txt.
#
# Cài thủ công nếu cần:
#   pip install minecraft-launcher-lib requests ttkbootstrap --break-system-packages

import os
import re
import sys
import json
import time
import shutil
import tarfile
import zipfile
import platform
import threading
import traceback
import importlib
import subprocess
import urllib.request
import webbrowser
from pathlib import Path
from datetime import datetime

# ==========================================================================
# BOOTSTRAP: nhận diện hệ điều hành + tự cài gói còn thiếu
# ==========================================================================

REQUIRED_PIP_PACKAGES = {
    # tên module python -> tên gói pip (bắt buộc — thiếu thì launcher không chạy được)
    "ttkbootstrap": "ttkbootstrap",
    "minecraft_launcher_lib": "minecraft-launcher-lib",
    "requests": "requests",
    "PIL": "pillow",
}

OPTIONAL_PIP_PACKAGES = {
    # tính năng phụ (Discord Rich Presence) — thiếu vẫn chạy launcher bình thường
    "pypresence": "pypresence",
}


def _bprint(msg):
    print(msg, flush=True)


# ==========================================================================
# GHI LOG LỖI RA FILE .txt (mọi lỗi trong launcher đều được lưu lại)
# ==========================================================================

ERROR_LOG_DIR = Path.home() / ".config" / "arch-client-launcher" / "error_logs"


def write_error_log(context, exc=None, extra_text=None):
    """Ghi lỗi ra file .txt kèm timestamp + traceback đầy đủ.

    context: mô tả ngắn nơi xảy ra lỗi (vd 'Cài Fabric', 'Khởi chạy game')
    exc: exception object (nếu có) — nếu None sẽ tự lấy traceback hiện tại
    extra_text: text bổ sung muốn ghi kèm (không bắt buộc)
    Trả về đường dẫn file log đã ghi, hoặc None nếu ghi thất bại.
    """
    try:
        ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_ctx = "".join(c if c.isalnum() else "_" for c in context)[:40] or "loi"
        log_path = ERROR_LOG_DIR / f"error_{ts}_{safe_ctx}.txt"

        tb_text = traceback.format_exc()
        if tb_text.strip() == "NoneType: None":
            tb_text = "(không có traceback — lỗi được báo cáo thủ công)"

        lines = [
            "=" * 70,
            "ARCH CLIENT — BÁO CÁO LỖI",
            "=" * 70,
            f"Thời gian     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Ngữ cảnh      : {context}",
            f"Hệ điều hành  : {OS_INFO['pretty'] if 'OS_INFO' in globals() else platform.platform()}",
            f"Python        : {sys.version.split()[0]}",
        ]
        if exc is not None:
            lines.append(f"Loại lỗi      : {type(exc).__name__}")
            lines.append(f"Nội dung      : {exc}")
        if extra_text:
            lines.append("-" * 70)
            lines.append(str(extra_text))
        lines.append("-" * 70)
        lines.append("Traceback đầy đủ:")
        lines.append(tb_text)
        lines.append("=" * 70)

        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _bprint(f"📝 Đã ghi file lỗi: {log_path}")
        return log_path
    except Exception as log_err:
        # Ghi log lỗi thất bại thì cũng không được làm crash thêm launcher
        _bprint(f"⚠ Không thể ghi file lỗi: {log_err}")
        return None


def _thread_excepthook(args):
    """Bắt mọi lỗi chưa được xử lý xảy ra trong các thread nền (vd cài Fabric,
    tải mod, khởi chạy game) và ghi lại thành file .txt thay vì làm treo im lặng."""
    context = f"Thread nền: {args.thread.name if args.thread else 'unknown'}"
    write_error_log(context, exc=args.exc_value)


def _main_excepthook(exc_type, exc_value, exc_tb):
    """Bắt mọi lỗi chưa được xử lý ở luồng chính (GUI) và ghi lại thành file .txt."""
    write_error_log("Luồng chính (GUI)", exc=exc_value)
    traceback.print_exception(exc_type, exc_value, exc_tb)


sys.excepthook = _main_excepthook
try:
    threading.excepthook = _thread_excepthook
except AttributeError:
    pass  # Python < 3.8 không có threading.excepthook


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
    if missing:
        _bprint(f"⏳ Thiếu thư viện Python: {', '.join(missing)} — đang tự động cài đặt qua pip...")
        ok = _pip_install(missing)
        if ok:
            _bprint("✅ Đã cài xong thư viện Python.")
            importlib.invalidate_caches()
        else:
            _bprint("❌ Cài tự động thất bại. Hãy cài thủ công bằng lệnh:")
            _bprint(f"   {sys.executable} -m pip install {' '.join(missing)} --break-system-packages")
            write_error_log("Bootstrap — cài thư viện Python thất bại",
                             extra_text=f"Các gói còn thiếu: {', '.join(missing)}")
            sys.exit(1)

    # Gói phụ (Discord Rich Presence...) — cố gắng cài nhưng KHÔNG chặn launcher
    # nếu thất bại (không có mạng, v.v.) vì đây chỉ là tính năng cộng thêm.
    opt_missing = []
    for mod_name, pip_name in OPTIONAL_PIP_PACKAGES.items():
        try:
            importlib.import_module(mod_name)
        except ImportError:
            opt_missing.append(pip_name)
    if opt_missing:
        _bprint(f"⏳ Thư viện phụ còn thiếu: {', '.join(opt_missing)} — thử cài (không bắt buộc)...")
        if _pip_install(opt_missing):
            _bprint("✅ Đã cài xong thư viện phụ.")
            importlib.invalidate_caches()
        else:
            _bprint("ℹ Không cài được thư viện phụ — Discord Rich Presence sẽ bị tắt, "
                     "launcher vẫn chạy bình thường.")


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


def _tk_report_callback_exception(self, exc_type, exc_value, exc_tb):
    """Mọi lỗi xảy ra bên trong các callback của Tkinter (nút bấm, sự kiện,
    .after(...)) đều đi qua đây thay vì sys.excepthook — ghi lại thành .txt
    để launcher không bao giờ 'lặng lẽ' bỏ qua lỗi."""
    write_error_log("Callback giao diện (Tkinter)", exc=exc_value)
    traceback.print_exception(exc_type, exc_value, exc_tb)


tk.Tk.report_callback_exception = _tk_report_callback_exception

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

try:
    from pypresence import Presence as DiscordPresence
except ImportError:
    DiscordPresence = None

DISCORD_CLIENT_ID = "1545310964331843584"

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
        "tab_log": "  🖥️ Console  ",
        "mc_dir_label": "Thư mục .minecraft:",
        "btn_choose": "Chọn...",
        "btn_install_fabric": "⬇ Cài / Cập nhật Fabric",
        "btn_play": "▶  CHƠI NGAY",
        "btn_website": "🌐 Website",
        "btn_clear_console": "🗑 Xoá console",
        "btn_save_console": "💾 Lưu log ra .txt",
        "splash_detect": "Đang xác định vị trí & ngôn ngữ...",
        "splash_load": "Đang tải cấu hình...",
    },
    "en": {
        "app_subtitle": "Minecraft {ver} · Fabric · Max FPS optimization",
        "status_ready": "Ready",
        "tab_overview": "  📊 Overview  ",
        "tab_settings": "  ⚙️ Settings  ",
        "tab_optimize": "  🚀 FPS Optimize  ",
        "tab_log": "  🖥️ Console  ",
        "mc_dir_label": ".minecraft folder:",
        "btn_choose": "Browse...",
        "btn_install_fabric": "⬇ Install / Update Fabric",
        "btn_clear_console": "🗑 Clear console",
        "btn_save_console": "💾 Save log as .txt",
        "btn_play": "▶  PLAY",
        "btn_website": "🌐 Website",
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

# Minecraft 1.20.5+ (bao gồm 1.21.x) yêu cầu tối thiểu Java 21 để chạy.
JAVA_MAJOR_REQUIRED = 21
JRE_DIR = CONFIG_DIR / "jre"

OPTIMIZATION_MODS = {
    "sodium":            "Render engine siêu nhanh — bắt buộc cho FPS cao",
    "lithium":           "Tối ưu logic game, giảm tick lag",
    "starlight":         "Tối ưu ánh sáng, giảm lag chunk",
    "ferrite-core":       "Giảm RAM sử dụng",
    "krypton":           "Tối ưu mạng, giảm lag khi chơi server",
    "lazydfu":           "Giảm thời gian khởi động game",
    "iris":              "Hỗ trợ shader, tương thích Sodium",
    "modernfix":         "Giảm RAM + tăng tốc thời gian khởi động",
    "entityculling":     "Bỏ qua render entity ngoài tầm nhìn — tăng FPS mạnh",
    "immediatelyfast":   "Tối ưu vẽ UI/immediate rendering, tăng FPS thêm",
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
        "username": "Player", "azure_client_id": "",
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


REQUIRED_MC_SUBDIRS = [
    "mods", "resourcepacks", "shaderpacks", "schematics",
    "saves", "screenshots", "config", "logs", "crash-reports", "versions",
]


def ensure_minecraft_dir(mc_dir: Path) -> dict:
    """Tự động nhận diện & khởi tạo cấu trúc thư mục .minecraft.

    - Nếu thư mục .minecraft chưa hề tồn tại: tự tạo TẤT CẢ các thư mục con cần thiết.
    - Nếu đã tồn tại nhưng thiếu một vài thư mục con (vd người dùng mới cài lại
      game, hoặc thư mục bị xoá nhầm): chỉ tạo bù đúng những cái đang thiếu.

    Trả về dict:
        {"first_time": bool, "created": [tên các thư mục con vừa được tạo]}
    """
    first_time = not mc_dir.exists()
    mc_dir.mkdir(parents=True, exist_ok=True)

    created = []
    for d in REQUIRED_MC_SUBDIRS:
        sub = mc_dir / d
        if not sub.exists():
            sub.mkdir(parents=True, exist_ok=True)
            created.append(d)

    # options.txt không bắt buộc nhưng nếu thiếu hoàn toàn (máy mới),
    # ghi sẵn 1 file rỗng để game không lỗi khi đọc lần đầu.
    opt_path = mc_dir / "options.txt"
    if first_time and not opt_path.exists():
        try:
            opt_path.write_text("", encoding="utf-8")
        except Exception:
            pass

    return {"first_time": first_time, "created": created}


# ==========================================================================
# JAVA (OpenJDK): tự nhận diện thiếu Java trên mọi OS và tự động cài
# ==========================================================================

def find_bundled_java() -> "Path | None":
    """Tìm file java đã được launcher tự tải & giải nén trước đó (nếu có)."""
    if not JRE_DIR.exists():
        return None
    exe_name = "java.exe" if platform.system() == "Windows" else "java"
    matches = [p for p in JRE_DIR.rglob(exe_name) if p.parent.name == "bin"]
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def get_java_version(java_exe) -> "int | None":
    """Chạy `java -version` và trả về số phiên bản chính (vd 21), None nếu lỗi."""
    try:
        result = subprocess.run([str(java_exe), "-version"], capture_output=True,
                                  text=True, timeout=10)
        output = (result.stdout or "") + (result.stderr or "")
        m = re.search(r'version\s+"(\d+)', output)
        if not m:
            m = re.search(r'(\d+)\.\d+\.\d+', output)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def resolve_java_path(configured: str) -> "str | None":
    """Quy đổi giá trị người dùng nhập (đường dẫn tuyệt đối hoặc chỉ 'java')
    thành đường dẫn thực thi được, hoặc None nếu không tìm thấy."""
    configured = (configured or "").strip() or "java"
    if os.path.isabs(configured) and Path(configured).exists():
        return configured
    found = shutil.which(configured)
    return found


def adoptium_download_info(java_major=JAVA_MAJOR_REQUIRED):
    """Trả về (url, ext) cho bản OpenJDK (Eclipse Temurin) phù hợp OS/kiến trúc
    hiện tại, hoặc (None, None) nếu OS không được hỗ trợ tự động cài."""
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Windows":
        os_name, ext = "windows", "zip"
    elif system == "Linux":
        os_name, ext = "linux", "tar.gz"
    else:
        return None, None

    if machine in ("amd64", "x86_64"):
        arch = "x64"
    elif machine in ("arm64", "aarch64"):
        arch = "aarch64"
    else:
        return None, None

    url = (f"https://api.adoptium.net/v3/binary/latest/{java_major}/ga/"
           f"{os_name}/{arch}/jdk/hotspot/normal/eclipse?project=jdk")
    return url, ext


def download_file(url, dest_path: Path, log_fn=_bprint):
    """Tải file với log tiến độ theo mốc 10%. Ném exception nếu lỗi mạng."""
    with requests.get(url, stream=True, timeout=60, allow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        downloaded = 0
        last_pct = -100
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=262144):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = int(downloaded * 100 / total)
                    if pct - last_pct >= 10:
                        mb_done = downloaded // (1024 * 1024)
                        mb_total = total // (1024 * 1024)
                        log_fn(f"  ⬇ {pct}% ({mb_done}MB / {mb_total}MB)")
                        last_pct = pct
    return dest_path


def extract_archive(archive_path: Path, dest_dir: Path, ext: str):
    dest_dir.mkdir(parents=True, exist_ok=True)
    if ext == "zip":
        with zipfile.ZipFile(archive_path) as z:
            z.extractall(dest_dir)
    else:
        with tarfile.open(archive_path) as t:
            t.extractall(dest_dir)


def install_java_via_pkg_manager(osinfo, java_major=JAVA_MAJOR_REQUIRED) -> bool:
    """Thử cài OpenJDK qua trình quản lý gói của distro Linux trước (nhanh
    hơn và tích hợp hệ thống tốt hơn bản tải rời). Trả về True nếu có vẻ
    thành công (không đảm bảo đúng version — hàm gọi sẽ tự kiểm tra lại)."""
    pm = osinfo.get("pkg_manager")
    if pm == "pacman":
        return _run(["pacman", "-Sy", "--needed", "--noconfirm", "jdk-openjdk"], use_sudo=True)
    elif pm == "apt":
        _run(["apt-get", "update"], use_sudo=True)
        ok = _run(["apt-get", "install", "-y", f"openjdk-{java_major}-jdk"], use_sudo=True)
        if not ok:
            ok = _run(["apt-get", "install", "-y", "default-jdk"], use_sudo=True)
        return ok
    return False



    """Màn hình chờ khi khởi động, giống launcher thương mại thật."""

    def __init__(self):
        super().__init__(themename="flatly")
        self.overrideredirect(True)
        w, h = 460, 380
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(bg="#2f7cf6")

        self._icon_full = load_icon_image()
        if self._icon_full:
            self.iconphoto(True, self._icon_full)

        outer = tb.Frame(self, bootstyle="primary")
        outer.pack(fill="both", expand=True)

        self._logo_img = load_icon_image(size=(72, 72))
        if self._logo_img:
            tb.Label(outer, image=self._logo_img, bootstyle="inverse-primary").pack(pady=(24, 0))
        else:
            tb.Label(outer, text="⚡", font=("", 40), bootstyle="inverse-primary").pack(pady=(24, 0))
        tb.Label(outer, text="ARCH CLIENT", font=("", 16, "bold"),
                  bootstyle="inverse-primary").pack(pady=(4, 2))
        tb.Label(outer, text=f"Minecraft {MC_VERSION} · Fabric", font=("", 9),
                  bootstyle="inverse-primary").pack()

        self._banner_img = load_banner_image(max_width=340)
        if self._banner_img:
            tb.Label(outer, image=self._banner_img, bootstyle="inverse-primary").pack(pady=(10, 0))

        self.status_lbl = tb.Label(outer, text="Đang khởi động...", font=("", 9),
                                     bootstyle="secondary-inverse-primary")
        self.status_lbl.pack(pady=(16, 6))

        self.bar = tb.Progressbar(outer, bootstyle="success-striped",
                                    mode="indeterminate", length=340)
        self.bar.pack(pady=(0, 16))
        self.bar.start(12)

    def set_status(self, text):
        self.status_lbl.config(text=text)
        self.update_idletasks()


class App(tb.Window):
    def __init__(self, lang="vi"):
        super().__init__(themename="flatly")
        self.lang = lang
        self.LANG = LANG_STRINGS[lang]
        self.title("⚡ Arch Client — Minecraft " + MC_VERSION)
        self.geometry("880x640")
        self.minsize(760, 560)

        self._icon_full = load_icon_image()
        if self._icon_full:
            self.iconphoto(True, self._icon_full)

        self.cfg = load_config()
        self.mc_dir = Path(self.cfg["mc_dir"])
        self.access_token = None
        self.uuid = None

        self.discord_rpc = None
        self.discord_start_time = int(time.time())

        mc_dir_result = ensure_minecraft_dir(self.mc_dir)

        self._build_header()
        self._build_footer()
        self._build_body()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.refresh_all()

        self.log(f"🖥 Hệ điều hành: {OS_INFO['pretty']}")
        if mc_dir_result["first_time"]:
            self.log(f"📁 Chưa có .minecraft — đã tự động tạo mới hoàn toàn tại: {self.mc_dir}")
            self.log(f"   (đã tạo {len(mc_dir_result['created'])} thư mục con: "
                      f"{', '.join(mc_dir_result['created'])})")
        elif mc_dir_result["created"]:
            self.log(f"🔍 Đã nhận diện .minecraft có sẵn nhưng thiếu thư mục con — đã tạo bù: "
                      f"{', '.join(mc_dir_result['created'])}")
        else:
            self.log("✅ Cấu trúc thư mục .minecraft đầy đủ, không thiếu gì.")
        if mll is None:
            self.log("⚠ Thiếu 'minecraft-launcher-lib' — pip install minecraft-launcher-lib --break-system-packages")
        if requests is None:
            self.log("⚠ Thiếu 'requests' — pip install requests --break-system-packages")

        # Tự động kiểm tra & cài Java nếu thiếu/quá cũ — chạy nền, không chặn UI.
        self.after(200, self.check_java_startup)

        # Discord Rich Presence — hiện đang làm gì / tải gì ngay trên Discord.
        self.after(300, self._init_discord_rpc)

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
            tb.Label(title_row, text="ARCH CLIENT", font=("", 20, "bold"),
                      bootstyle="inverse-primary").pack(side="left")
        else:
            tb.Label(title_row, text="⚡ ARCH CLIENT", font=("", 20, "bold"),
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
        self.tab_log = tb.Frame(self.nb, padding=10)

        self.nb.add(self.tab_overview, text=self.LANG["tab_overview"])
        self.nb.add(self.tab_settings, text=self.LANG["tab_settings"])
        self.nb.add(self.tab_optimize, text=self.LANG["tab_optimize"])
        self.nb.add(self.tab_log, text=self.LANG["tab_log"])

        self._build_overview_tab()
        self._build_settings_tab()
        self._build_optimize_tab()
        self._build_log_tab()

        self._discord_tab_states = {
            str(self.tab_overview): "Đang xem: Tổng quan",
            str(self.tab_settings): "Đang xem: Cài đặt",
            str(self.tab_optimize): "Đang xem: Tối ưu FPS",
            str(self.tab_log): "Đang xem: Console",
        }
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    # --------------------------------------------------------------- footer
    def _build_footer(self):
        bar = tb.Frame(self, padding=(14, 10))
        bar.pack(side="bottom", fill="x")

        tb.Separator(self, bootstyle="secondary").pack(side="bottom", fill="x")

        left = tb.Frame(bar)
        left.pack(side="left")

        tb.Button(left, text=self.LANG["btn_install_fabric"], bootstyle="info-outline",
                   command=self.install_fabric_thread).pack(side="left", ipady=4)

        tb.Button(left, text=self.LANG["btn_website"], bootstyle="primary-outline",
                   command=self.open_website).pack(side="left", padx=(10, 0), ipady=4)

        self.play_btn = tb.Button(bar, text=self.LANG["btn_play"], bootstyle="success",
                                    width=20, command=self.launch_game_thread)
        self.play_btn.pack(side="right", ipady=6)

    def open_website(self):
        webbrowser.open(WEBSITE_URL)

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
        tb.Entry(dirbar, textvariable=self.dir_var, bootstyle="primary").pack(
            side="left", fill="x", expand=True, padx=8)
        tb.Button(dirbar, text=self.LANG["btn_choose"], bootstyle="secondary-outline",
                   command=self.choose_dir).pack(side="left", padx=2)
        tb.Button(dirbar, text="⟳", bootstyle="secondary-outline", width=3,
                   command=self.refresh_all).pack(side="left")

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
            result = ensure_minecraft_dir(self.mc_dir)
            self.dir_var.set(str(self.mc_dir))
            self.cfg["mc_dir"] = str(self.mc_dir)
            save_config(self.cfg)
            self.refresh_all()
            if result["first_time"]:
                self.log(f"📁 Đã tự động khởi tạo thư mục .minecraft mới tại: {self.mc_dir}")
            elif result["created"]:
                self.log(f"🔍 Đã tạo bù thư mục con còn thiếu: {', '.join(result['created'])}")

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
        tb.Entry(f, textvariable=self.java_var, width=45, bootstyle="primary").grid(
            row=0, column=1, sticky="w", **pad)
        tb.Button(f, text="Chọn file...", bootstyle="secondary-outline",
                   command=self.choose_java).grid(row=0, column=2, sticky="w", padx=6)

        java_row = tb.Frame(f)
        java_row.grid(row=1, column=1, columnspan=2, sticky="w", pady=(0, 6))
        self.java_status_lbl = tb.Label(java_row, text="☕ Chưa kiểm tra Java",
                                          bootstyle="secondary", font=("", 9))
        self.java_status_lbl.pack(side="left")
        tb.Button(java_row, text="⬇ Kiểm tra / Cài Java tự động", bootstyle="info-outline",
                   command=self.install_java_thread).pack(side="left", padx=(12, 0))

        tb.Label(f, text="RAM cấp cho game", font=("", 11, "bold")).grid(
            row=2, column=0, sticky="w", **pad)
        ram_wrap = tb.Frame(f)
        ram_wrap.grid(row=2, column=1, columnspan=2, sticky="w", **pad)
        self.ram_var = tk.IntVar(value=self.cfg["ram_mb"])
        self.ram_scale = tb.Scale(ram_wrap, from_=1024, to=16384, orient="horizontal",
                                    variable=self.ram_var, length=320, bootstyle="info",
                                    command=self._on_ram_change)
        self.ram_scale.pack(side="left")
        self.ram_lbl = tb.Label(ram_wrap, text=f"{self.ram_var.get()} MB", width=10,
                                  font=("", 10, "bold"))
        self.ram_lbl.pack(side="left", padx=10)

        tb.Label(f, text="Tên người chơi", font=("", 11, "bold")).grid(
            row=3, column=0, sticky="w", **pad)
        self.user_var = tk.StringVar(value=self.cfg["username"])
        tb.Entry(f, textvariable=self.user_var, width=25, bootstyle="primary").grid(
            row=3, column=1, sticky="w", **pad)

        tb.Label(f, text="Azure client_id\n(login Microsoft)", font=("", 11, "bold")).grid(
            row=4, column=0, sticky="w", **pad)
        self.client_id_var = tk.StringVar(value=self.cfg["azure_client_id"])
        tb.Entry(f, textvariable=self.client_id_var, width=45, bootstyle="primary").grid(
            row=4, column=1, sticky="w", **pad)
        tb.Button(f, text="🔑 Login Microsoft", bootstyle="warning-outline",
                   command=self.login_microsoft_thread).grid(row=4, column=2, sticky="w", padx=6)

        tb.Button(f, text="💾 Lưu cài đặt", bootstyle="success",
                   command=self.save_settings).grid(row=5, column=1, sticky="w", pady=18)

        note = ("Để trống Azure client_id → chạy chế độ offline/dev "
                "(chơi singleplayer hoặc server online-mode=false).")
        tb.Label(f, text=note, bootstyle="secondary", wraplength=520,
                  justify="left").grid(row=6, column=0, columnspan=3, sticky="w", pady=6)

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

    # ------------------------------------------------------------- Java
    def _set_java_status(self, text, bootstyle="secondary"):
        self.after(0, lambda: self.java_status_lbl.config(text=text, bootstyle=bootstyle))

    def check_java_startup(self):
        """Tự động kiểm tra Java ngay khi mở launcher — chạy nền, không chặn UI.
        Nếu thiếu hoặc quá cũ, tự động tải OpenJDK phù hợp mà không cần bấm gì."""
        threading.Thread(target=self._check_java_background, daemon=True).start()

    def _check_java_background(self):
        try:
            configured = self.java_var.get().strip() or "java"
            exe = resolve_java_path(configured)
            version = get_java_version(exe) if exe else None

            if exe and version and version >= JAVA_MAJOR_REQUIRED:
                self.log(f"☕ Đã có Java {version} tại: {exe}")
                self._set_java_status(f"☕ Java {version} — OK", "success")
                return

            # Chưa có Java hợp lệ theo cấu hình — thử bản đã tự cài trước đó
            bundled = find_bundled_java()
            if bundled:
                bv = get_java_version(bundled)
                if bv and bv >= JAVA_MAJOR_REQUIRED:
                    self.java_var.set(str(bundled))
                    self.cfg["java_path"] = str(bundled)
                    save_config(self.cfg)
                    self.log(f"☕ Dùng lại Java {bv} đã tải trước đó: {bundled}")
                    self._set_java_status(f"☕ Java {bv} — OK", "success")
                    return

            if exe and version:
                self.log(f"⚠ Java hiện tại là bản {version}, Minecraft {MC_VERSION} "
                          f"cần Java {JAVA_MAJOR_REQUIRED}+ — sẽ tự động cài bản phù hợp.")
            else:
                self.log(f"⚠ Chưa tìm thấy Java trên máy — sẽ tự động cài OpenJDK "
                          f"{JAVA_MAJOR_REQUIRED} (Eclipse Temurin).")
            self._set_java_status("☕ Đang tự động cài Java...", "warning")
            self._install_java_auto()
        except Exception as e:
            self.log(f"❌ Lỗi khi kiểm tra Java: {e}")
            write_error_log("Kiểm tra Java lúc khởi động", exc=e)

    def install_java_thread(self):
        threading.Thread(target=self._install_java_auto, daemon=True).start()

    def _install_java_auto(self):
        try:
            self.set_status("Đang cài Java...", "warning-inverse-primary")
            self._set_java_status("☕ Đang cài đặt...", "warning")
            self.log(f"☕ Bắt đầu cài OpenJDK {JAVA_MAJOR_REQUIRED}...")

            # Bước 1 (chỉ Linux): thử qua trình quản lý gói hệ thống trước —
            # nhanh hơn, cập nhật được qua hệ thống, phù hợp CachyOS/Arch/Debian/Ubuntu.
            if OS_INFO.get("system") == "Linux" and OS_INFO.get("pkg_manager"):
                self.log(f"  → Thử cài qua trình quản lý gói ({OS_INFO['pkg_manager']})...")
                if install_java_via_pkg_manager(OS_INFO, JAVA_MAJOR_REQUIRED):
                    exe = shutil.which("java")
                    ver = get_java_version(exe) if exe else None
                    if exe and ver and ver >= JAVA_MAJOR_REQUIRED:
                        self.java_var.set(exe)
                        self.cfg["java_path"] = exe
                        save_config(self.cfg)
                        self.log(f"✅ Đã cài Java {ver} qua trình quản lý gói: {exe}")
                        self._set_java_status(f"☕ Java {ver} — OK", "success")
                        self.set_status("Sẵn sàng")
                        return
                    self.log("  ⚠ Gói hệ thống không đủ mới hoặc không có sẵn — "
                              "chuyển sang tải bản OpenJDK rời (portable).")
                else:
                    self.log("  ⚠ Không cài được qua trình quản lý gói — "
                              "chuyển sang tải bản OpenJDK rời (portable).")

            # Bước 2 (Windows luôn dùng cách này, Linux dùng khi bước 1 thất bại):
            # tải thẳng bản Eclipse Temurin (Adoptium) — không cần quyền quản trị.
            if requests is None:
                self.log("❌ Thiếu thư viện 'requests' nên không thể tự tải Java. "
                          "Cài thủ công: pip install requests --break-system-packages")
                self._set_java_status("☕ Cần cài Java thủ công", "danger")
                self.set_status("Lỗi", "danger-inverse-primary")
                return

            url, ext = adoptium_download_info(JAVA_MAJOR_REQUIRED)
            if not url:
                self.log(f"❌ Không hỗ trợ tự động cài Java trên hệ điều hành/kiến trúc này "
                          f"({OS_INFO.get('pretty')}). Vui lòng cài Java {JAVA_MAJOR_REQUIRED}+ thủ công "
                          "rồi chọn file java trong mục Cài đặt.")
                self._set_java_status("☕ Cần cài Java thủ công", "danger")
                self.set_status("Lỗi", "danger-inverse-primary")
                return

            JRE_DIR.mkdir(parents=True, exist_ok=True)
            archive_path = JRE_DIR / f"openjdk{JAVA_MAJOR_REQUIRED}.{ext}"
            self.log(f"⬇ Đang tải OpenJDK {JAVA_MAJOR_REQUIRED} (Eclipse Temurin)... "
                      "có thể mất vài phút tuỳ tốc độ mạng.")
            download_file(url, archive_path, log_fn=self.log)

            self.log("📦 Đang giải nén Java...")
            extract_archive(archive_path, JRE_DIR, ext)
            archive_path.unlink(missing_ok=True)

            java_exe = find_bundled_java()
            if not java_exe:
                raise RuntimeError("Đã tải và giải nén nhưng không tìm thấy file java bên trong.")
            if platform.system() != "Windows":
                try:
                    os.chmod(java_exe, 0o755)
                except Exception:
                    pass

            ver = get_java_version(java_exe) or JAVA_MAJOR_REQUIRED
            self.java_var.set(str(java_exe))
            self.cfg["java_path"] = str(java_exe)
            save_config(self.cfg)
            self.log(f"✅ Đã cài Java {ver} thành công tại: {java_exe}")
            self._set_java_status(f"☕ Java {ver} — OK", "success")
            self.set_status("Sẵn sàng")
        except Exception as e:
            self.log(f"❌ Lỗi khi cài Java: {e}")
            log_path = write_error_log("Cài OpenJDK tự động", exc=e)
            if log_path:
                self.log(f"📝 Chi tiết lỗi đã ghi vào: {log_path}")
            self._set_java_status("☕ Cài Java thất bại", "danger")
            self.set_status("Lỗi", "danger-inverse-primary")

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

    # -------------------------------------------------------------- log tab
    def _build_log_tab(self):
        f = self.tab_log

        toolbar = tb.Frame(f)
        toolbar.pack(fill="x", pady=(0, 8))
        tb.Label(toolbar, text="🖥️  Console", font=("", 12, "bold")).pack(side="left")
        tb.Button(toolbar, text=self.LANG["btn_save_console"], bootstyle="info-outline",
                   command=self.save_console_to_file).pack(side="right", padx=(6, 0))
        tb.Button(toolbar, text=self.LANG["btn_clear_console"], bootstyle="secondary-outline",
                   command=self.clear_console).pack(side="right")

        # Khung console kiểu terminal thật (nền tối, chữ đơn cách) — đặt trong
        # khung viền xanh để vẫn ăn khớp với tông trắng-xanh của launcher.
        console_wrap = tb.Frame(f, bootstyle="primary", padding=2)
        console_wrap.pack(fill="both", expand=True)

        self.log_widget = ScrolledText(console_wrap, autohide=True, height=18,
                                         font=("Consolas", 10))
        self.log_widget.pack(fill="both", expand=True, padx=1, pady=1)
        txt = self.log_widget.text
        txt.configure(bg="#0b1220", fg="#d7e3f4", insertbackground="#d7e3f4",
                       relief="flat", padx=8, pady=6)

        # Tag màu theo cấp độ log — giống console launcher thật
        txt.tag_configure("ts", foreground="#5b7ca8")
        txt.tag_configure("lvl_info", foreground="#7fb2ff")
        txt.tag_configure("lvl_success", foreground="#33d17a")
        txt.tag_configure("lvl_warn", foreground="#f2c94c")
        txt.tag_configure("lvl_error", foreground="#ff6b6b")
        txt.tag_configure("lvl_default", foreground="#d7e3f4")

    def clear_console(self):
        self.log_widget.text.delete("1.0", "end")

    def save_console_to_file(self):
        content = self.log_widget.text.get("1.0", "end").strip()
        try:
            ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = ERROR_LOG_DIR / f"console_{ts}.txt"
            out_path.write_text(content + "\n", encoding="utf-8")
            self.log(f"💾 Đã lưu console ra file: {out_path}")
        except Exception as e:
            self.log(f"❌ Không thể lưu console: {e}")

    def log(self, msg, level=None):
        """Ghi 1 dòng ra console kèm timestamp + màu theo cấp độ.

        level tự suy ra từ nội dung nếu không truyền vào (dựa trên icon
        ❌/⚠/✅ đã được dùng nhất quán khắp launcher).
        """
        text = str(msg)
        if level is None:
            if text.startswith("❌"):
                level = "error"
            elif text.startswith("⚠"):
                level = "warn"
            elif text.startswith("✅") or text.startswith("🎉"):
                level = "success"
            elif text.startswith(("🖥", "📁", "🔍", "⏳", "👉", "▶", "🚀", "⬇", "🔑", "📝", "💾", "ℹ")):
                level = "info"
            else:
                level = "default"
        tag = f"lvl_{level}" if level in ("info", "success", "warn", "error") else "lvl_default"

        def _do():
            txt = self.log_widget.text
            ts = datetime.now().strftime("%H:%M:%S")
            txt.insert("end", f"[{ts}] ", "ts")
            txt.insert("end", text + "\n", tag)
            txt.see("end")
        self.after(0, _do)

    def set_status(self, text, style="success-inverse-primary"):
        self.after(0, lambda: self.status_badge.config(text=f"● {text}", bootstyle=style))

    # -------------------------------------------------- Discord Rich Presence
    def _init_discord_rpc(self):
        if DiscordPresence is None:
            self.log("ℹ Discord Rich Presence: chưa cài 'pypresence' — bỏ qua (không ảnh hưởng launcher).")
            return

        def _connect():
            try:
                rpc = DiscordPresence(DISCORD_CLIENT_ID)
                rpc.connect()
                self.discord_rpc = rpc
                self.log("🎮 Đã kết nối Discord Rich Presence.")
                self.set_discord_activity("Đang mở Arch Client", "Tổng quan")
            except Exception as e:
                self.discord_rpc = None
                self.log(f"ℹ Không kết nối được Discord (Discord có đang mở không?): {e}")

        threading.Thread(target=_connect, daemon=True).start()

    def set_discord_activity(self, details, state=None):
        """Cập nhật trạng thái hiện lên Discord: đang làm gì (details) /
        đang ở đâu hay tải gì (state). Lỗi khi cập nhật (Discord bị đóng
        giữa chừng...) được bỏ qua âm thầm, không làm ảnh hưởng launcher."""
        if not self.discord_rpc:
            return
        try:
            self.discord_rpc.update(
                details=details,
                state=state or "Arch Client",
                start=self.discord_start_time,
                large_image="logo",
                large_text="Arch Client — Minecraft Fabric Launcher",
            )
        except Exception:
            self.discord_rpc = None

    def _on_tab_changed(self, _event=None):
        try:
            current = self.nb.select()
            label = self._discord_tab_states.get(current, "Đang xem launcher")
            self.set_discord_activity(label, f"Minecraft {MC_VERSION} · Fabric")
        except Exception:
            pass

    def _on_close(self):
        if self.discord_rpc:
            try:
                self.discord_rpc.close()
            except Exception:
                pass
        self.destroy()

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
            self.log(f"⏳ Đang cài Fabric Loader cho Minecraft {MC_VERSION}...")
            callback = {
                "setStatus": lambda text: self.log(f"  {text}"),
                "setProgress": lambda value: None,
                "setMax": lambda value: None,
            }
            mll.fabric.install_fabric(MC_VERSION, str(self.mc_dir), callback=callback)
            self.log("✅ Cài Fabric thành công!")
            self.set_status("Sẵn sàng")
        except Exception as e:
            self.log(f"❌ Lỗi khi cài Fabric: {e}")
            log_path = write_error_log("Cài Fabric", exc=e)
            if log_path:
                self.log(f"📝 Chi tiết lỗi đã ghi vào: {log_path}")
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
            self.log(f"❌ Lỗi đăng nhập Microsoft: {e}")
            log_path = write_error_log("Đăng nhập Microsoft", exc=e)
            if log_path:
                self.log(f"📝 Chi tiết lỗi đã ghi vào: {log_path}")

    # ------------------------------------------------------------- Launch
    def launch_game_thread(self):
        if mll is None:
            self.log("❌ Cần cài minecraft-launcher-lib")
            return
        threading.Thread(target=self._launch_game, daemon=True).start()

    def _launch_game(self):
        try:
            self.set_status("Đang khởi chạy...", "warning-inverse-primary")

            java_path = self.java_var.get().strip() or "java"
            resolved_java = resolve_java_path(java_path)
            if not resolved_java:
                self.log(f"❌ Không tìm thấy Java tại '{java_path}'. "
                          "Bấm 'Kiểm tra / Cài Java tự động' trong tab Cài đặt trước.")
                self.set_status("Thiếu Java", "danger-inverse-primary")
                return
            jver = get_java_version(resolved_java)
            if jver and jver < JAVA_MAJOR_REQUIRED:
                self.log(f"⚠ Java hiện tại là bản {jver}, Minecraft {MC_VERSION} cần Java "
                          f"{JAVA_MAJOR_REQUIRED}+. Bấm 'Kiểm tra / Cài Java tự động' để cập nhật.")
                self.set_status("Java quá cũ", "danger-inverse-primary")
                return

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
                "launcherName": "ArchClient",
                "launcherVersion": "2.0",
            }
            command = mll.command.get_minecraft_command(version_id, str(self.mc_dir), options)
            command[0] = resolved_java

            self.log("▶ Đang khởi chạy Minecraft...")
            proc = subprocess.Popen(command, cwd=str(self.mc_dir),
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, bufsize=1)
            self.set_status("Đang chơi", "success-inverse-primary")

            def stream_output():
                game_log_lines = []
                for line in proc.stdout:
                    game_log_lines.append(line.rstrip())
                    self.log(line.rstrip())
                ret = proc.wait()
                if ret != 0:
                    self.log(f"❌ Minecraft thoát với mã lỗi {ret}.")
                    log_path = write_error_log(
                        f"Minecraft crash (mã lỗi {ret})",
                        extra_text="--- 200 dòng cuối của game log ---\n" +
                                    "\n".join(game_log_lines[-200:]))
                    if log_path:
                        self.log(f"📝 Chi tiết crash đã ghi vào: {log_path}")
                    self.set_status("Crash", "danger-inverse-primary")
                else:
                    self.log("ℹ Minecraft đã đóng.")
                    self.set_status("Sẵn sàng")

            threading.Thread(target=stream_output, daemon=True).start()
        except FileNotFoundError as e:
            self.log(f"❌ Không tìm thấy Java tại '{self.java_var.get() or 'java'}': {e}")
            self.log("   Hãy kiểm tra lại đường dẫn Java trong tab Cài đặt.")
            write_error_log("Khởi chạy game — thiếu Java", exc=e)
            self.set_status("Lỗi", "danger-inverse-primary")
        except Exception as e:
            self.log(f"❌ Lỗi khi khởi chạy: {e}")
            log_path = write_error_log("Khởi chạy game", exc=e)
            if log_path:
                self.log(f"📝 Chi tiết lỗi đã ghi vào: {log_path}")
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
            self.log(f"  ❌ Lỗi tải {slug}: {e}")
            write_error_log(f"Tải mod Modrinth ({slug})", exc=e)

    def _apply_optimization(self):
        self.after(0, self.opt_progress.start)
        self.set_status("Đang tối ưu...", "warning-inverse-primary")
        self.log("🚀 Bắt đầu tối ưu FPS...")
        try:
            self._write_optimized_options()
            for slug, var in self.mod_vars.items():
                if var.get():
                    self._download_modrinth_mod(slug)
            self.log("🎉 Hoàn tất tối ưu! Khởi động lại game để áp dụng.")
            self.set_status("Sẵn sàng")
        except Exception as e:
            self.log(f"❌ Lỗi khi tối ưu FPS: {e}")
            log_path = write_error_log("Tối ưu FPS", exc=e)
            if log_path:
                self.log(f"📝 Chi tiết lỗi đã ghi vào: {log_path}")
            self.set_status("Lỗi", "danger-inverse-primary")
        finally:
            # Luôn dừng thanh tiến trình dù thành công hay lỗi, tránh treo UI
            self.after(0, self.opt_progress.stop)
            self.after(0, self.refresh_all)


class SplashScreen(tb.Window):
    """Cửa sổ splash hiển thị khi launcher đang khởi động (dò ngôn ngữ, tải
    cấu hình...) trước khi cửa sổ chính (App) được mở."""

    def __init__(self):
        super().__init__(themename="flatly")
        self.title("Arch Client")
        self.overrideredirect(True)  # không viền/thanh tiêu đề
        self.attributes("-topmost", True)

        width, height = 420, 260
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - width) // 2
        y = (sh - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)

        self._icon_full = load_icon_image()
        if self._icon_full:
            self.iconphoto(True, self._icon_full)

        container = tb.Frame(self, padding=24)
        container.pack(fill=BOTH, expand=True)

        self._banner_img = load_banner_image(max_width=340)
        if self._banner_img:
            tb.Label(container, image=self._banner_img).pack(pady=(10, 15))
        else:
            tb.Label(
                container, text="⚡ Arch Client",
                font=("Segoe UI", 20, "bold"), bootstyle="primary",
            ).pack(pady=(20, 15))

        self.status_var = tk.StringVar(value="")
        tb.Label(
            container, textvariable=self.status_var,
            font=("Segoe UI", 10), bootstyle="secondary",
        ).pack(pady=(0, 12))

        self.bar = tb.Progressbar(
            container, mode="indeterminate", bootstyle="info-striped",
        )
        self.bar.pack(fill=X, padx=10)
        self.bar.start(12)

    def set_status(self, text):
        self.status_var.set(text)


def run_with_splash():
    splash = SplashScreen()

    def worker():
        splash.after(0, lambda: splash.set_status(LANG_STRINGS["vi"]["splash_detect"]))
        lang = detect_language()
        strings = LANG_STRINGS[lang]
        splash.after(0, lambda: splash.set_status(strings["splash_load"]))
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
