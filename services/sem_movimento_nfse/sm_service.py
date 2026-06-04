"""
services/sem_movimento_nfse/sm_service.py — Orquestra thread, stop_flag e eventos.

Molde: services/buscar_xml/services.py
"""
import os
import sys
import threading
import logging

_HERE       = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(_HERE, "sm_engine")

for _p in (_ENGINE_DIR, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

log = logging.getLogger("SemMovimento.Service")


class SemMovimentoService:

    def __init__(self, on_event_cb, config_fn):
        """
        on_event_cb(evento, dados) — encaminha eventos para o EventBus da Central.
        config_fn()                — retorna o dict de configuração da Central.
        """
        self._on_event  = on_event_cb
        self._config_fn = config_fn
        self._running: dict = {}   # {"lote": threading.Event}
        self._resultados: list = []

    # ── API pública ───────────────────────────────────────────────────────────

    def executar(self, empresas: list, mes: int, ano: int, pasta_destino: str) -> dict:
        if self._running.get("lote") and not self._running["lote"].is_set():
            return {"ok": False, "erro": "Já existe um lote em execução."}

        stop = threading.Event()
        self._running["lote"] = stop
        self._resultados = []

        cfg = self._config_fn()

        t = threading.Thread(
            target=self._run_lote,
            args=(empresas, mes, ano, pasta_destino, stop, cfg),
            daemon=True,
        )
        t.start()
        return {"ok": True}

    def cancelar(self) -> dict:
        stop = self._running.get("lote")
        if stop:
            stop.set()
            log.info("Cancelamento solicitado.")
        return {"ok": True}

    def get_status(self) -> dict:
        ativo = bool(self._running.get("lote") and not self._running["lote"].is_set())
        return {"status": "running" if ativo else "idle"}

    # ── Thread principal ──────────────────────────────────────────────────────

    def _run_lote(self, empresas, mes, ano, pasta_destino, stop, cfg):
        from sm_portal import executar_lote
        from sm_resumo import gerar as gerar_resumo

        def progress_cb(pct, msg, cnpj):
            self._cb("sm_progress", {"pct": pct, "msg": msg, "cnpj": cnpj})

        def empresa_cb(cnpj, status, emitidas, recebidas, detalhe, indice, total):
            resultado = {
                "cnpj":      cnpj,
                "status":    status,
                "emitidas":  emitidas,
                "recebidas": recebidas,
                "detalhe":   detalhe,
                "indice":    indice,
                "total":     total,
            }
            self._resultados.append(resultado)
            self._cb("sm_empresa", resultado)

        resumo_arquivo = None
        try:
            res = executar_lote(
                empresas=empresas,
                mes=mes,
                ano=ano,
                pasta_destino=pasta_destino,
                stop_flag=stop,
                progress_cb=progress_cb,
                empresa_cb=empresa_cb,
                cfg=cfg,
            )

            if self._resultados and not stop.is_set():
                try:
                    resumo_arquivo = gerar_resumo(self._resultados, mes, ano, pasta_destino)
                except Exception as e:
                    log.error(f"Erro ao gerar resumo: {e}")

            self._cb("sm_done", {
                "ok":           res["erros"] == 0,
                "total":        res["total"],
                "ok_count":     res["ok"],
                "erros":        res["erros"],
                "cancelado":    res["cancelado"],
                "resumo_arquivo": resumo_arquivo,
            })

        except Exception as e:
            log.error(f"Erro fatal no lote: {e}")
            self._cb("sm_done", {
                "ok": False, "total": len(empresas),
                "ok_count": 0, "erros": len(empresas),
                "cancelado": False, "resumo_arquivo": None,
                "detalhe": str(e),
            })
        finally:
            self._running.pop("lote", None)

    def _cb(self, evento: str, dados: dict):
        try:
            self._on_event(evento, dados)
        except Exception as e:
            log.error(f"Erro no callback de evento '{evento}': {e}")
