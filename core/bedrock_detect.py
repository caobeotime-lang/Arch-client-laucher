"""
Device detection and Bedrock handoff.

Mirrors core/detect.py from the Java Edition Android app, but instead of
checking for PojavLauncher, this checks for the official Minecraft Bedrock
package. Bedrock itself is closed-source and distributed only through the
Play Store, so this module never tries to download or install the game --
it only detects whether it's already there, opens its Play Store listing
if not, or hands off to it (like a normal Android "Open" action) if it is.
"""

import platform

BEDROCK_PACKAGE = "com.mojang.minecraftpe"
PLAY_STORE_URL = f"market://details?id={BEDROCK_PACKAGE}"
PLAY_STORE_WEB_URL = f"https://play.google.com/store/apps/details?id={BEDROCK_PACKAGE}"

try:
    from jnius import autoclass, cast
    ON_ANDROID = True
except ImportError:
    ON_ANDROID = False


def get_abi():
    if ON_ANDROID:
        Build = autoclass("android.os.Build")
        abis = list(Build.SUPPORTED_ABIS)
        return abis[0] if abis else "unknown"
    return platform.machine() or "unknown"


def get_total_ram_mb():
    if ON_ANDROID:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        ActivityManager = autoclass("android.app.ActivityManager")
        Context = autoclass("android.content.Context")
        am = cast(ActivityManager, activity.getSystemService(Context.ACTIVITY_SERVICE))
        info = autoclass("android.app.ActivityManager$MemoryInfo")()
        am.getMemoryInfo(info)
        return int(info.totalMem / (1024 * 1024))
    return 4096


def is_bedrock_installed():
    """Check via the Android PackageManager whether Bedrock is installed."""
    if not ON_ANDROID:
        return False
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        pm = activity.getPackageManager()
        pm.getPackageInfo(BEDROCK_PACKAGE, 0)
        return True
    except Exception:
        return False


def launch_bedrock():
    """Open Minecraft Bedrock if it's already installed."""
    if not ON_ANDROID:
        print("[desktop stub] would launch Minecraft Bedrock here")
        return False
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        pm = activity.getPackageManager()
        intent = pm.getLaunchIntentForPackage(BEDROCK_PACKAGE)
        if intent is None:
            return False
        activity.startActivity(intent)
        return True
    except Exception as e:
        print(f"Failed to launch Minecraft Bedrock: {e}")
        return False


def open_play_store():
    """
    Open Bedrock's Play Store listing so the user can install/buy it
    themselves. This never downloads or sideloads the game -- Bedrock is
    only ever installed through Google's own official flow.
    """
    if not ON_ANDROID:
        import webbrowser
        webbrowser.open(PLAY_STORE_WEB_URL)
        return True
    try:
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        try:
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(PLAY_STORE_URL))
            activity.startActivity(intent)
        except Exception:
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(PLAY_STORE_WEB_URL))
            activity.startActivity(intent)
        return True
    except Exception as e:
        print(f"Failed to open Play Store: {e}")
        return False


def device_summary():
    return {
        "abi": get_abi(),
        "total_ram_mb": get_total_ram_mb(),
        "bedrock_installed": is_bedrock_installed(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(device_summary(), indent=2))
