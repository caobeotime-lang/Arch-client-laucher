"""
.minecraft folder management.

Same idea as arch_client.py on PC: create whatever subfolders are missing,
never touch what's already there. The one Android-specific twist is that
we don't assume a fixed path for Pojav's .minecraft folder -- its location
has moved between Pojav versions, and reading another app's storage
requires MANAGE_EXTERNAL_STORAGE. So the app asks the user to point at it
once (Overview tab), exactly like the PC version's folder picker, and
remembers the choice.
"""

import json
import os

REQUIRED_SUBDIRS = [
    "mods",
    "resourcepacks",
    "shaderpacks",
    "schematics",
    "config",
    "versions",
    "libraries",
    "assets",
    "saves",
]

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".archclient_mobile_config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get_minecraft_dir():
    return load_config().get("minecraft_dir")


def set_minecraft_dir(path):
    cfg = load_config()
    cfg["minecraft_dir"] = path
    save_config(cfg)


def inspect(minecraft_dir):
    """Return which required subfolders exist / are missing."""
    if not minecraft_dir or not os.path.isdir(minecraft_dir):
        return {"exists": False, "missing": REQUIRED_SUBDIRS, "present": []}

    present, missing = [], []
    for name in REQUIRED_SUBDIRS:
        (present if os.path.isdir(os.path.join(minecraft_dir, name)) else missing).append(name)
    return {"exists": True, "missing": missing, "present": present}


def build_missing(minecraft_dir, log=print):
    """Create only the subfolders that don't already exist yet."""
    os.makedirs(minecraft_dir, exist_ok=True)
    report = inspect(minecraft_dir)
    for name in report["missing"]:
        path = os.path.join(minecraft_dir, name)
        os.makedirs(path, exist_ok=True)
        log(f"Created missing folder: {name}/")
    if not report["missing"]:
        log(".minecraft already has everything needed, nothing to create.")
    return inspect(minecraft_dir)


def installed_mod_files(minecraft_dir):
    mods_dir = os.path.join(minecraft_dir, "mods")
    if not os.path.isdir(mods_dir):
        return []
    return [f for f in os.listdir(mods_dir) if f.endswith(".jar")]
