# Arch Client Mobile

A companion launcher for Android (built for the Samsung A13, works on other
arm64/armv7 phones too) that mirrors the desktop **Arch Client** launcher's
automation: detects your device, builds the `.minecraft` folder structure,
installs Fabric, and downloads the same curated FPS mod pack (Sodium,
Lithium, Starlight, FerriteCore, Krypton, LazyDFU, Iris, ModernFix,
EntityCulling, ImmediatelyFast).

## What this app does NOT do

Minecraft Java Edition cannot run on Android without a JVM built for
Android and an OpenGL-to-OpenGL-ES translation layer. That code is what
**[PojavLauncher](https://github.com/PojavLauncherTeam/PojavLauncher)**
provides (years of native Java/C work) -- this app does not reimplement
it. **PLAY NOW** hands off to PojavLauncher, which must already be
installed. Think of this app as the "Overview / Settings / Optimize FPS"
tabs from the PC version, running as their own app, pointed at Pojav's
game folder.

## Requirements

- PojavLauncher installed on the phone (from its own release/Play Store
  listing) -- required before this app is useful.
- A computer with Buildozer to compile the APK (Buildozer itself doesn't
  run on Android):
  ```
  pip install buildozer cython --break-system-packages
  ```
- Linux is by far the easiest host OS for Buildozer; it will download its
  own Android SDK/NDK on first build.

## Building the APK

### Option A: GitHub Actions (recommended -- no need for a capable Linux machine)

This project includes `.github/workflows/build-apk.yml`, which builds the
APK on GitHub's own Ubuntu runners using
[buildozer-action](https://github.com/ArtemSBulgakov/buildozer-action).

1. Push to `main` or `feature/mobile-launcher` (or click "Run workflow"
   manually from the Actions tab). `img/icon.png` and `img/banner.png` are
   already committed in this project, so no extra prep needed.
2. Wait for the run to finish (~20-40 min the first time), then open the
   run and download the `archclient-mobile-apk` artifact -- it's a zip
   containing the `.apk`.
3. **Optional, one direct download link instead of digging through
   Actions**: push a tag like `git tag v0.1.0 && git push origin v0.1.0`.
   This also creates a GitHub Release with the APK attached, so you can
   just open that release page on the phone and tap the `.apk` to
   download it straight into Downloads.

### Option B: Build it yourself locally

```
cd archclient_mobile
buildozer android debug
```

The APK lands in `bin/archclientmobile-0.1.0-arm64-v8a_armeabi-v7a-debug.apk`.
Copy it to the phone and install it (enable "install unknown apps" for
whichever app you transfer it with).

## Testing the logic on a desktop first (recommended)

`main.py` runs fine on a regular PC too (the Android-only calls in
`core/detect.py` fall back to stand-in values), so you can iterate on the
UI and the download logic without doing a full Buildozer build every time:

```
pip install kivy requests minecraft-launcher-lib --break-system-packages
python main.py
```

## New since the last version

- **Microsoft login** (`core/msa_login.py`) via `minecraft_launcher_lib`,
  same dependency the PC version already used for this. You need your own
  Azure App registration (client ID) -- required by Microsoft for every
  custom launcher, paste it into the Settings tab. **Honest limitation**:
  this proves account ownership and fetches name/uuid/token, but PLAY NOW
  still hands off to PojavLauncher, which has its own separate built-in
  login -- there's no public API to inject this token into Pojav, so you
  still sign in inside Pojav once to actually play online.
- **VI/EN auto language** (`core/i18n.py`), same IP-geolocation-with-locale-fallback
  approach as the PC version, plus a manual EN/VI toggle button.
- **Automatic error logging** (`core/error_logging.py`) -- unhandled
  exceptions on the main thread or background threads get written to
  `~/.archclient_mobile/error_logs/*.txt` with a full traceback instead of
  crashing silently.
- **Bundled client mod auto-copy** (`core/client_mod.py`) -- drop a `.jar`
  into a `client/` folder next to `main.py` and it's copied into
  `mods/` automatically whenever missing or changed, same as the PC
  version's `client/` folder.
- **Save console log to file**, button in the Console tab.

## Branding (icon / banner)

Both bundled locally now (no network needed to show them):

- **In-app banner** (top of the window): `img/banner.png`, loaded by
  `main.py` via a plain local `Image` widget.
- **App launcher icon** (the icon on the phone's home screen/app list):
  `img/icon.png`, referenced by `buildozer.spec`'s `icon.filename` and baked
  into the APK at build time.

Both files are already your actual logo (uploaded in chat) -- replace
either file directly if you ever want to change it, no code changes
needed.

## Discord Rich Presence -- not included, and here's why

The PC version's Discord Rich Presence works by talking to a **Discord
desktop client running on the same machine** over a local socket. There is
no Discord desktop client running on an Android phone for it to talk to,
so `pypresence` (or any Discord RPC library) won't have anything to
connect to on mobile. This isn't a "not implemented yet" gap, it's a
platform limitation -- skipped rather than shipping code that can't work.

## Known limitations / things to finish before relying on this daily

- **Storage access**: Pojav's `.minecraft` folder lives under
  `Android/data/net.kdt.pojavlaunch/...`, which is app-private storage on
  Android 11+. `buildozer.spec` requests `MANAGE_EXTERNAL_STORAGE` so this
  app can read/write it, which works for side-loaded personal use but
  Google Play will reject apps that request that permission without a
  narrow, justified use case -- fine for your own phone, not for a public
  release as-is. The folder picker in `main.py` is a plain file chooser
  stub; on-device you'll want Android's Storage Access Framework (SAF)
  document picker instead (via `plyer` or a small `pyjnius` wrapper) for a
  smoother one-tap experience.
- **PojavLauncher has no public "launch this exact instance" intent**, so
  `PLAY NOW` opens Pojav itself rather than jumping straight into a
  specific version -- the player picks the profile inside Pojav the first
  time, same as opening it directly.
- **License**: like the desktop version, this is for personal,
  non-commercial use.
