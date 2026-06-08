# -*- mode: python ; coding: utf-8 -*-
"""
Spec do PyInstaller para o DMF Engine (64-bit unificado).

Como buildar:
    py -3-64 -m PyInstaller --noconfirm dmf_engine.spec

Saída em: dist/DMF Engine/  (modo onedir)
Entrypoint: dist/DMF Engine/DMF Engine.exe

A Automação de Horas roda no MESMO processo (não há mais subprocesso nem
um segundo .exe): os pacotes ah_* de services/automacao_horas/ são
empacotados e importados via sys.path em runtime. Ver docs/migracao-64bit.md.
"""

import os
from PyInstaller.utils.hooks import collect_submodules

PROJECT_ROOT = os.path.abspath(SPECPATH)
_AH_DIR = os.path.join(PROJECT_ROOT, "services", "automacao_horas")

# Arquivos auxiliares que precisam ir junto do .exe (read-only embedded)
datas = [
    # Front-end HTML/JS/CSS — carregado pelo pywebview
    (os.path.join(PROJECT_ROOT, "dmf_engine", "ui"), "dmf_engine/ui"),
    # UI da Automação de Horas (carregada por ah_launcher no mesmo processo)
    (os.path.join(_AH_DIR, "ui"), "services/automacao_horas/ui"),
]

# usuarios.json é a fonte da verdade de quem pode logar. Empacota como fallback
# (auth.py também procura ao lado do exe, permitindo editar sem rebuildar).
_usuarios_src = os.path.join(PROJECT_ROOT, "dmf_engine", "usuarios.json")
if os.path.exists(_usuarios_src):
    datas.append((_usuarios_src, "dmf_engine"))

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

# Pacotes ah_* da Automação de Horas — importados via sys.path em runtime,
# então o PyInstaller não os detecta sozinho. Coleta explicitamente.
hiddenimports += ["ah_launcher", "ah_api", "ah_auth", "ah_compat"]
for _pkg in ("ah_engine", "ah_modulos", "ah_modules", "ah_core"):
    hiddenimports += collect_submodules(_pkg)

# Recolhe submódulos de pacotes "dinâmicos" para garantir
hiddenimports += collect_submodules("openpyxl")

block_cipher = None

a = Analysis(
    [os.path.join(PROJECT_ROOT, "dmf_engine", "main.py")],
    pathex=[PROJECT_ROOT, _AH_DIR],
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
