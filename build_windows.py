#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_windows.py — build bản Arch Client TỐI ƯU DUY NHẤT cho Windows.

CHẠY FILE NÀY TRÊN MÁY WINDOWS CÓ PYTHON (chỉ người build cần Python,
người dùng cuối KHÔNG cần cài gì cả — chỉ double-click file .exe kết quả).

Việc build làm gì:
  1. Cài đủ mọi thư viện launcher cần (ttkbootstrap, minecraft-launcher-lib,
     requests, pillow, pypresence...) vào máy build.
  2. Cài PyInstaller nếu chưa có.
  3. Đóng gói arch_laucher.py + toàn bộ thư viện đó thành MỘT file .exe
     duy nhất (--onefile), nhúng sẵn icon + ảnh banner bên trong.
  4. Kết quả nằm ở:  dist/ArchClient.exe

Sau khi build xong, chỉ cần gửi cho người dùng:
    dist/ArchClient.exe        (bắt buộc)
    img/                       (tuỳ chọn — launcher đã có bản nhúng sẵn
                                 bên trong .exe, nhưng nếu đặt cạnh .exe
                                 thì dùng bản đó thay thế)
    client/                    (tuỳ chọn — nếu có mod .jar muốn tự kèm)

Người dùng cuối chỉ cần double-click ArchClient.exe:
  - Lần đầu chạy: launcher tự phát hiện chưa có Java 21 -> tự tải thẳng
    Eclipse Temurin (Adoptium) về ~/.config/arch-client-launcher/jre,
    không cần cài đặt gì thủ công, không cần quyền admin.
  - KHÔNG cần pip install gì cả vì mọi thư viện Python đã được nhúng sẵn
    trong .exe lúc build (đây chính là điều bản .exe cũ trước đây bị lỗi:
    nó cố tự "pip install" bằng chính file .exe, mà .exe thì không có
    "-m pip" nên luôn thất bại).

Usage:
    python build_windows.py
"""
from __future__ import annotations

import os
import sys

# Console Windows trên GitHub Actions runner mặc định dùng codepage không
# hiểu Unicode (emoji, tiếng Việt có dấu) -> in ra là crash ngay lập tức
# (UnicodeEncodeError), khiến job fail chỉ sau vài giây, trước khi kịp cài
# gì. Ép stdout/stderr sang UTF-8 ngay từ đầu để tránh lỗi này.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN_SCRIPT = HERE / "arch_laucher.py"
APP_NAME = "ArchClient"

REQUIRED_PACKAGES = [
    "ttkbootstrap",
    "minecraft-launcher-lib",
    "requests",
    "pillow",
]
OPTIONAL_PACKAGES = [
    "pypresence",
]
BUILD_TOOLS = ["pyinstaller"]


def run(cmd):
    print("  $ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def pip_install(packages, required=True):
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + packages
    try:
        run(cmd)
    except subprocess.CalledProcessError:
        if required:
            raise
        print(f"  ⚠ Bỏ qua gói tuỳ chọn thất bại: {packages}")


def ensure_icon() -> str | None:
    """PyInstaller --icon cần file .ico. Nếu chỉ có icon.png, convert bằng Pillow."""
    ico_path = HERE / "img" / "icon.ico"
    png_path = HERE / "img" / "icon.png"
    if ico_path.exists():
        return str(ico_path)
    if not png_path.exists():
        return None
    try:
        from PIL import Image
        img = Image.open(png_path).convert("RGBA")
        img.save(ico_path, format="ICO",
                 sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        return str(ico_path)
    except Exception as e:
        print(f"  ⚠ Không tạo được icon.ico ({e}) — build vẫn tiếp tục, chỉ là thiếu icon .exe.")
        return None


def main():
    if sys.platform != "win32":
        print("⚠ Script này chỉ tạo bản build Windows — nên chạy trên Windows.")
        print("  (PyInstaller không cross-compile: build trên Windows mới ra .exe Windows.)")

    if not MAIN_SCRIPT.exists():
        sys.exit(f"❌ Không tìm thấy {MAIN_SCRIPT}")

    print("== 1/4: Cài thư viện bắt buộc ==")
    pip_install(REQUIRED_PACKAGES, required=True)

    print("== 2/4: Cài thư viện tuỳ chọn (Discord RPC...) ==")
    pip_install(OPTIONAL_PACKAGES, required=False)

    print("== 3/4: Cài công cụ build (PyInstaller) ==")
    pip_install(BUILD_TOOLS, required=True)

    print("== 4/4: Đóng gói thành ArchClient.exe ==")
    icon = ensure_icon()

    for d in ("build", "dist"):
        shutil.rmtree(HERE / d, ignore_errors=True)
    spec_file = HERE / f"{APP_NAME}.spec"
    if spec_file.exists():
        spec_file.unlink()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
        "--clean",
        "--noconfirm",
    ]
    if icon:
        cmd += ["--icon", icon]

    img_dir = HERE / "img"
    if img_dir.exists():
        sep = ";" if sys.platform == "win32" else ":"
        cmd += ["--add-data", f"{img_dir}{sep}img"]

    # Các gói tuỳ chọn đôi khi PyInstaller không tự dò ra hết — khai báo rõ
    # để nếu người build có cài thì chúng cũng được nhúng theo.
    for hidden in ("pypresence", "tkinterweb", "webview"):
        cmd += ["--hidden-import", hidden]

    cmd += [str(MAIN_SCRIPT)]
    run(cmd)

    exe_path = HERE / "dist" / f"{APP_NAME}.exe"
    if exe_path.exists():
        print(f"\n✅ Build xong: {exe_path}")
        print("   Gửi file này (kèm thư mục img/ và client/ nếu có) cho người dùng.")
        print("   Người dùng chỉ cần double-click — không cần cài Python, pip hay Java thủ công.")
    else:
        sys.exit("❌ Build thất bại — không thấy file .exe trong dist/.")


if __name__ == "__main__":
    main()
