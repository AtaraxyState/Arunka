# PyInstaller build spec
# Run: pyinstaller arunka.spec

import sys
from pathlib import Path

block_cipher = None

# Only set an icon if one is actually present - otherwise PyInstaller aborts.
_icon_path = Path("assets/icon.ico")
icon = str(_icon_path) if _icon_path.exists() else None

a = Analysis(
    ["run.py"],
    pathex=[str(Path(".").resolve())],
    binaries=[],
    datas=[
        ("assets",              "assets"),
        ("config/settings.yaml","config"),
        # CustomTkinter ships its own theme assets - must be bundled
        (
            str(Path(sys.executable).parent / "Lib/site-packages/customtkinter"),
            "customtkinter"
        ),
    ],
    hiddenimports=[
        "customtkinter",
        "PIL._tkinter_finder",
        "cv2", "numpy",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
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
    name="Arunka",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no terminal window
    onefile=True,           # single .exe
    icon=icon,              # uses assets/icon.ico if present, else default
)
