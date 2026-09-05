"""
VI/EN strings, auto-picked the same way the PC version does: try to guess
the country from the device's IP (best-effort, works only with internet),
fall back to system locale if that fails or there's no connection.
"""

import locale as _locale

import requests

STRINGS = {
    "en": {
        "device": "Device",
        "minecraft_folder": "Minecraft folder",
        "choose_folder": "Choose .minecraft folder",
        "create_missing": "Create missing folders",
        "not_set": "Not set yet. Tap 'Choose .minecraft folder' below.",
        "all_present": "OK, all folders present",
        "missing_prefix": "Missing: ",
        "mc_version": "Minecraft version",
        "ram_allocated": "RAM allocated (MB)",
        "suggested_ram": "Suggested for your device: ",
        "optimize_fps_desc": (
            "Downloads the same curated performance mod set as the PC version: "
            "Sodium, Lithium, Starlight, FerriteCore, Krypton, LazyDFU, Iris, "
            "ModernFix, EntityCulling, ImmediatelyFast."
        ),
        "optimize_now": "Optimize FPS now",
        "install_fabric": "Install / Update Fabric",
        "play_now": "PLAY NOW",
        "login_microsoft": "Log in with Microsoft",
        "logged_in_as": "Logged in as ",
        "not_logged_in": "Not logged in",
        "save_log": "Save log to file",
        "pick_folder_first": "Pick a .minecraft folder first (Overview tab).",
    },
    "vi": {
        "device": "Thiết bị",
        "minecraft_folder": "Thư mục Minecraft",
        "choose_folder": "Chọn thư mục .minecraft",
        "create_missing": "Tạo các thư mục còn thiếu",
        "not_set": "Chưa chọn. Bấm 'Chọn thư mục .minecraft' bên dưới.",
        "all_present": "OK, đã đủ thư mục",
        "missing_prefix": "Còn thiếu: ",
        "mc_version": "Phiên bản Minecraft",
        "ram_allocated": "RAM cấp phát (MB)",
        "suggested_ram": "Đề xuất cho máy bạn: ",
        "optimize_fps_desc": (
            "Tải bộ mod tối ưu hiệu năng giống hệt bản PC: "
            "Sodium, Lithium, Starlight, FerriteCore, Krypton, LazyDFU, Iris, "
            "ModernFix, EntityCulling, ImmediatelyFast."
        ),
        "optimize_now": "Tối ưu FPS ngay",
        "install_fabric": "Cài / Cập nhật Fabric",
        "play_now": "CHƠI NGAY",
        "login_microsoft": "Đăng nhập Microsoft",
        "logged_in_as": "Đã đăng nhập: ",
        "not_logged_in": "Chưa đăng nhập",
        "save_log": "Lưu log ra file",
        "pick_folder_first": "Hãy chọn thư mục .minecraft trước (tab Overview).",
    },
}


def _country_from_ip():
    try:
        r = requests.get("https://ipapi.co/json/", timeout=4)
        r.raise_for_status()
        return r.json().get("country_code", "").upper()
    except Exception:
        return None


def detect_language():
    country = _country_from_ip()
    if country == "VN":
        return "vi"
    if country:
        return "en"

    # No internet / API failed -> fall back to system locale, like the PC version.
    try:
        lang_code, _ = _locale.getdefaultlocale()
        if lang_code and lang_code.startswith("vi"):
            return "vi"
    except Exception:
        pass
    return "en"


class Translator:
    def __init__(self, lang=None):
        self.lang = lang or detect_language()

    def t(self, key):
        return STRINGS.get(self.lang, STRINGS["en"]).get(key, key)

    def set_lang(self, lang):
        if lang in STRINGS:
            self.lang = lang
