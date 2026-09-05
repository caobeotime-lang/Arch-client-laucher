"""
Installs Fabric without needing a JVM to run an installer.jar.

The official Fabric installer is just a Java program that:
  1. asks meta.fabricmc.net which loader versions exist for your MC version,
  2. downloads a "launcher profile" JSON describing the libraries needed,
  3. downloads each library jar from Maven and writes the profile into
     .minecraft/versions/<name>/<name>.json

All of that is plain HTTP + file I/O, so we can replicate it directly in
Python -- no Java needed on the phone for this step. (Actually *running*
the resulting profile is still Pojav's job.)
"""

import os
import requests

META_BASE = "https://meta.fabricmc.net/v2"


def list_loader_versions(mc_version):
    r = requests.get(f"{META_BASE}/versions/loader/{mc_version}", timeout=15)
    r.raise_for_status()
    return r.json()


def latest_stable_loader(mc_version):
    versions = list_loader_versions(mc_version)
    for entry in versions:
        if entry["loader"]["stable"]:
            return entry["loader"]["version"]
    if versions:
        return versions[0]["loader"]["version"]
    raise RuntimeError(f"No Fabric loader available for Minecraft {mc_version}")


def fetch_profile(mc_version, loader_version):
    url = f"{META_BASE}/versions/loader/{mc_version}/{loader_version}/profile/json"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()


def _maven_coord_to_path(coord):
    # e.g. "net.fabricmc:fabric-loader:0.15.11" ->
    #      net/fabricmc/fabric-loader/0.15.11/fabric-loader-0.15.11.jar
    group, artifact, version = coord.split(":")
    group_path = group.replace(".", "/")
    filename = f"{artifact}-{version}.jar"
    return f"{group_path}/{artifact}/{version}/{filename}"


def install(minecraft_dir, mc_version, loader_version=None, log=print):
    """
    Downloads the Fabric profile JSON and every library it lists into
    <minecraft_dir>/versions/ and <minecraft_dir>/libraries/, matching the
    layout Pojav (and every other MC launcher) expects.
    """
    loader_version = loader_version or latest_stable_loader(mc_version)
    log(f"Fetching Fabric profile for {mc_version} / loader {loader_version}...")
    profile = fetch_profile(mc_version, loader_version)

    version_name = profile["id"]  # e.g. "fabric-loader-0.15.11-1.21.1"
    version_dir = os.path.join(minecraft_dir, "versions", version_name)
    os.makedirs(version_dir, exist_ok=True)

    profile_path = os.path.join(version_dir, f"{version_name}.json")
    with open(profile_path, "w") as f:
        import json
        json.dump(profile, f, indent=2)
    log(f"Wrote version profile: versions/{version_name}/{version_name}.json")

    libraries = profile.get("libraries", [])
    libraries_dir = os.path.join(minecraft_dir, "libraries")
    total = len(libraries)

    for i, lib in enumerate(libraries, 1):
        coord = lib["name"]
        repo = lib.get("url", "https://maven.fabricmc.net/")
        rel_path = _maven_coord_to_path(coord)
        dest_path = os.path.join(libraries_dir, rel_path)

        if os.path.exists(dest_path):
            log(f"[{i}/{total}] already have {coord}, skipping")
            continue

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        url = repo.rstrip("/") + "/" + rel_path
        log(f"[{i}/{total}] downloading {coord}")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)

    log(f"Fabric {loader_version} installed for Minecraft {mc_version}.")
    return version_name
