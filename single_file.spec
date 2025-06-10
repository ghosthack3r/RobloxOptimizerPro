# single_file.spec

# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# ─── 1) Name of the final EXE (no spaces) ───────────────────────────────────────
app_name = "RobloxOptimizerPro"

# ─── 2) Hard‐code the absolute folder where everything lives ────────────────────
project_dir = r"C:\Users\ghosthack3r\APPS\Roblox Optimizer Pro - GUI UPDATE"

# ─── 3) Specify the full path to your entry‐point script ────────────────────────
main_script = os.path.join(project_dir, "launcher_script.py")
if not os.path.exists(main_script):
    raise FileNotFoundError(
        f"Could not find your entry‐point at:\n    {main_script}\n"
        "Make sure that path is correct and that launcher_script.py actually exists there."
    )

# ─── 4) Icon path (optional). Make sure resources/icon.ico exists under project_dir ───
icon_path = os.path.join(project_dir, "resources", "icon.ico")
if not os.path.exists(icon_path):
    icon_path = None
    print("WARNING: resources/icon.ico not found. Continuing without a custom icon.")

# ─── 5) Bundle any data files (icons, SVGs, sub-executables) ─────────────────────
datas = []
for rel_src, dst_folder in [
    ("resources/icon.ico",         "resources"),
    ("resources/down_arrow.svg",   "resources"),
    ("resources/rbxfpsunlocker/rbxfpsunlocker.exe", "resources/rbxfpsunlocker"),
    ("resources/speedtest/speedtest.exe",          "resources/speedtest"),
]:
    abs_src = os.path.join(project_dir, rel_src)
    if os.path.exists(abs_src):
        datas.append((abs_src, dst_folder))
    else:
        print(f"WARNING: Data file not found, skipping: {abs_src}")

# ─── 6) Explicitly include python3X.dll and VCRUNTIME140.dll ─────────────────────
binaries = []
python_ver_minor = sys.version_info.minor
python_dll_name = f"python3{python_ver_minor}.dll"
python_dll_path = os.path.join(sys.base_prefix, python_dll_name)
if os.path.exists(python_dll_path):
    binaries.append((python_dll_path, "."))
else:
    print(f"WARNING: {python_dll_name} not found at {python_dll_path}")

vcruntime_name = "VCRUNTIME140.dll"
vcruntime_path1 = os.path.join(sys.base_prefix, vcruntime_name)
vcruntime_path2 = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32", vcruntime_name)
if os.path.exists(vcruntime_path1):
    binaries.append((vcruntime_path1, "."))
elif os.path.exists(vcruntime_path2):
    binaries.append((vcruntime_path2, "."))
else:
    print(f"WARNING: {vcruntime_name} not found in Python folder or System32")

# ─── 7) (Optional) Custom runtime hooks ─────────────────────────────────────────
runtime_hooks = []
hook_path = os.path.join(project_dir, "my_rthook.py")
if os.path.exists(hook_path):
    runtime_hooks.append(hook_path)
else:
    print("WARNING: my_rthook.py not found; skipping runtime hooks.")

# ─── 8) Collect all PySide6 data, binaries, and hidden imports ───────────────────
# This ensures that QShortcut, QKeySequence, and any dynamically loaded Qt modules are included.
pyside_datas, pyside_binaries, pyside_hiddenimports = collect_all("PySide6")

# ─── 9) Merge user-specified datas/binaries with PySide6 files ───────────────────
all_datas = datas + pyside_datas
all_binaries = binaries + pyside_binaries

# ─── 10) Define any additional hiddenimports you explicitly need ─────────────────
extra_hiddenimports = [
    # Additional Python modules that may be dynamically imported at runtime
    "psutil",
    "winreg",
    "keyboard",
    "win32gui",
    "win32process",
    "win32api",
    "pywintypes",
    # Explicitly ensure QtCore/QtGui/QtWidgets/etc. are bundled
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtSvg",
    "shiboken6",
    # Particularly ensure QShortcut and QKeySequence are available
    "PySide6.QtWidgets.QShortcut",
    "PySide6.QtWidgets.QKeySequence",
    "PySide6.QtGui.QShortcut",
    "PySide6.QtGui.QKeySequence",
]

# Combine with the automatically collected hiddenimports from collect_all
all_hiddenimports = list(set(pyside_hiddenimports + extra_hiddenimports))

# ─── 11) ANALYSIS: detect imports, collect binaries & datas ─────────────────────
a = Analysis(
    [main_script],
    pathex=[project_dir],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    runtime_hooks=runtime_hooks,
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

# ─── 12) PYZ: bundle pure‐Python modules into a compressed archive ───────────────
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

# ─── 13) EXE: build one single-file executable (no separate COLLECT step) ───────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=app_name,
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,                  # Set to True for console window; False for GUI-only
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path
)

# ─── 14) NO COLLECT: single-file bundle is complete at dist\<app_name>.exe ───────
