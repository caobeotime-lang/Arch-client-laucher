# Arch Laucher — Linux

A Minecraft Fabric launcher written in Python. Originally built for my own
CachyOS/KDE Plasma setup. The goal was simple: click once and play — no
manually installing Java, setting up Fabric, or fighting the stock launcher
over a messy mod folder.

This is the **Linux branch**. It has every feature of the Windows branch,
plus a layer of Linux-only tuning: GPU and session detection, threaded
OpenGL, on-disk shader cache, `gamemoderun`/MangoHud integration, jemalloc
preloading, and JVM flags that actually make sense on Linux.

The UI uses `ttkbootstrap` (flatly theme) and includes a real terminal-style
console for watching logs live.

![Arch Client icon](img/icon.png)

---

## Why this exists

Mojang's official launcher doesn't support Fabric, and third-party launchers
(MultiMC, Prism...) are great but heavier than needed if all you want is a
fixed, pre-optimized mod set. Arch Client automates that part: open it, it
detects what's missing and installs it, builds the `.minecraft` folder
structure, and gives you a one-click "Optimize FPS" button that pulls a
curated mod set from Modrinth.

On Linux there's a second problem the other launchers mostly leave to you:
the default JVM and driver settings are not what you want for gaming. Mesa's
threaded GL is off, the shader cache is tiny, `_JAVA_OPTIONS` from your
distro silently overrides your heap size, hybrid laptops render on the iGPU,
and a too-large `-Xmx` gets your game killed by the OOM killer mid-session.
This branch handles all of that.

## Features

### Core (shared with the Windows branch)

- **Automatic OS detection** — Arch and Arch-based (Manjaro, EndeavourOS,
  Garuda, CachyOS...), Debian/Ubuntu-based (Mint, Pop!_OS, Zorin...),
  Fedora/Nobara, openSUSE, Void, Alpine. Immutable distros (SteamOS,
  Bazzite, Silverblue, NixOS) and Flatpak/Snap sandboxes are detected and
  never asked for `sudo`.
- **Auto-installs missing Python packages** at startup, with fallbacks for
  the `externally-managed-environment` error: `--break-system-packages`,
  then a user-local install into `~/.local`.
- **Auto-installs missing system packages** for `tkinter` and WebKitGTK,
  via the right package manager for your distro.
- **Auto-detects and installs Java** for the target Minecraft version
  (Java 21+ for 1.20.5 and up), from your package manager or straight from
  Adoptium. You can pick which major version to install (21–26).
- **Auto-builds the `.minecraft` folder structure**, creating from scratch
  or filling in only what's missing.
- **Installs/updates Fabric** for the selected Minecraft version in one click.
- **One-click FPS optimization** — writes a pre-tuned `options.txt` and
  downloads Sodium, Lithium, Starlight, FerriteCore, Krypton, LazyDFU, Iris,
  ModernFix, EntityCulling and ImmediatelyFast, each matched to the exact
  Minecraft + Fabric version you selected. Iris pulls in a compatible Sodium
  build automatically instead of leaving you with a shader crash.
- **Built-in content browser** — search Modrinth for mods, resource packs and
  shaders, with thumbnails, author and download counts. Files land in
  `mods/`, `resourcepacks/` or `shaderpacks/` on their own.
- **Real browser behaviour** — smart address bar (URL opens, anything else
  searches) with a search-engine picker: DuckDuckGo, Google, Bing,
  Startpage, Brave, YouTube, Modrinth, CurseForge. Known tracker domains and
  tracking query parameters are stripped on the way through.
- **Microsoft login** for online play.
- **Discord Rich Presence** (optional, skipped if `pypresence` is missing).
- **Built-in console** with live game logs and a save-to-`.txt` button.
- **Automatic error logging** — every unhandled exception, on any thread, is
  written with a full traceback to
  `~/.config/arch-client-launcher/error_logs/`. No silent crashes.
- **Fully bilingual UI (VI/EN)** — auto-selected from your IP, falling back
  to system locale, with a manual override in Settings.

### Linux-only

All of these live in the **🚀 Optimize FPS** tab, under **🐧 Linux-only
optimization**. The panel shows your detected GPU, session type (X11 or
Wayland), core count, CPU governor and total RAM, and each toggle is saved
to your config.

| Toggle | What it does |
|---|---|
| `gamemoderun` | Runs the game under Feral GameMode — CPU governor to performance, GPU to high-power |
| MangoHud | FPS/temperature/frametime overlay |
| Threaded OpenGL | `mesa_glthread=true` (AMD/Intel) and `__GL_THREADED_OPTIMIZATIONS=1` (NVIDIA). Usually worth 5–20% FPS |
| On-disk shader cache | `MESA_SHADER_CACHE_*` and `__GL_SHADER_DISK_CACHE` pointed at a 4 GB cache — much faster startup and chunk loading from the second run on |
| jemalloc / mimalloc | `LD_PRELOAD`s whichever is installed. The JVM's default glibc allocator fragments badly under Minecraft's allocation pattern; this cuts RSS and micro-stutter |
| Huge Pages + NUMA | `-XX:+UseTransparentHugePages`, and `-XX:+UseNUMA` on multi-socket machines |
| Force discrete GPU | `__NV_PRIME_RENDER_OFFLOAD` + `prime-run` on NVIDIA Optimus, `DRI_PRIME=1` on AMD |
| Disable driver VSync | `vblank_mode=0` / `__GL_SYNC_TO_VBLANK=0` — lower input lag |
| Tiling WM fix | `_JAVA_AWT_WM_NONREPARENTING=1`, which fixes blank/grey windows on i3, sway, bspwm and awesome |
| System GLFW | `-Dorg.lwjgl.glfw.libname=…` so the game uses your distro's GLFW instead of LWJGL's bundled copy — better Wayland behaviour |
| Higher CPU priority | Wraps the launch in `nice -n -5` |
| ZGC instead of G1 | For 8 GB+ heaps, where ZGC's sub-millisecond pauses beat G1 |

Applied regardless of the toggles:

- **Heap is clamped to 75% of physical RAM.** Allocating more than you have
  is the single most common reason a Linux Minecraft session dies to the OOM
  killer with no crash log. The launcher also shows a recommended value.
- **`_JAVA_OPTIONS` and `JAVA_TOOL_OPTIONS` are cleared** before launch.
  Several distros and IDEs export these, and they silently override the
  `-Xmx` the launcher passes.
- **`start_new_session=True`** — closing the launcher no longer kills the
  running game.
- **WebKitGTK is only installed when it's genuinely missing.** Earlier builds
  shelled out to `pacman`/`apt` on every single startup, so every launch
  prompted for a sudo password.

There's also an **⬇ Install gamemode / MangoHud** button that calls the
correct package manager for your distro.

## Folder structure

```
Arch-client-laucher/
├── arch_laucher.py     # the entire launcher, run this file
├── build_linux.py      # packaging script (tar.gz / AppImage)
├── client/             # (optional) bundled client mod, auto-copied into mods/
│   └── arch-client-1.21.11.jar
└── img/
    ├── icon.png        # window/taskbar icon
    └── banner.png      # banner on the Overview tab and splash screen
```

Missing images are not fatal — the launcher falls back to text. The
`client/` folder is optional too; without it the mod-copy step is skipped.

## Requirements

- Python 3.9 or newer.
- `tkinter` (`tk` on Arch, `python3-tk` on Debian/Ubuntu, `python3-tkinter`
  on Fedora). The launcher installs it for you if it can use `sudo`.
- An internet connection on first run, for libraries, Fabric, Java and
  IP-based language detection. Everything except downloads and login works
  offline afterwards.
- Optional but recommended: `gamemode`, `mangohud`, `jemalloc`.

## Installation & running

```bash
git clone -b Linux https://github.com/caobeotime-lang/Arch-client-laucher.git
cd Arch-client-laucher
python3 arch_laucher.py
```

The first run is slower — it installs Python packages, detects Java and
builds the `.minecraft` tree. Later runs skip all of that.

To install the dependencies yourself first:

```bash
pip install minecraft-launcher-lib requests ttkbootstrap pillow --break-system-packages
```

## Building a standalone package

Users receiving the build need no Python, no pip and no Java.

```bash
python3 build_linux.py             # onedir + ArchClient-2.1.0-linux-x86_64.tar.gz
python3 build_linux.py --appimage  # also produces an .AppImage
python3 build_linux.py --onefile   # single executable
```

The `.tar.gz` ships with an `install.sh` that copies everything into
`~/.local/share/arch-client`, symlinks `arch-client` into `~/.local/bin`, and
registers a `.desktop` entry plus icon — no root needed.

**Build on the oldest glibc you intend to support.** A binary built on
current Arch will not start on Ubuntu 22.04, but the reverse works fine.
That's why `.github/workflows/linuxbuild.yml` pins `ubuntu-22.04` rather
than `ubuntu-latest`.

The launcher detects when it's running frozen and reads `$APPDIR` so the
AppImage finds its own `img/` directory.

## Usage guide

| Tab | What it's for |
|---|---|
| 📊 Overview | Pick the `.minecraft` folder, browse installed mods / resource packs / shaderpacks / schematics |
| ⚙️ Settings | Check and install Java, Microsoft login, RAM slider, Minecraft version, language |
| 🚀 Optimize FPS | Performance mod set, tuned `options.txt`, and the Linux-only panel above |
| 🌐 Browser / Mods | Modrinth search with thumbnails, plus a real address bar and search-engine picker |
| 🖥️ Console | Live game logs, clear, save to file |

The footer always shows **⬇ Install / Update Fabric** and **▶ PLAY NOW**.
First-run order: install Fabric → check Java in Settings → Microsoft login
if you're playing online → Play Now.

## Troubleshooting

**`ModuleNotFoundError: No module named 'tkinter'`**
Your distro ships Tk separately. `sudo pacman -S tk`,
`sudo apt install python3-tk`, or `sudo dnf install python3-tkinter`.

**The game window is blank/grey on i3, sway or bspwm**
Enable the tiling WM fix in the Linux panel. It sets
`_JAVA_AWT_WM_NONREPARENTING=1`, which those window managers need.

**The game dies with no crash log, and `dmesg` mentions `oom-kill`**
You allocated more RAM than the system can give. The launcher now clamps to
75% of physical RAM automatically, but check the value on the RAM slider
against the recommendation shown in the Linux panel.

**FPS is far lower than expected on a laptop**
You're probably rendering on the integrated GPU. Turn on "Force the discrete
GPU". On NVIDIA, install `nvidia-prime` so `prime-run` is available. Confirm
with `glxinfo | grep "OpenGL renderer"` under the same wrapper.

**Stuttering that gamemode doesn't fix**
Check the governor shown in the Linux panel. If it reads `powersave` and
GameMode isn't installed, either install `gamemode` or set the governor
yourself with `cpupower frequency-set -g performance`.

**Heavy stuttering on Wayland, or the window won't resize properly**
Enable "Use the system GLFW". LWJGL's bundled GLFW is X11-only, so without it
you're going through XWayland.

**The embedded browser tab is empty**
`tkinterweb`/`pywebview` need WebKitGTK. Install `webkit2gtk-4.1` +
`python-gobject` (Arch) or `gir1.2-webkit2-4.1` + `python3-gi`
(Debian/Ubuntu). The launcher attempts this automatically when it detects
the module is missing.

**Automatic pip installs fail**
Usually no internet on first run, or a proxy. Run the command the console
prints — it already includes the right flags for your distro.

**Game crashes on launch with `Mod resolution failed` / a `MessageFormat`
error**
Two mods in `mods/` conflict. A Fabric Loader bug masks the real message
behind an unrelated date-format exception. Look for the
`Mod resolution failed` and `Immediate reason:` lines just above the crash in
`latest.log` or in the launcher's `error_logs/` file.

**Discord Rich Presence doesn't appear**
`pypresence` isn't installed. Purely optional:
`pip install pypresence --break-system-packages`.

## Contributing

Personal repo, no formal process yet. Bug reports are welcome — please
include your distro, desktop environment and session type (X11/Wayland),
GPU and driver, Python version, and the traceback from `error_logs/`.

## License

Free for **personal, non-commercial use**. You may download, modify and
redistribute it free of charge. You may **not** sell it, rent it, repackage
it for profit, or use it commercially in any form without prior written
consent. See [`LICENSE`](LICENSE).

This covers the launcher's own code only. Mods it downloads (Sodium,
Lithium, Iris, Fabric API...) keep their original licenses.

## Credits

Built on [Fabric](https://fabricmc.net/),
[minecraft-launcher-lib](https://github.com/JakobDev/minecraft-launcher-lib),
[ttkbootstrap](https://ttkbootstrap.readthedocs.io/),
[Feral GameMode](https://github.com/FeralInteractive/gamemode),
[MangoHud](https://github.com/flightlessmango/MangoHud), and the authors of
every optimization mod listed above on [Modrinth](https://modrinth.com/).

---

🌐 [archclient.netlify.app](https://archclient.netlify.app)
