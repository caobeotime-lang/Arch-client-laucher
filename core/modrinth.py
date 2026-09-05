"""
Downloads the same curated "Optimize FPS" mod set as the PC launcher,
matched to the player's exact Minecraft + Fabric combination via the
Modrinth API. No JVM involved, just HTTP + file writes -- same as fabric_installer.py.
"""

import os
import requests

API_BASE = "https://api.modrinth.com/v2"

# Same picks as the desktop launcher's "Optimize FPS" button.
FPS_MOD_SLUGS = [
    "sodium",
    "lithium",
    "starlight",
    "ferrite-core",
    "krypton",
    "lazydfu",
    "iris",
    "modernfix",
    "entityculling",
    "immediatelyfast",
]

HEADERS = {"User-Agent": "ArchClientMobile/0.1 (personal-use launcher)"}


def _best_version_for(slug, mc_version, loader="fabric"):
    """Find the newest Modrinth version file compatible with this MC version + loader."""
    r = requests.get(
        f"{API_BASE}/project/{slug}/version",
        params={"loaders": f'["{loader}"]', "game_versions": f'["{mc_version}"]'},
        headers=HEADERS,
        timeout=15,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    versions = r.json()
    return versions[0] if versions else None


def install_fps_pack(minecraft_dir, mc_version, loader="fabric", log=print):
    """Download every mod in FPS_MOD_SLUGS that has a build for this MC version."""
    mods_dir = os.path.join(minecraft_dir, "mods")
    os.makedirs(mods_dir, exist_ok=True)

    installed, skipped = [], []

    for slug in FPS_MOD_SLUGS:
        version = _best_version_for(slug, mc_version, loader)
        if not version:
            log(f"No build of '{slug}' for Minecraft {mc_version} ({loader}) -- skipping.")
            skipped.append(slug)
            continue

        primary_file = next((f for f in version["files"] if f.get("primary")), version["files"][0])
        filename = primary_file["filename"]
        dest_path = os.path.join(mods_dir, filename)

        if os.path.exists(dest_path):
            log(f"{filename} already installed.")
            installed.append(filename)
            continue

        log(f"Downloading {filename}...")
        resp = requests.get(primary_file["url"], headers=HEADERS, timeout=60)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        installed.append(filename)

    log(f"FPS pack done: {len(installed)} installed, {len(skipped)} unavailable for this version.")
    return {"installed": installed, "skipped": skipped}
