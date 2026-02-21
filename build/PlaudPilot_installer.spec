# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for PlaudPilot — onedir build for Inno Setup installer.

This produces an uncompressed directory of files, allowing Inno Setup's LZMA2
solid compression to achieve much better ratios than PyInstaller's built-in
zlib (~50-60% smaller installer vs wrapping a onefile EXE).
"""

import os
import sys
from pathlib import Path

block_cipher = None

REPO_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
VENDOR_FFMPEG = os.path.join(REPO_ROOT, "vendor", "ffmpeg")

# Collect vendor/ffmpeg binaries
ffmpeg_datas = []
if os.path.isdir(VENDOR_FFMPEG):
    for fname in os.listdir(VENDOR_FFMPEG):
        fpath = os.path.join(VENDOR_FFMPEG, fname)
        if os.path.isfile(fpath) and not fname.endswith(".md"):
            ffmpeg_datas.append((fpath, os.path.join("vendor", "ffmpeg")))

# Collect whisper package assets (mel_filters.npz, tokenizer files, etc.)
import importlib.util
_whisper_spec = importlib.util.find_spec("whisper")
if _whisper_spec and _whisper_spec.origin:
    _whisper_pkg = os.path.dirname(_whisper_spec.origin)
    _whisper_assets = os.path.join(_whisper_pkg, "assets")
    if os.path.isdir(_whisper_assets):
        for fname in os.listdir(_whisper_assets):
            fpath = os.path.join(_whisper_assets, fname)
            if os.path.isfile(fpath):
                ffmpeg_datas.append((fpath, os.path.join("whisper", "assets")))

a = Analysis(
    [os.path.join(SRC_DIR, "main.py")],
    pathex=[REPO_ROOT],
    binaries=[],
    datas=ffmpeg_datas,
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "whisper",
        "torch",
    ],
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
    [],
    exclude_binaries=True,  # onedir: binaries go in COLLECT, not EXE
    name="PlaudPilot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # skip UPX — Inno Setup LZMA2 handles compression
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
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
    upx=False,
    upx_exclude=[],
    name="PlaudPilot",
)
