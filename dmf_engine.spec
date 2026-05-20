# -*- mode: python ; coding: utf-8 -*-
"""
Spec do PyInstaller para o DMF Engine.

Como buildar:
    py -3-32 -m PyInstaller --noconfirm dmf_engine.spec

Saída em: dist/DMF Engine/  (modo onedir)
Entrypoint: dist/DMF Engine/DMF Engine.exe
"""

import os
from PyInstaller.utils.hooks import collect_submodules

PROJECT_ROOT = os.path.abspath(SPECPATH)

# Arquivos auxiliares que precisam ir junto do .exe (read-only embedded)
datas = [
    # Front-end HTML/JS/CSS — carregado pelo pywebview
    (os.path.join(PROJECT_ROOT, "dmf_engine", "ui"), "dmf_engine/ui"),
]

# Imports indiretos que o PyInstaller não detecta sozinho
hiddenimports = [
    "clr_loader.ffi",
    "clr_loader.types",
    "pythonnet",
    "webview.platforms.winforms",
    # Módulos do próprio projeto (importados via from-import dinâmico em alguns pontos)
    "engine.database",
    "engine.master_writer",
    "engine.excel_parser",
    "engine.onedrive_helper",
    "engine.lock_master",
    "engine.estado_compartilhado",
    "modulos.fiscal",
    "modulos.dp",
    "modulos.contabil_preenchedor",
    "modulos.contabil_integrador",
    "modulos.excecoes",
    "dmf_engine.auth",
]

# Recolhe submódulos de pacotes "dinâmicos" para garantir
hiddenimports += collect_submodules("openpyxl")

block_cipher = None

a = Analysis(
    [os.path.join(PROJECT_ROOT, "dmf_engine", "main.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DMF Engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # Sem janela preta de terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, "dmf_engine", "ui", "logo.ico"),
    uac_admin=False,         # Não exige admin
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DMF Engine",
)
