[app]
title = Arch Laucher
package.name = archlaucher
package.domain = org.caobeotime

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf,otf,txt

version = 1.0

# Điền đủ lib mà main.py import (sửa lại theo code thực tế)
requirements = python3,kivy

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/img/icon.png

# --- Android ---
android.permissions = INTERNET
android.api = 33
android.minapi = 23
android.ndk = 25b
android.sdk = 33

# Samsung A13 dùng chip 64-bit -> build riêng arm64 để nhẹ và chạy nhanh hơn
android.archs = arm64-v8a

android.allow_backup = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
