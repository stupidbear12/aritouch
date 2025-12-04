# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

block_cipher = None

try:
    project_dir = Path(__file__).resolve().parent
except NameError:
    project_dir = Path(os.getcwd()).resolve()
entry_point = project_dir / "main.py"

mediapipe_hidden = collect_submodules("mediapipe")
cv2_hidden = collect_submodules("cv2")
hiddenimports = sorted(set(mediapipe_hidden + cv2_hidden))

mediapipe_datas = collect_data_files(
    "mediapipe",
    includes=[
        "**/*.binarypb",
        "**/*.pbtxt",
        "**/*.task",
        "**/*.json",
        "**/*.tflite",
    ],
)
datas = mediapipe_datas

mediapipe_bins = collect_dynamic_libs("mediapipe")
cv2_bins = collect_dynamic_libs("cv2")
binaries = mediapipe_bins + cv2_bins

a = Analysis(
    [str(entry_point)],
    pathex=[str(project_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AirTouch",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AirTouch",
)

