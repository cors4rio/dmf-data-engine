"""
services/automacao_horas/ah_launcher.py

Abre a janela da Automação de Horas DENTRO do processo da Central (64-bit),
sem subprocesso e sem token SSO por arquivo. A sessão da Central é passada
direto para a Api de Horas.

Pré-requisito: a Central já chamou webview.start() (único por processo).
PyWebView permite múltiplas webview.create_window() compartilhando esse start.
Ver memória migracao-horas-inline.

Uso (a partir do adaptador m_automacao_horas.py):
    from ah_launcher import abrir_janela_horas
    abrir_janela_horas(sessao=sessao_atual_da_central)
"""
import os
import sys
import logging

log = logging.getLogger("AutomacaoHoras.Launcher")

_HERE = os.path.dirname(os.path.abspath(__file__))

# Janela única: se já estiver aberta, foca em vez de abrir outra.
_janela_horas = None


def _garantir_path():
    """Injeta o diretório do automacao_horas no sys.path para resolver ah_*."""
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    raiz = os.path.dirname(os.path.dirname(_HERE))  # repo root
    if raiz not in sys.path:
        sys.path.insert(0, raiz)


def abrir_janela_horas(sessao: dict | None = None) -> dict:
    """
    Constrói o stack ah_* e abre a janela de Horas no processo atual.

    sessao: dict da sessão já autenticada na Central (SSO direto, sem token).
            Se None, a UI de Horas faz login manual.

    Retorna {"ok": bool, "erro"?: str}.
    """
    global _janela_horas
    import webview

    # Se a janela já existe e está viva, foca nela em vez de duplicar.
    if _janela_horas is not None:
        try:
            if _janela_horas in webview.windows:
                log.info("Janela de Horas já aberta — focando.")
                try:
                    _janela_horas.show()
                except Exception:
                    pass
                return {"ok": True, "msg": "Janela de Horas já estava aberta."}
        except Exception:
            pass
        _janela_horas = None

    _garantir_path()

    try:
        from ah_core.config import ConfigManager
        from ah_core.event_bus import EventBus
        from ah_core.thread_runner import ThreadRunner
        from ah_modules.registry import ModuleRegistry
        from ah_modules.m_fiscal import FiscalModule
        from ah_modules.m_dp import DPModule
        from ah_modules.m_contabil import ContabilModule
        from ah_api import Api
        import ah_compat
        import ah_auth
    except Exception as e:
        log.error("Falha ao importar o stack ah_*: %s", e)
        return {"ok": False, "erro": f"Falha ao carregar a Automação de Horas: {e}"}

    # Resolução de caminhos compatível com frozen (PyInstaller):
    #   - UI (read-only) vem do bundle: _MEIPASS/services/automacao_horas/ui
    #   - config.json (escrita) fica ao lado do exe (BASE_DIR), não no bundle
    if getattr(sys, "frozen", False):
        base_dir      = os.path.dirname(sys.executable)
        resources_dir = os.path.join(sys._MEIPASS, "services", "automacao_horas")
    else:
        base_dir      = _HERE
        resources_dir = _HERE
    config_file = os.path.join(base_dir, "config.json")

    _config = ConfigManager(config_file)

    # Aplica credenciais DSN-less no singleton db do stack de Horas.
    try:
        ah_compat.db.configurar_de_cfg(_config.load())
    except Exception as e:
        log.error("[BOOT] Falha ao configurar DB de Horas: %s", e)

    # A janela é preenchida abaixo; o EventBus e a Api a acessam via closure.
    estado = {"window": None}

    _bus     = EventBus(lambda: estado["window"])
    _runner  = ThreadRunner(_bus)
    _registry = ModuleRegistry(_runner)

    api_ref = {"api": None}

    def _sessao_fn():
        return api_ref["api"]._sessao if api_ref["api"] else None

    _registry.register(FiscalModule(_bus, _config, _sessao_fn))
    _registry.register(DPModule(_bus, _config, _sessao_fn))
    _registry.register(ContabilModule(_bus, _config, _sessao_fn))

    api = Api(
        registry=_registry,
        config=_config,
        auth=ah_auth,
        bus=_bus,
        base_dir=base_dir,
        project_root=ah_compat.PROJECT_ROOT,
        window_fn=lambda: estado["window"],
        sessao_inicial=sessao,   # SSO direto: a sessão da Central
    )
    api_ref["api"] = api

    try:
        janela = webview.create_window(
            title="DMF — Automação de Horas",
            url=os.path.join(resources_dir, "ui", "index.html"),
            js_api=api,
            width=1100,
            height=720,
            min_size=(900, 600),
            resizable=True,
        )
    except Exception as e:
        log.error("Falha ao criar a janela de Horas: %s", e)
        return {"ok": False, "erro": f"Não foi possível abrir a janela: {e}"}

    estado["window"]   = janela
    ah_compat.window   = janela
    _janela_horas      = janela

    # Limpa a referência quando a janela fechar, permitindo reabrir depois.
    def _on_closed():
        global _janela_horas
        _janela_horas = None
        estado["window"] = None

    try:
        janela.events.closed += _on_closed
    except Exception:
        pass

    log.info("Janela de Horas aberta no processo da Central (sessão: %s).",
             sessao.get("nome") if sessao else "login manual")
    return {"ok": True, "msg": "Automação de Horas aberta."}
