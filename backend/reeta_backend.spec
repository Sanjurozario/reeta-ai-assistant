# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

backend_root = Path(SPECPATH).resolve()

datas = [
    (str(backend_root / "app"), "app"),
]

# Collect package data and dynamic libs
datas += collect_data_files("sqlite_vec")
datas += collect_data_files("faster_whisper")
datas += collect_data_files("ctranslate2")
datas += collect_data_files("tokenizers")

binaries = []
binaries += collect_dynamic_libs("sqlite_vec")
binaries += collect_dynamic_libs("sounddevice")
binaries += collect_dynamic_libs("ctranslate2")

hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "aiosqlite",
    "sqlite_vec",
    "keyring",
    "keyring.backends",
    "keyring.backends.Windows",
    "pyttsx3",
    "pyttsx3.drivers",
    "pyttsx3.drivers.sapi5",
    "sounddevice",
    "numpy",
    "scipy",
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "playwright",
    "bs4",
    "pydantic",
    "pydantic_settings",
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.aiosqlite",
    "sqlalchemy.ext.asyncio",
    "app.main",
    "app.api.v1",
    "app.api.v1.tasks",
    "app.api.v1.system",
    "app.api.v1.permissions",
    "app.api.v1.memory",
    "app.api.v1.voice",
    "app.api.websockets.stream",
    "app.voice.native_audio",
]

a = Analysis(
    [str(backend_root / "app" / "main.py")],
    pathex=[str(backend_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="reeta-backend",
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="reeta-backend",
)

