"""
Addon (.mcpack / .mcaddon / .mcworld) download + import.

Design choice, and why: Bedrock's own content folder location is app-
private storage that moves around between Play Store / Store versions and
requires broad storage permissions to reach directly -- fragile, and the
kind of thing Google Play now rejects apps for requesting without a very
narrow justification. Instead, this downloads the file into this app's
own cache and fires a normal Android ACTION_VIEW intent at it. Minecraft
already registers itself as the handler for these file types (that's what
happens when you tap a .mcpack file from a browser download or a file
manager) -- so Android's own chooser (or Minecraft directly, if it's the
only handler) does the actual import. Nothing here writes into another
app's folders, bypasses licensing, or needs elevated permissions beyond
plain INTERNET.
"""

import os
from urllib.parse import urlparse

import requests

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".archclient_bedrock", "addons")

# Mojang registers these on Android so Minecraft shows up as a handler
# for files downloaded/shared with these extensions.
MIME_TYPES = {
    ".mcpack": "application/mcpack",
    ".mcaddon": "application/mcaddon",
    ".mcworld": "application/mcworld",
    ".mctemplate": "application/mctemplate",
    ".mcproject": "application/mcproject",
}

ALLOWED_EXTENSIONS = tuple(MIME_TYPES.keys())

try:
    from jnius import autoclass, cast
    ON_ANDROID = True
except ImportError:
    ON_ANDROID = False


class AddonError(Exception):
    pass


def _extension_of(url, content_disposition=None):
    name = None
    if content_disposition and "filename=" in content_disposition:
        name = content_disposition.split("filename=")[-1].strip('"; ')
    if not name:
        name = os.path.basename(urlparse(url).path)
    for ext in ALLOWED_EXTENSIONS:
        if name.lower().endswith(ext):
            return name, ext
    return name or "addon.mcpack", None


def download(url, log=print):
    """
    Download an addon file to the app's cache. Returns the local path.
    Raises AddonError if the URL doesn't look like a supported addon file.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    log(f"Downloading {url} ...")
    resp = requests.get(url, stream=True, timeout=30)
    if not resp.ok:
        raise AddonError(f"Download failed: HTTP {resp.status_code}")

    filename, ext = _extension_of(url, resp.headers.get("content-disposition"))
    if ext is None:
        raise AddonError(
            "That link doesn't end in .mcpack / .mcaddon / .mcworld / "
            ".mctemplate / .mcproject -- Minecraft won't recognize it."
        )

    dest = os.path.join(CACHE_DIR, filename)
    total = 0
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
            total += len(chunk)
    log(f"Saved {filename} ({total // 1024} KB)")
    return dest


def import_into_minecraft(file_path):
    """
    Fire the Android intent that hands the file to Minecraft's own addon
    importer (or the system chooser, if more than one app can open it).
    Returns True if an activity was found and started.
    """
    if not ON_ANDROID:
        print(f"[desktop stub] would hand {file_path} to Minecraft's importer here")
        return False

    ext = next((e for e in ALLOWED_EXTENSIONS if file_path.lower().endswith(e)), None)
    mime = MIME_TYPES.get(ext, "application/octet-stream")

    try:
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        File = autoclass("java.io.File")
        FileProvider = autoclass("androidx.core.content.FileProvider")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity

        java_file = File(file_path)
        authority = f"{activity.getPackageName()}.fileprovider"
        uri = FileProvider.getUriForFile(activity, authority, java_file)

        intent = Intent(Intent.ACTION_VIEW)
        intent.setDataAndType(uri, mime)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

        chooser = Intent.createChooser(intent, "Import into Minecraft")
        activity.startActivity(chooser)
        return True
    except Exception as e:
        print(f"Failed to hand off addon to Minecraft: {e}")
        return False


def download_and_import(url, log=print):
    path = download(url, log=log)
    ok = import_into_minecraft(path)
    if ok:
        log("Handed off to Minecraft / system chooser. Finish the import there.")
    else:
        log(
            f"Saved to {path} -- open it manually with a file manager and "
            "choose Minecraft if the automatic handoff didn't work."
        )
    return path
