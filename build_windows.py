#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_windows.py — build Arch Client cho Windows, TỐI ƯU ĐỂ KHÔNG BỊ
WINDOWS DEFENDER / ANTIVIRUS GẮN CỜ.

Vì sao bản .exe cũ hay bị Defender báo "Trojan:Win32/Wacatac.B!ml":
  1. --onefile: file .exe tự giải nén hàng chục MB ra %TEMP% rồi chạy tiếp
     từ đó. Đây ĐÚNG hành vi của dropper/packer malware -> heuristic ML của
     Defender chấm điểm rất cao. Đây là nguyên nhân số 1.
  2. File .exe KHÔNG có version resource (tên công ty, sản phẩm, phiên bản)
     -> Defender/SmartScreen coi là "phần mềm vô danh", cộng thêm điểm nghi.
  3. UPX nén -> luôn bị coi là packer (ở đây đã tắt sẵn bằng --noupx).
  4. Không ký số (code signing) -> SmartScreen vẫn cảnh báo lần đầu chạy.

Script này xử lý 1, 2, 3 tự động:
  * Mặc định build --onedir (một thư mục ArchClient/ chứa ArchClient.exe
    + DLL) rồi đóng thành ArchClient-windows.zip. Bản onedir gần như
    KHÔNG BAO GIỜ bị gắn cờ vì không có màn tự giải nén ra %TEMP%.
  * Tự sinh file version_info.txt (CompanyName / ProductName / FileVersion)
    và nhúng vào .exe bằng --version-file.
  * Kèm manifest requestedExecutionLevel = asInvoker (xin quyền admin là
    một cờ đỏ khác của Defender).
  * Loại bỏ các module nặng không dùng -> file nhỏ hơn, ít nghi hơn.
  * --noupx, --clean.

Vấn đề 4 (ký số) cần chứng chỉ trả phí, script không làm thay được. Xem
phần "NẾU VẪN BỊ GẮN CỜ" ở cuối file.

Cách dùng:
    python build_windows.py                 # onedir + zip  (KHUYÊN DÙNG)
    python build_windows.py --onefile       # 1 file .exe duy nhất (dễ bị flag)
    python build_windows.py --onefile --sign-self   # onefile + tự ký self-signed
"""
from __future__ import annotations

import os
import sys

# Console Windows trên GitHub Actions dùng codepage không hiểu Unicode ->
# in emoji/tiếng Việt là crash ngay. Ép UTF-8 từ đầu.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import shutil
import zipfile
import argparse
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN_SCRIPT = HERE / "arch_laucher.py"
APP_NAME = "ArchClient"

# Metadata nhúng vào .exe — càng đầy đủ, điểm heuristic càng thấp.
APP_VERSION = "2.1.0"
COMPANY_NAME = "Arch Client"
PRODUCT_NAME = "Arch Client Launcher"
FILE_DESC = "Arch Client - Minecraft Fabric Launcher"
COPYRIGHT = "Free for personal, non-commercial use"

REQUIRED_PACKAGES = ["ttkbootstrap", "minecraft-launcher-lib", "requests", "pillow"]
OPTIONAL_PACKAGES = ["pypresence", "tkinterweb", "pywebview"]
BUILD_TOOLS = ["pyinstaller"]

# Module to, không dùng tới -> loại ra cho .exe nhỏ và "sạch" hơn.
EXCLUDES = [
    "matplotlib", "numpy", "scipy", "pandas", "pytest", "IPython",
    "notebook", "PyQt5", "PyQt6", "PySide2", "PySide6", "sqlite3",
    "test", "unittest", "pydoc_data", "distutils",
]


def run(cmd, check=True):
    print("  $ " + " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=check)


def pip_install(packages, required=True):
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + packages
    try:
        run(cmd)
    except subprocess.CalledProcessError:
        if required:
            raise
        print(f"  ⚠ Bỏ qua gói tuỳ chọn cài thất bại: {packages}")


def ensure_icon() -> str | None:
    """PyInstaller --icon cần .ico; chỉ có icon.png thì convert bằng Pillow."""
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
        print(f"  ⚠ Không tạo được icon.ico ({e}) — build vẫn tiếp tục.")
        return None


def write_version_file() -> Path:
    """Sinh version resource cho .exe.

    File .exe không có metadata bị Defender coi là phần mềm vô danh và cộng
    điểm heuristic. Có CompanyName/ProductName/FileVersion đầy đủ thì tỉ lệ
    bị gắn cờ giảm rõ rệt (và SmartScreen hiện tên sản phẩm thay vì
    'Unknown Publisher').
    """
    parts = (APP_VERSION.split(".") + ["0", "0", "0", "0"])[:4]
    nums = ", ".join(str(int(p)) for p in parts)
    content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({nums}),
    prodvers=({nums}),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{COMPANY_NAME}'),
         StringStruct(u'FileDescription', u'{FILE_DESC}'),
         StringStruct(u'FileVersion', u'{APP_VERSION}'),
         StringStruct(u'InternalName', u'{APP_NAME}'),
         StringStruct(u'LegalCopyright', u'{COPYRIGHT}'),
         StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
         StringStruct(u'ProductName', u'{PRODUCT_NAME}'),
         StringStruct(u'ProductVersion', u'{APP_VERSION}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    path = HERE / "version_info.txt"
    path.write_text(content, encoding="utf-8")
    return path


def write_manifest() -> Path:
    """Manifest asInvoker: KHÔNG xin quyền admin.

    Ứng dụng xin elevation mà không cần là một tín hiệu nghi ngờ mạnh. Arch
    Client không cần admin (Java tải về thư mục ~/.config của người dùng).
    """
    content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity version="{APP_VERSION}.0" processorArchitecture="*"
                    name="{COMPANY_NAME}.{APP_NAME}" type="win32"/>
  <description>{FILE_DESC}</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <!-- Windows 10 / 11 -->
      <supportedOS Id="{{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}}"/>
    </application>
  </compatibility>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true</dpiAware>
    </windowsSettings>
  </application>
</assembly>
"""
    path = HERE / f"{APP_NAME}.manifest"
    path.write_text(content, encoding="utf-8")
    return path


def sign_self_signed(target: Path):
    """Tự ký bằng chứng chỉ self-signed.

    KHÔNG làm SmartScreen im lặng (chứng chỉ không do CA cấp), nhưng có chữ
    ký hợp lệ vẫn giúp giảm điểm heuristic ở một số AV. Cần PowerShell.
    """
    ps = f"""
$ErrorActionPreference = 'Stop'
$cert = Get-ChildItem Cert:\\CurrentUser\\My | Where-Object {{ $_.Subject -eq 'CN={COMPANY_NAME}' }} | Select-Object -First 1
if (-not $cert) {{
  $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject 'CN={COMPANY_NAME}' -CertStoreLocation Cert:\\CurrentUser\\My -NotAfter (Get-Date).AddYears(5)
}}
Set-AuthenticodeSignature -FilePath '{target}' -Certificate $cert -TimestampServer 'http://timestamp.digicert.com' | Out-Null
Write-Host 'Signed OK'
"""
    try:
        run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps])
        print("  ✅ Đã ký self-signed.")
    except Exception as e:
        print(f"  ⚠ Ký self-signed thất bại ({e}) — bỏ qua, build vẫn dùng được.")


def zip_dir(folder: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(folder.parent))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onefile", action="store_true",
                    help="Đóng thành 1 file .exe duy nhất (DỄ BỊ ANTIVIRUS GẮN CỜ).")
    ap.add_argument("--sign-self", action="store_true",
                    help="Ký self-signed sau khi build (Windows, cần PowerShell).")
    ap.add_argument("--no-zip", action="store_true", help="Không nén thư mục dist.")
    args = ap.parse_args()

    if sys.platform != "win32":
        print("⚠ Script này tạo bản Windows — nên chạy trên Windows.")
        print("  (PyInstaller không cross-compile: muốn ra .exe phải build trên Windows.)")

    if not MAIN_SCRIPT.exists():
        sys.exit(f"❌ Không tìm thấy {MAIN_SCRIPT}")

    print("== 1/5: Cài thư viện bắt buộc ==")
    pip_install(REQUIRED_PACKAGES, required=True)

    print("== 2/5: Cài thư viện tuỳ chọn (Discord RPC, browser nhúng…) ==")
    pip_install(OPTIONAL_PACKAGES, required=False)

    print("== 3/5: Cài PyInstaller ==")
    pip_install(BUILD_TOOLS, required=True)

    print("== 4/5: Sinh metadata chống antivirus gắn cờ ==")
    icon = ensure_icon()
    version_file = write_version_file()
    manifest = write_manifest()
    print(f"  ✓ version resource: {version_file.name}")
    print(f"  ✓ manifest asInvoker: {manifest.name}")

    print("== 5/5: Đóng gói ==")
    for d in ("build", "dist"):
        shutil.rmtree(HERE / d, ignore_errors=True)
    spec_file = HERE / f"{APP_NAME}.spec"
    if spec_file.exists():
        spec_file.unlink()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile" if args.onefile else "--onedir",
        "--windowed",
        "--noupx",                      # UPX = packer = cờ đỏ với mọi AV
        "--clean", "--noconfirm",
        "--name", APP_NAME,
        "--version-file", str(version_file),
        "--manifest", str(manifest),
        "--collect-all", "ttkbootstrap",
    ]
    if icon:
        cmd += ["--icon", icon]
    for mod in EXCLUDES:
        cmd += ["--exclude-module", mod]

    img_dir = HERE / "img"
    if img_dir.exists():
        sep = ";" if sys.platform == "win32" else ":"
        cmd += ["--add-data", f"{img_dir}{sep}img"]

    for hidden in ("pypresence", "tkinterweb", "webview", "PIL._tkinter_finder"):
        cmd += ["--hidden-import", hidden]

    cmd += [str(MAIN_SCRIPT)]
    run(cmd)

    if args.onefile:
        exe_path = HERE / "dist" / f"{APP_NAME}.exe"
        if not exe_path.exists():
            sys.exit("❌ Build thất bại — không thấy .exe trong dist/.")
        if args.sign_self and sys.platform == "win32":
            sign_self_signed(exe_path)
        print(f"\n✅ Build xong: {exe_path}")
        print("⚠ Bản --onefile tự giải nén ra %TEMP% -> Defender có thể vẫn gắn cờ.")
        print("  Bị báo nhầm thì build lại KHÔNG có --onefile (bản onedir).")
        return

    app_dir = HERE / "dist" / APP_NAME
    exe_path = app_dir / f"{APP_NAME}.exe"
    if not exe_path.exists():
        sys.exit("❌ Build thất bại — không thấy .exe trong dist/.")
    if args.sign_self and sys.platform == "win32":
        sign_self_signed(exe_path)

    print(f"\n✅ Build xong: {app_dir}")
    if not args.no_zip:
        zip_path = HERE / "dist" / f"{APP_NAME}-windows.zip"
        zip_dir(app_dir, zip_path)
        size = zip_path.stat().st_size / 1024 / 1024
        print(f"✅ Đã nén: {zip_path}  ({size:.1f} MB)")
        print("   Gửi file .zip này cho người dùng — giải nén rồi chạy ArchClient.exe.")
    print("\n📌 Bản onedir gần như không bị Defender gắn cờ vì không tự giải nén")
    print("   ra %TEMP% như bản --onefile.")


if __name__ == "__main__":
    main()
