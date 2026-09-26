[app]
title = Arch Client Bedrock
package.name = archclientbedrock
package.domain = org.caobeotime

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf,otf,txt

version = 1.0

# Everything main.py / core/*.py import. python-for-android bundles its own
# Python interpreter + these packages into the APK at build time, so a
# person installing the finished APK never needs Python or pip themselves --
# only the build machine (or the GitHub Actions workflow) needs them.
requirements = python3,kivy,requests,pyjnius

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/img/icon.png

# --- Android ---
# Only INTERNET is needed: no storage permission, because addon files are
# handed to Minecraft's own import dialog instead of being copied directly
# into another app's folder (see core/addon_manager.py for why).
android.permissions = INTERNET

android.api = 33
android.minapi = 23
android.ndk = 25b
android.sdk = 33

android.archs = arm64-v8a,armeabi-v7a

android.allow_backup = True
android.accept_sdk_license = True

# --- FileProvider, required so addon_manager.py can hand a downloaded
# addon file to Minecraft via a content:// URI instead of a raw file://
# path (file:// in a cross-app intent crashes with FileUriExposedException
# since Android 7). The two XML files below are injected into the manifest
# / res/xml at build time -- see android_manifest/ for what's in them, and
# why the "authorities" value in that XML must stay in sync with
# package.domain + package.name below.
android.gradle_dependencies = androidx.core:core:1.10.1
android.enable_androidx = True
android.extra_manifest_application_arguments = %(source.dir)s/android_manifest/extra_manifest_application_arguments.xml
android.res_xml = %(source.dir)s/android_manifest/file_paths.xml

[buildozer]
log_level = 2
warn_on_root = 1
