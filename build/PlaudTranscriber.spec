# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for PlaudTranscriber — onefile build."""

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

a = Analysis(
    [os.path.join(SRC_DIR, "main.py")],
    pathex=[REPO_ROOT],
    binaries=[],
    datas=ffmpeg_datas,
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "openai",
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PlaudTranscriber",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI app, no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if available
)
