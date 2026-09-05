"""
Device / environment detection.

On a real Android device this uses pyjnius to talk to the Android API
directly (Build.SUPPORTED_ABIS, ActivityManager for RAM, PackageManager to
check whether PojavLauncher is installed). When not running on Android
(e.g. you're testing this file on a desktop with `python -m core.detect`)
it falls back to safe stand-in values so the rest of the app doesn't crash.
"""

import platform

POJAV_PACKAGE = "net.kdt.pojavlaunch"

try:
    from jnius import autoclass, cast
    ON_ANDROID = True
except ImportError:
    ON_ANDROID = False


def get_abi():
    """Return the primary ABI of this device, e.g. 'arm64-v8a'."""
    if ON_ANDROID:
        Build = autoclass("android.os.Build")
        abis = list(Build.SUPPORTED_ABIS)
        return abis[0] if abis else "unknown"
    return platform.machine() or "unknown"


def get_total_ram_mb():
    """Total device RAM in MB. Used to suggest a safe RAM allocation for the game."""
    if ON_ANDROID:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        ActivityManager = autoclass("android.app.ActivityManager")
        Context = autoclass("android.content.Context")
        am = cast(ActivityManager, activity.getSystemService(Context.ACTIVITY_SERVICE))
        info = autoclass("android.app.ActivityManager$MemoryInfo")()
        am.getMemoryInfo(info)
        return int(info.totalMem / (1024 * 1024))
    # Desktop fallback so the code is testable off-device.
    return 4096


def suggested_ram_allocation_mb(total_ram_mb=None):
    """
    Conservative RAM suggestion for Minecraft on a shared device like the A13
    (4GB total on most variants): leave enough for Android + the launcher itself.
    """
    total = total_ram_mb or get_total_ram_mb()
    if total <= 3072:
        return 1024
    if total <= 4096:
        return 1536
    if total <= 6144:
        return 2048
    return 3072


def is_pojav_installed():
    """Check whether PojavLauncher is installed, using the Android PackageManager."""
    if not ON_ANDROID:
        return False
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        pm = activity.getPackageManager()
        pm.getPackageInfo(POJAV_PACKAGE, 0)
        return True
    except Exception:
        return False


def launch_pojav():
    """
    Hand off to PojavLauncher so it can actually run the game (JVM + GL
    translation live there, not in this app). This only launches the app;
    Pojav has no officially documented intent API to jump straight to a
    specific instance/version, so the player picks the profile inside Pojav
    the first time.
    """
    if not ON_ANDROID:
        print("[desktop stub] would launch PojavLauncher here")
        return False
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        pm = activity.getPackageManager()
        intent = pm.getLaunchIntentForPackage(POJAV_PACKAGE)
        if intent is None:
            return False
        activity.startActivity(intent)
        return True
    except Exception as e:
        print(f"Failed to launch PojavLauncher: {e}")
        return False


def device_summary():
    return {
        "abi": get_abi(),
        "total_ram_mb": get_total_ram_mb(),
        "suggested_ram_mb": suggested_ram_allocation_mb(),
        "pojav_installed": is_pojav_installed(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(device_summary(), indent=2))
