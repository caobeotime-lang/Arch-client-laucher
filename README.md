# Arch Client Bedrock

A companion app for **Minecraft Bedrock Edition** on Android, in the same
spirit as the **Arch Client** launcher (Windows/Linux, Java Edition) and
**Arch Client Mobile** (Android, Java Edition via PojavLauncher) -- same
look, same VI/EN bilingual UI, same "point and tap" philosophy.

## What this app does NOT do (read this first)

Minecraft Bedrock is **closed-source** and sold only through the Google
Play Store / Microsoft Store, unlike Java Edition where Mojang's version
manifest is public and any launcher can fetch the game files legitimately.
That means:

- This app **cannot download, unlock, crack, or activate** Minecraft
  Bedrock. There is no legitimate API for that, and building one would
  mean piracy -- not something this project does.
- The Microsoft sign-in here **does not log you into the game**. Bedrock
  signs in to Xbox Live by itself, inside the game, and there's no public
  way for another app to inject a session into it.
- There is no "auto-add server" API for Bedrock's in-game server list, so
  the Servers tab is a personal bookmark list you copy-paste from, not
  something that appears inside Minecraft by itself.

If any of that is a dealbreaker for what you had in mind, this app isn't
going to do it -- and no Bedrock launcher legitimately can.

## What it actually does

- **Overview**: detects whether Bedrock is installed (checks for
  `com.mojang.minecraftpe`) and shows either an **OPEN MINECRAFT** button
  or a **Open Google Play to install** button -- never tries to fetch the
  game itself.
- **Account**: "Sign in with Microsoft" -- a standard OAuth2 + Xbox Live
  token exchange (the same kind of flow many fan-made stat-tracker apps
  use) that reads your public Xbox profile (gamertag, XUID, gamerpic).
  Read-only identity, nothing more.
- **Addons**: paste a direct link to a `.mcpack` / `.mcaddon` / `.mcworld`
  file (from your own storage, your own site, or anywhere you trust), the
  app downloads it and hands it straight to Minecraft's own import dialog
  via a `content://` URI (a `FileProvider`, wired up in `buildozer.spec` /
  `android_manifest/`) -- the same thing that happens when you tap a
  `.mcpack` file from a browser download. No `MANAGE_EXTERNAL_STORAGE`,
  no guessing where Bedrock's data folder lives this month.
- **Servers**: a local bookmark list (name + `host:port`) with a Copy
  button, since there's no API to inject entries into Bedrock's own list.
- **Console**: live log of everything the app does, with a "save to file"
  button. Every unhandled exception (main thread or background thread)
  is also caught and written to
  `~/.archclient_bedrock/error_logs/*.txt` with a full traceback.
- Fully bilingual (VI/EN), auto-detected from IP with a manual toggle,
  same as the other Arch Client apps.

## One thing you need to set up yourself: an Azure App registration

Signing in with Microsoft requires every custom app to have its own
"Client ID" -- this is a Microsoft requirement, not something this app
can bundle for you (same requirement the Java Edition launcher already
has). It's free and takes a couple of minutes:

1. Go to <https://portal.azure.com> -> **App registrations** -> **New
   registration**.
2. Name it anything. Under **Supported account types**, pick "Personal
   Microsoft accounts only" (or "Accounts in any organizational directory
   and personal Microsoft accounts").
3. Under **Redirect URI**, pick platform **"Mobile and desktop
   applications"** and add:
   `https://login.microsoftonline.com/common/oauth2/nativeclient`
4. After creating it, go to **Authentication** -> **Advanced settings**
   and turn on **"Allow public client flows"**.
5. Copy the **Application (client) ID** from the Overview page and paste
   it into the Account tab in the app.

## Requirements to build

- A computer with Buildozer (Buildozer itself doesn't run on Android):
  ```
  pip install buildozer cython --break-system-packages
  ```
- Linux is by far the easiest host OS; Buildozer downloads its own
  Android SDK/NDK on first build.

## Building the APK

### Option A: GitHub Actions (recommended)

This project includes `.github/workflows/build-apk.yml`.

1. Push to the `Bedrock` branch (or click "Run workflow" manually).
2. Wait for the run to finish (~20-40 min the first time), then download
   the `archclient-bedrock-apk` artifact from the run.
3. Or tag a release (`git tag v0.1.0 && git push origin v0.1.0`) to get a
   direct APK download link via GitHub Releases.

### Option B: Build it yourself locally

```bash
buildozer android debug
```

The APK lands in `bin/archclientbedrock-1.0-arm64-v8a_armeabi-v7a-debug.apk`.
Copy it to the phone and install it (enable "install unknown apps" for
whichever app you transfer it with) -- **this only installs the
companion app itself**; Bedrock still has to come from the Play Store,
same as any other phone.

Once it's installed, **"just tap the APK" really is the whole setup**:
python-for-android bundles Python + every library this app needs directly
into the APK at build time, so there's nothing to install manually on the
phone afterward -- no Python, no pip, no missing-library prompts.

## Testing the logic on a desktop first (recommended)

`main.py` runs fine on a regular PC too (the Android-only calls fall back
to safe stand-in values, and the "open store" button just opens the web
listing in your browser instead of Play Store):

```bash
pip install kivy requests --break-system-packages
python main.py
```

## Project layout

```
archclient_bedrock/
├── main.py                     # Kivy app, 5 tabs: Overview/Account/Addons/Servers/Console
├── core/
│   ├── bedrock_detect.py       # detect Bedrock, open Play Store / launch it
│   ├── xbox_login.py           # OAuth2 + Xbox Live token exchange -> profile
│   ├── addon_manager.py        # download + hand off .mcpack/.mcaddon/.mcworld
│   ├── server_list.py          # local server bookmarks + clipboard copy
│   ├── i18n.py                 # VI/EN strings, auto-detected
│   └── error_logging.py        # catches unhandled exceptions -> log file
├── android_manifest/           # FileProvider manifest snippet + res/xml, wired
│                                # in via buildozer.spec (see comments in both)
├── img/                        # icon.png / banner.png (shared with the other branches)
└── buildozer.spec
```

## License

Same terms as the rest of Arch Client: free for personal, non-commercial
use. See [`LICENSE`](LICENSE).
