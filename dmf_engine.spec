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
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

PROJECT_ROOT = os.path.abspath(SPECPATH)
_AH_DIR         = os.path.join(PROJECT_ROOT, "services", "automacao_horas")
_TFF_DIR        = os.path.join(PROJECT_ROOT, "services", "tff_salvador")
_TFF_ENGINE_DIR = os.path.join(_TFF_DIR, "tf_engine")
_BX_DIR         = os.path.join(PROJECT_ROOT, "services", "buscar_xml")

# collect_submodules() resolve via sys.path do processo do PyInstaller (não o pathex
# do Analysis). Injetamos os dirs dos serviços flat para que collect_submodules
# enxergue bx_config/bx_engine (e os ah_* já dependem do mesmo mecanismo).
for _p in (_AH_DIR, _TFF_DIR, _TFF_ENGINE_DIR, _BX_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Arquivos auxiliares que precisam ir junto do .exe (read-only embedded)
datas = [
    # Front-end HTML/JS/CSS — carregado pelo pywebview
    (os.path.join(PROJECT_ROOT, "dmf_engine", "ui"), "dmf_engine/ui"),
    # UI da Automação de Horas (carregada por ah_launcher no mesmo processo)
    (os.path.join(_AH_DIR, "ui"), "services/automacao_horas/ui"),
]

# Motor TOKAI unificado (services/buscar_xml/tokai_motor/) — código do auto_tokai
# absorvido no projeto. Vai como DADOS para _MEIPASS/tokai_motor; em runtime o
# tokai_adapter sincroniza para uma pasta gravável ao lado do exe (o motor escreve
# token/sessão/logs). NÃO empacotamos segredos: .env, credentials.json, token.json
# e playwright_storage.json ficam por máquina (estão no .gitignore e fora da cópia).
_BX_MOTOR = os.path.join(_BX_DIR, "tokai_motor")
_MOTOR_SKIP_DIRS = {"__pycache__", "logs", "scratch", ".git", ".vscode", ".idea"}
_MOTOR_SKIP_FILES = {".env", "credentials.json", "token.json",
                     "playwright_storage.json", "playwright_storage.json.bak"}
if os.path.isdir(_BX_MOTOR):
    for _root, _dirs, _files in os.walk(_BX_MOTOR):
        _dirs[:] = [d for d in _dirs if d not in _MOTOR_SKIP_DIRS]
        for _f in _files:
            if _f in _MOTOR_SKIP_FILES or _f.endswith((".log", ".zip", ".rar", ".pyc")):
                continue
            if _f.startswith(("debug_", "erro_")):
                continue
            _abs = os.path.join(_root, _f)
            _rel = os.path.relpath(_root, _BX_MOTOR)
            _dest = "tokai_motor" if _rel == "." else os.path.join("tokai_motor", _rel)
            datas.append((_abs, _dest))

# Driver do Playwright (node.exe + package JS) — necessário para lançar o Chromium.
# Sem esses arquivos o sync_playwright() trava indefinidamente no .exe.
datas += collect_data_files("playwright", includes=["driver/**"])

# Chromium headless EMPACOTADO (chromium_headless_shell-1223, ~267 MB).
# Sem isto, máquinas externas travam no chromium.launch(): o instalador antigo
# dependia de baixar o navegador da internet (falha com firewall/proxy/sem rede).
# Empacotado vai para _internal/ms-playwright; o código aponta
# PLAYWRIGHT_BROWSERS_PATH para lá em runtime (ver tf_portal/sm_portal).
_CHROMIUM_BUNDLE = os.path.join(PROJECT_ROOT, "_chromium_bundle")
if os.path.isdir(_CHROMIUM_BUNDLE):
    for _root, _dirs, _files in os.walk(_CHROMIUM_BUNDLE):
        for _f in _files:
            _abs = os.path.join(_root, _f)
            _rel = os.path.relpath(_root, _CHROMIUM_BUNDLE)
            _dest = os.path.join("ms-playwright", _rel) if _rel != "." else "ms-playwright"
            datas.append((_abs, _dest))

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

# Módulos do serviço TFF Salvador — importados como nomes FLAT via sys.path em runtime.
# collect_submodules("tf_engine") geraria tf_engine.tf_planilha (errado); declaramos explicitamente.
hiddenimports += ["tf_service", "tf_planilha", "tf_portal", "tf_resumo"]

# Serviço Buscar XML — services/buscar_xml/ é injetado no sys.path em runtime
# (m_buscar_xml._injetar_path) e importado como nomes FLAT: `from bx_service import
# BuscarXMLService` + pacotes `bx_config.*` / `bx_engine.*`. Sem isto, no exe o
# import falha e listar_lojas() cai no `except: return []` (lista de lojas VAZIA).
# O arquivo foi renomeado de services.py → bx_service.py: o nome "services" colidia
# com o pacote raiz services/__init__.py (vazio) que o PyInstaller empacota, e no exe
# `from services import` resolvia para o pacote vazio (lojas sumiam).
hiddenimports += ["bx_service"]
hiddenimports += collect_submodules("bx_config")
hiddenimports += collect_submodules("bx_engine")

# Dependências do motor TOKAI externo (auto_tokai), carregado via sys.path em runtime.
# O PyInstaller não enxerga os imports do motor (ele não está no Analysis), então as
# libs que o motor usa precisam ser declaradas aqui — senão o exe dá
# "No module named 'dateutil'" etc. O motor em si fica em cada máquina (motor_path);
# só as libs Python viajam no exe. Adicionadas defensivamente (ignora as ausentes).
_TOKAI_LIBS = [
    "dateutil", "dateutil.parser", "dateutil.relativedelta",
    "google", "googleapiclient", "googleapiclient.discovery",
    "google_auth_oauthlib", "google_auth_oauthlib.flow",
    "google.auth", "google.oauth2", "google.oauth2.credentials",
    "google_auth_httplib2", "httplib2",
    "loguru", "dotenv", "rarfile", "schedule", "patoolib",
]
for _lib in _TOKAI_LIBS:
    try:
        __import__(_lib)
        hiddenimports.append(_lib)
    except Exception:
        pass  # lib opcional/ausente (ex.: patoolib) — não bloqueia o build
# Pacotes Google têm muitos submódulos carregados dinamicamente — recolhe o que existir.
for _pkg in ("googleapiclient", "google_auth_oauthlib", "google.oauth2", "dateutil"):
    try:
        hiddenimports += collect_submodules(_pkg)
    except Exception:
        pass

# Recolhe submódulos de pacotes "dinâmicos" para garantir
hiddenimports += collect_submodules("openpyxl")

block_cipher = None

a = Analysis(
    [os.path.join(PROJECT_ROOT, "dmf_engine", "main.py")],
    pathex=[PROJECT_ROOT, _AH_DIR, _TFF_DIR, _TFF_ENGINE_DIR, _BX_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 'unittest' NÃO pode ser excluído: libs do motor TOKAI (google/googleapiclient)
    # importam unittest.mock transitivamente → "No module named 'unittest'" no exe.
    # Mantemos só tkinter fora (pesado e não usado pela UI, que é pywebview).
    excludes=["tkinter"],
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
