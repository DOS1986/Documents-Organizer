# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH)

app_name = "DocumentsOrganizer"

entry_point = project_root / "main.py"

icon_path = (
    project_root
    / "images"
    / "folder-256.ico"
)

images_path = (
    project_root
    / "images"
)

version_info_path = (
    project_root
    / "packaging"
    / "windows"
    / "version_info.txt"
)

a = Analysis(
    [str(entry_point)],
    pathex=[
        str(project_root),
    ],
    binaries=[],
    datas=[
        (
            str(images_path),
            "images",
        ),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(
    a.pure
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(version_info_path),
    icon=[
        str(icon_path),
    ],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)