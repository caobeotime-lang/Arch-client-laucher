"""
VI/EN strings, same auto-detect approach as the Java Edition launcher:
try to guess the country from the device's IP, fall back to system
locale if that fails or there's no connection.
"""

import locale as _locale

import requests

STRINGS = {
    "en": {
        "app_title": "Arch Client Bedrock",
        "tab_overview": "Overview",
        "tab_account": "Account",
        "tab_addons": "Addons",
        "tab_servers": "Servers",
        "tab_console": "Console",
        "device": "Device",
        "bedrock_status": "Minecraft Bedrock",
        "bedrock_installed": "Installed, ready to play",
        "bedrock_missing": "Not installed on this device",
        "open_play_store": "Open Google Play to install",
        "open_bedrock": "OPEN MINECRAFT",
        "what_this_does_not_do": (
            "Honest limitation: this app cannot download, unlock, or activate "
            "Minecraft Bedrock itself -- the game is closed-source and sold "
            "only through the Play Store / Microsoft Store. This app is a "
            "companion: it helps you install addons, check your Xbox profile, "
            "and keep a server list, exactly like the Overview/Settings tabs "
            "of the PC launcher, but pointed at Bedrock instead of Java."
        ),
        "account_intro": (
            "Sign in with your Microsoft account to see your Xbox profile "
            "(gamertag, XUID). This only reads your public Xbox profile -- "
            "it does not log you into the game itself; you still sign in to "
            "Minecraft the normal way the first time you open it."
        ),
        "client_id_label": "Azure App client ID (yours, see README)",
        "login_microsoft": "Sign in with Microsoft",
        "step1_open_browser": "1) Open sign-in page",
        "step2_paste_url": "2) Paste the URL the browser landed on:",
        "step3_complete": "Complete sign-in",
        "logged_in_as": "Signed in as ",
        "not_logged_in": "Not signed in",
        "addons_intro": (
            "Paste a direct link to a .mcpack / .mcaddon / .mcworld file "
            "(from your own storage/host, or any site you trust). The app "
            "downloads it and hands it to Minecraft's own import dialog -- "
            "nothing is copied into game folders directly, so this keeps "
            "working across Bedrock updates."
        ),
        "addon_url_hint": "https://.../my-pack.mcpack",
        "download_import": "Download && Import into Minecraft",
        "servers_intro": (
            "Bedrock has no public API to add servers to its in-game list "
            "automatically, so this is your own bookmark list -- tap Copy, "
            "then paste the address into Minecraft's 'Add Server' screen."
        ),
        "server_name": "Name",
        "server_address": "Address (host:port)",
        "add_server": "Add",
        "copy": "Copy",
        "remove": "Remove",
        "save_log": "Save log to file",
        "settings": "Settings",
        "language": "Language",
    },
    "vi": {
        "app_title": "Arch Client Bedrock",
        "tab_overview": "Tổng quan",
        "tab_account": "Tài khoản",
        "tab_addons": "Addon",
        "tab_servers": "Máy chủ",
        "tab_console": "Console",
        "device": "Thiết bị",
        "bedrock_status": "Minecraft Bedrock",
        "bedrock_installed": "Đã cài, sẵn sàng chơi",
        "bedrock_missing": "Chưa cài trên máy này",
        "open_play_store": "Mở Google Play để cài",
        "open_bedrock": "MỞ MINECRAFT",
        "what_this_does_not_do": (
            "Giới hạn thật: app này KHÔNG THỂ tự tải, mở khoá hay kích hoạt "
            "Minecraft Bedrock -- game đóng mã nguồn, chỉ bán qua Play Store / "
            "Microsoft Store. App này chỉ là công cụ hỗ trợ: cài addon, xem "
            "thông tin tài khoản Xbox, lưu danh sách server -- giống các tab "
            "Overview/Settings của bản PC, nhưng dành cho Bedrock thay vì Java."
        ),
        "account_intro": (
            "Đăng nhập Microsoft để xem hồ sơ Xbox của bạn (gamertag, XUID). "
            "Chỉ đọc hồ sơ Xbox công khai -- KHÔNG đăng nhập giùm vào game; "
            "bạn vẫn cần đăng nhập trong Minecraft như bình thường lần đầu mở."
        ),
        "client_id_label": "Azure App client ID (của bạn, xem README)",
        "login_microsoft": "Đăng nhập Microsoft",
        "step1_open_browser": "1) Mở trang đăng nhập",
        "step2_paste_url": "2) Dán URL trình duyệt chuyển tới:",
        "step3_complete": "Hoàn tất đăng nhập",
        "logged_in_as": "Đã đăng nhập: ",
        "not_logged_in": "Chưa đăng nhập",
        "addons_intro": (
            "Dán link tải trực tiếp file .mcpack / .mcaddon / .mcworld "
            "(từ nơi bạn lưu trữ, hoặc trang bạn tin tưởng). App sẽ tải về "
            "rồi đưa cho hộp thoại nhập addon của chính Minecraft xử lý -- "
            "không copy thẳng vào thư mục game, nên vẫn hoạt động sau khi "
            "Bedrock cập nhật."
        ),
        "addon_url_hint": "https://.../goi-addon.mcpack",
        "download_import": "Tải về && Nhập vào Minecraft",
        "servers_intro": (
            "Bedrock không có API công khai để tự thêm server vào danh sách "
            "trong game, nên đây là danh sách đánh dấu riêng của bạn -- bấm "
            "Copy rồi dán địa chỉ vào màn hình 'Add Server' trong Minecraft."
        ),
        "server_name": "Tên",
        "server_address": "Địa chỉ (host:port)",
        "add_server": "Thêm",
        "copy": "Copy",
        "remove": "Xoá",
        "save_log": "Lưu log ra file",
        "settings": "Cài đặt",
        "language": "Ngôn ngữ",
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
