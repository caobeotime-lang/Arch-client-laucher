"""
Local Bedrock server bookmark list.

Honest limitation: Bedrock's own in-game server list lives in that app's
private storage and there is no public API for another app to write
entries into it -- so this is a bookmark list that belongs to this app,
not something that appears inside Minecraft automatically. The workflow
is: add a server here once, then tap Copy and paste the address into
Minecraft's own "Add Server" screen. Small extra step, but it's the only
one that doesn't depend on undocumented behavior that Mojang could break
at any update.
"""

import json
import os

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".archclient_bedrock_servers.json")


def load_servers():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_servers(servers):
    with open(CONFIG_FILE, "w") as f:
        json.dump(servers, f, indent=2)


def add_server(name, address):
    servers = load_servers()
    servers.append({"name": name.strip(), "address": address.strip()})
    save_servers(servers)
    return servers


def remove_server(index):
    servers = load_servers()
    if 0 <= index < len(servers):
        servers.pop(index)
        save_servers(servers)
    return servers


def copy_to_clipboard(text):
    try:
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(text)
        return True
    except Exception as e:
        print(f"Clipboard copy failed: {e}")
        return False
