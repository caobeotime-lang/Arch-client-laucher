"""
If this app ships with a client/<name>.jar bundled inside it (same idea as
the PC launcher's client/ folder), copy it into .minecraft/mods/ whenever
it's missing or out of date. Skipped silently if there's no client/ folder,
exactly like the PC version.
"""

import filecmp
import os
import shutil

CLIENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client")


def sync_client_mod(minecraft_dir, log=print):
    if not os.path.isdir(CLIENT_DIR):
        return  # optional folder, nothing to do

    jars = [f for f in os.listdir(CLIENT_DIR) if f.endswith(".jar")]
    if not jars:
        return

    mods_dir = os.path.join(minecraft_dir, "mods")
    os.makedirs(mods_dir, exist_ok=True)

    for jar in jars:
        src = os.path.join(CLIENT_DIR, jar)
        dest = os.path.join(mods_dir, jar)
        if os.path.exists(dest) and filecmp.cmp(src, dest, shallow=False):
            continue  # already installed and identical
        shutil.copy2(src, dest)
        log(f"Installed bundled client mod: {jar}")
