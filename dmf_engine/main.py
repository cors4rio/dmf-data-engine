"""
DMF Engine — Ponto de entrada PyWebView
Abre janela nativa com o HTML já existente e expõe a bridge Python ↔ JS.
"""
import webview
import os
import sys
import platform
import threading
import logging
from logging.handlers import RotatingFileHandler

# Fix para o ícone na barra de tarefas do Windows
if platform.system() == "Windows":
    import ctypes
    try:
        myappid = "dmf.engine.app.1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

# Resolve diretórios:
#   BASE_DIR      → escrita (logs, config.json, supervisores.json) — ao lado do .exe em frozen
#   RESOURCES_DIR → leitura de assets empacotados (HTML, .ico) — dentro de _internal em frozen
#   PROJECT_ROOT  → raiz para importar engine/ e modulos/
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    RESOURCES_DIR = os.path.join(sys._MEIPASS, "dmf_engine")
    PROJECT_ROOT = BASE_DIR
    # Fix: PyInstaller frozen exe no Windows usa ProactorEventLoop (IOCP) por padrão.
    # O pywebview/winforms já ocupa o IOCP do thread principal; quando Playwright
    # cria um ProactorEventLoop em thread daemon para se comunicar com node.exe via
    # PIPE, ocorre conflito e o loop bloqueia indefinidamente sem lançar exceção.
    # SelectorEventLoop não usa IOCP e funciona corretamente em qualquer thread.
    if sys.platform == "win32":
        import asyncio as _asyncio
        _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCES_DIR = BASE_DIR
    PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_ROOT)

# db e estado_sh são re-exportados para os adaptadores de módulo que referenciam
# `import dmf_engine.main as _main; _main.db / _main.estado_sh` na transição.
from engine.database import db             # noqa: F401
from engine import estado_compartilhado as estado_sh  # noqa: F401
from dmf_engine import auth as auth_mod

# B09: RotatingFileHandler em vez de FileHandler — impede crescimento ilimitado.
# 10MB por arquivo × 5 backups = 50MB máximo por handler.
_log_geral = RotatingFileHandler(
    os.path.join(BASE_DIR, "dmf_engine.log"),
    maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8",
)
_log_geral.setLevel(logging.INFO)
_log_geral.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

_log_erros = RotatingFileHandler(
    os.path.join(BASE_DIR, "dmf_engine_errors.log"),
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


CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# Referência global à janela — preenchida após webview.create_window().
# Exposta como global para que adaptadores de módulo referenciem via
# `import dmf_engine.main as _main; win = _main.window` durante a transição.
window = None

# ── Plugin Module System bootstrap ───────────────────────────────────────────
from dmf_engine.core.config import ConfigManager
from dmf_engine.core.event_bus import EventBus
from dmf_engine.core.thread_runner import ThreadRunner
from dmf_engine.modules.registry import ModuleRegistry
from dmf_engine.modules.m_automacao_horas import AutomacaoHorasLauncher
from dmf_engine.modules.m_relatorio_rendimentos import RelatorioRendimentosModule
from dmf_engine.modules.m_buscar_xml import BuscarXMLModule
from dmf_engine.modules.m_sem_movimento_nfse import SemMovimentoNfseModule
from dmf_engine.modules.m_tff_salvador import TffSalvadorModule
from dmf_engine.api import Api

_config = ConfigManager(CONFIG_FILE)
_bus    = EventBus(lambda: window)
_runner = ThreadRunner(_bus)
_registry = ModuleRegistry(_runner)


def _sessao_fn():
    # Retorna a sessão atual da instância api (criada logo abaixo).
    return api._sessao  # noqa: F821


_registry.register(AutomacaoHorasLauncher(_bus, _config, _sessao_fn))
_registry.register(RelatorioRendimentosModule(_bus, _config, _sessao_fn))
_registry.register(BuscarXMLModule(_bus, _config, _sessao_fn))
_registry.register(SemMovimentoNfseModule(_bus, _config, _sessao_fn))
_registry.register(TffSalvadorModule(_bus, _config, _sessao_fn))

# ── Inicialização ─────────────────────────────────────────────────────────────

api = Api(
    registry=_registry,
    config=_config,
    auth=auth_mod,
    bus=_bus,
    base_dir=BASE_DIR,
    project_root=PROJECT_ROOT,
    window_fn=lambda: window,
)

window = webview.create_window(
    title="Central DMF",
    url=os.path.join(RESOURCES_DIR, "ui", "index.html"),
    js_api=api,
    width=1100,
    height=720,
    min_size=(900, 600),
    resizable=True,
)

if __name__ == "__main__":
    webview.start(debug=False, icon=os.path.join(RESOURCES_DIR, "ui", "logo.ico"))
