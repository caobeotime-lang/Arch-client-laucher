[app]
title = Arch Client Mobile
package.name = archclientmobile
package.domain = org.archclient
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1.0

# requests -> mod/fabric downloads, pyjnius -> talk to Android (ABI, package manager, intents)
requirements = python3,kivy==2.3.0,requests,pyjnius,android,minecraft-launcher-lib

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/img/icon.png

# Storage: we need broad file access to reach PojavLauncher's .minecraft folder
# under Android/data/net.kdt.pojavlaunch/. MANAGE_EXTERNAL_STORAGE is required on
# Android 11+ for that; it is fine for personal side-loaded use but Google Play
# restricts apps that request it, so do not expect to publish this on the Play Store
# without reworking storage access (e.g. Storage Access Framework / SAF picker).
android.permissions = INTERNET,MANAGE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,QUERY_ALL_PACKAGES

# Samsung A13 is arm64 (Helio G80 / Exynos 850 depending on region).
# Keep armeabi-v7a too for older/other phones "and other phones" per the request.
android.archs = arm64-v8a,armeabi-v7a

android.api = 33
android.minapi = 24
android.ndk = 25b

[buildozer]
log_level = 2
warn_on_root = 1
