# Arch Client Launcher — Windows

A Minecraft Fabric launcher, packed into a **single `.exe` file**. No
Python required, no manual Java install, no `pip install` — just
double-click and go.

![Arch Client icon](img/icon.png)

---

## Features

- **Auto-downloads Java 21** when missing — the launcher detects it and
  pulls Eclipse Temurin (Adoptium) directly, extracts it, and uses it —
  no manual installation needed.
- **Auto-builds the `.minecraft` folder structure** — creates everything
  from scratch if nothing exists, or fills in just the missing
  subfolders if an older setup is already there.
- **Installs/updates Fabric** for the targeted Minecraft version with a
  single click.
- **One-click FPS optimization** — writes a pre-tuned `options.txt` and
  automatically downloads popular performance mods (Sodium, Lithium,
  Starlight, FerriteCore, Krypton, LazyDFU, Iris, ModernFix,
  EntityCulling, ImmediatelyFast) from Modrinth, matched to the correct
  Minecraft + Fabric version.
- **Microsoft login** for playing online.
- **Discord Rich Presence** (optional) — shows what you're playing /
  which tab you're on right on Discord.
- **Built-in console** — watch game logs live inside the app, save logs
  to a `.txt` file when you need to report a bug.
- **Automatic error logging** — every unhandled exception is caught and
  written to a timestamped `.txt` file with a full traceback in
  `%USERPROFILE%\.config\arch-client-launcher\error_logs\` — never a
  silent crash.
- **Multi-language (VI/EN)** — auto-selected based on your location via
  IP, falling back to system locale if there's no internet connection.
- **Auto-adds a bundled client mod** — if a `.jar` file is present in a
  `client/` folder next to the `.exe`, it's automatically copied into
  `mods/` if missing or outdated.

## Requirements

- Windows 10/11.
- An internet connection on first run (to download Java, download
  Fabric, and detect language via IP). Works offline afterward, aside
  from features that need internet (downloading mods, logging in).

## Installation & running

No setup required — just download `ArchClient.exe` and run it:

1. Download `ArchClient.exe`.
2. Double-click to open it.
3. If Windows shows a **"Windows protected your PC"** warning
   (SmartScreen) — that's expected for an unsigned `.exe` (no code
   signing), not a virus. Click **More info → Run anyway** to open it.
4. The first run takes a bit longer since the launcher is downloading
   Java 21 and building the `.minecraft` folder structure. Later runs
   will be much faster.

## Usage guide

The main window is split into 4 tabs:

| Tab | What it's for |
|---|---|
| 📊 Overview | Choose the `.minecraft` folder, view the list of mod/resourcepack/shaderpack/schematic files currently installed. |
| ⚙️ Settings | Auto-check/install Java, log in with Microsoft, adjust RAM allocated to the game. |
| 🚀 Optimize FPS | One click to write optimized FPS settings + download the selected performance mod set. |
| 🖥️ Console | Watch live logs while the game runs, clear the console, save logs to a file. |

The footer always has 2 fixed buttons: **⬇ Install / Update Fabric**
(click before playing for the first time or after changing versions) and
**▶ PLAY NOW**. The standard first-run flow: install Fabric → check Java
in the Settings tab → log in with Microsoft (if playing online) → click
Play Now.

## Troubleshooting

**Windows blocks or deletes the file on download / when opening it**
The `.exe` isn't code-signed, so Windows Defender/SmartScreen sometimes
flags it as a false positive. Click **More info → Run anyway**, or add
an exception in Windows Security if needed.

**Nothing opens, or a black console window flashes and closes
immediately**
Check your internet connection — the first run needs internet to
download Java and detect language. If it still fails, check the latest
log file in `%USERPROFILE%\.config\arch-client-launcher\error_logs\` for
the full traceback.

**Game crashes right on launch, Java log shows an error related to
`MessageFormat` / `Mod resolution failed`**
This usually means two mods in `mods/` are conflicting. Look for the
`Mod resolution failed` and `Immediate reason:` lines right above the
crash in `latest.log` (or in the log file in `error_logs/`) to find out
exactly which mods are conflicting, then remove or swap one out.

**Discord Rich Presence doesn't show up**
Optional feature, not required — doesn't affect gameplay if it's not
active.

## License

This software is **free for personal, non-commercial use**. You're
allowed to download, modify, and redistribute it for free. You are
**not** allowed to sell it, rent it, repackage it for profit, or use it
for any commercial purpose in any form without prior written consent
from the author. See the [`LICENSE`](LICENSE) file for details.

## Credits

Thanks to the open-source projects Arch Client relies on:
[Fabric](https://fabricmc.net/),
[minecraft-launcher-lib](https://github.com/JakobDev/minecraft-launcher-lib),
[ttkbootstrap](https://ttkbootstrap.readthedocs.io/), and all the authors
of the FPS optimization mods listed above on
[Modrinth](https://modrinth.com/).

---

🌐 [archclient.netlify.app](https://archclient.netlify.app)
