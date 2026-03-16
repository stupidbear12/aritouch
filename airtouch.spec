from PyInstaller.utils.hooks import (
    collect_dynamic_libs,
    collect_submodules,
    collect_data_files,
)

APP_NAME = "Aritouch"
ENTRY = "run_app.py"
ICON = None
cv2_bins = collect_dynamic_libs("cv2")
mp_bins  = collect_dynamic_libs("mediapipe")

hidden = []
hidden += collect_submodules("mediapipe")
hidden += collect_submodules("cv2")

mp_datas = collect_data_files(
    "mediapipe",
    includes=[
        "modules/*/*.binarypb",
        "modules/*/*/*.binarypb",
        "modules/*/*/*/*.binarypb",
    ],
    include_py_files=False,
)


a = Analysis(
    [ENTRY],
    pathex=[],
    binaries=cv2_bins + mp_bins,
    datas=mp_datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=APP_NAME,
    console=False,
    icon=ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=APP_NAME,
)
