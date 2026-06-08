"""
services/automacao_horas/main.py
Ponto de entrada standalone da Automação de Horas.

Pode ser lançado de duas formas:
  1. Standalone (login manual):
       py -3-32 services\automacao_horas\main.py

  2. Via SSO da Central DMF (token de sessão):
       py -3-32 services\automacao_horas\main.py --session-token <token>
"""
import os
import sys
import platform

# ── Ajuste de sys.path ────────────────────────────────────────────────────────
# _ROOT = services/automacao_horas/  — local dos módulos desta aplicação.
# Os pacotes têm prefixo ah_* (ah_engine, ah_modulos, ah_core, ah_modules,
# ah_api, ah_compat, ah_auth) para não colidir com os da Central quando rodam
# no mesmo processo. Ver memória colisao-pacotes-engine-config / migracao-horas-inline.
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.dirname(os.path.dirname(_ROOT)))

import threading
import logging
from logging.handlers import RotatingFileHandler

import webview

# Fix para o ícone na barra de tarefas do Windows
if platform.system() == "Windows":
    import ctypes
    try:
        myappid = "dmf.automacao_horas.1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

# BASE_DIR: escrita de logs e config.json ao lado deste main.py (services/automacao_horas/)
BASE_DIR = _ROOT
RESOURCES_DIR = _ROOT
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# Guard de arquitetura: o driver ODBC do Sybase é 32-bit.
PYTHON_BITS = platform.architecture()[0]
if PYTHON_BITS != "32bit":
    print(
        f"[BOOT] AVISO: Python rodando em {PYTHON_BITS}. "
        "O driver ODBC do Domínio (SQL Anywhere) é 32-bit — "
        "conexões falharão. Use 'py -3-32' para rodar este app."
    )

# ── Logging ───────────────────────────────────────────────────────────────────
_log_geral = RotatingFileHandler(
    os.path.join(BASE_DIR, "automacao_horas.log"),
    maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8",
)
_log_geral.setLevel(logging.INFO)
_log_geral.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

_log_erros = RotatingFileHandler(
    os.path.join(BASE_DIR, "automacao_horas_errors.log"),
    maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8",
)
_log_erros.setLevel(logging.WARNING)
_log_erros.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s · %(message)s"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[_log_geral, _log_erros, logging.StreamHandler()],
)


def _logar_excecao_nao_tratada(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logging.critical("Exceção não tratada", exc_info=(exc_type, exc_value, exc_tb))


sys.excepthook = _logar_excecao_nao_tratada
try:
    threading.excepthook = lambda args: logging.critical(
        f"Exceção não tratada na thread {args.thread.name}",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
except AttributeError:
    pass

# ── SSO: recuperar sessão via token da Central DMF ────────────────────────────

def _recuperar_sessao_via_token():
    """
    Lê o token passado pela Central DMF e reconstrói a sessão.
    O token é um arquivo JSON em %TEMP% válido por 30 segundos.
    """
    token = None
    for i, arg in enumerate(sys.argv):
        if arg == "--session-token" and i + 1 < len(sys.argv):
            token = sys.argv[i + 1]
            break
    if not token:
        return None

    import json
    import tempfile
    from datetime import datetime

    caminho = os.path.join(tempfile.gettempdir(), f"dmf_session_{token}.json")
    if not os.path.exists(caminho):
        logging.warning("[SSO] Token não encontrado: %s", caminho)
        return None

    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        os.remove(caminho)  # uso único — apaga imediatamente

        expira = datetime.fromisoformat(dados["expira_em"])
        if datetime.now() > expira:
            logging.warning("[SSO] Token expirado.")
            return None

        sessao = {
            "nome":    dados["usuario"],
            "label":   dados.get("label", dados["usuario"].title()),
            "papel":   dados["papel"],
            "maquina": dados.get("maquina"),
        }
        logging.info("[SSO] Sessão recuperada via token: %s (%s)", sessao["nome"], sessao["papel"])
        return sessao
    except Exception as e:
        logging.error("[SSO] Falha ao ler token: %s", e)
        return None


_sessao_sso = _recuperar_sessao_via_token()

# ── Plugin Module System ───────────────────────────────────────────────────────
from ah_core.config import ConfigManager
from ah_core.event_bus import EventBus
from ah_core.thread_runner import ThreadRunner
from ah_modules.registry import ModuleRegistry
from ah_modules.m_fiscal import FiscalModule
from ah_modules.m_dp import DPModule
from ah_modules.m_contabil import ContabilModule
from ah_api import Api
import ah_compat  # shim: expõe db, estado_sh, PROJECT_ROOT, window

# Aplica credenciais do config.json no singleton db
_config = ConfigManager(CONFIG_FILE)
try:
    _cfg_boot = _config.load()
    compat.db.configurar_de_cfg(_cfg_boot)
except Exception as _e:
    logging.error("[BOOT] Falha ao configurar DB: %s", _e)

# Referência global à janela — atualizada após create_window.
# Também exposta via compat.window para os módulos que precisam de file dialog.
window = None

_bus    = EventBus(lambda: window)
_runner = ThreadRunner(_bus)
_registry = ModuleRegistry(_runner)


def _sessao_fn():
    return api._sessao  # noqa: F821


_registry.register(FiscalModule(_bus, _config, _sessao_fn))
_registry.register(DPModule(_bus, _config, _sessao_fn))
_registry.register(ContabilModule(_bus, _config, _sessao_fn))

# ── Inicialização ─────────────────────────────────────────────────────────────

api = Api(
    registry=_registry,
    config=_config,
    auth=__import__("ah_auth"),
    bus=_bus,
    base_dir=BASE_DIR,
    project_root=compat.PROJECT_ROOT,
    window_fn=lambda: window,
    sessao_inicial=_sessao_sso,
)

window = webview.create_window(
    title="DMF — Automação de Horas",
    url=os.path.join(RESOURCES_DIR, "ui", "index.html"),
    js_api=api,
    width=1100,
    height=720,
    min_size=(900, 600),
    resizable=True,
)

# Propaga a referência para o compat (módulos que chamam _main.window)
compat.window = window

if __name__ == "__main__":
    webview.start(debug=False, icon=os.path.join(RESOURCES_DIR, "ui", "logo.ico"))
