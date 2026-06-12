"""
services/tff_salvador/tf_service.py — Orquestra thread, stop_flag e eventos TFF Salvador.

Molde: services/sem_movimento_nfse/sm_service.py
"""
import os
import sys
import threading
import logging

# Em dev: injeta tf_engine/ no sys.path para que tf_portal, tf_planilha etc.
# sejam importáveis como nomes flat. No exe (PyInstaller frozen), os módulos
# tf_* já estão em sys._MEIPASS via pathex — injetar __file__-relativo dentro
# de _internal causaria ImportError.
if not getattr(sys, "frozen", False):
    _HERE       = os.path.dirname(os.path.abspath(__file__))
    _ENGINE_DIR = os.path.join(_HERE, "tf_engine")
    for _p in (_ENGINE_DIR, _HERE):
        if _p not in sys.path:
            sys.path.insert(0, _p)

log = logging.getLogger("TffSalvador.Service")


class TffSalvadorService:

    def __init__(self, on_event_cb, config_fn):
        """
        on_event_cb(evento, dados) — encaminha eventos para o EventBus da Central.
        config_fn()                — retorna o dict de configuração da Central.
        """
        self._on_event  = on_event_cb
        self._config_fn = config_fn
        self._running: dict = {}
        self._resultados: list = []

    # ── API pública ───────────────────────────────────────────────────────────

    def executar(self, clientes: list, ano: int, pasta_destino: str,
                 tipo: str = "TFF") -> dict:
        if self._running.get("lote") and not self._running["lote"].is_set():
            return {"ok": False, "erro": "Já existe um lote em execução."}

        stop = threading.Event()
        self._running["lote"] = stop
        self._resultados = []

        cfg  = self._config_fn()
        tipo = (tipo or "TFF").upper()

        t = threading.Thread(
            target=self._run_lote,
            args=(clientes, ano, pasta_destino, stop, cfg, tipo),
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

    def _run_lote(self, clientes, ano, pasta_destino, stop, cfg, tipo="TFF"):
        def progress_cb(pct, msg, cga):
            self._cb("tf_progress", {"pct": pct, "msg": msg, "cga": cga})

        def cliente_cb(cga, razao_social, cnpj, municipio, status, guias, detalhe, indice, total):
            resultado = {
                "cga":          cga,
                "razao_social": razao_social,
                "cnpj":         cnpj,
                "municipio":    municipio,
                "status":       status,
                "guias":        guias,
                "detalhe":      detalhe,
                "indice":       indice,
                "total":        total,
            }
            self._resultados.append(resultado)
            self._cb("tf_cliente", resultado)

        resumo_arquivo = None
        try:
            from tf_portal import executar_lote
            from tf_resumo import gerar as gerar_resumo
            res = executar_lote(
                clientes=clientes,
                ano=ano,
                pasta_destino=pasta_destino,
                stop_flag=stop,
                progress_cb=progress_cb,
                cliente_cb=cliente_cb,
                cfg=cfg,
                tipo=tipo,
            )

            if self._resultados and not stop.is_set():
                try:
                    resumo_arquivo = gerar_resumo(self._resultados, ano, pasta_destino, tipo)
                except Exception as e:
                    log.error(f"Erro ao gerar resumo: {e}")

            self._cb("tf_done", {
                "ok":             res["erros"] == 0,
                "total":          res["total"],
                "ok_count":       res["ok"],
                "erros":          res["erros"],
                "cancelado":      res["cancelado"],
                "resumo_arquivo": resumo_arquivo,
            })

        except BaseException as e:
            import traceback as _tb
            msg = f"{type(e).__name__}: {e}\n{_tb.format_exc()}"
            log.error(f"Erro fatal no lote: {msg}")
            # Escreve em arquivo temporário para diagnóstico mesmo sem log configurado
            try:
                import tempfile, os as _os
                p = _os.path.join(tempfile.gettempdir(), "dmf_tff_erro.txt")
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(msg)
            except Exception:
                pass
            self._cb("tf_done", {
                "ok": False, "total": len(clientes),
                "ok_count": 0, "erros": len(clientes),
                "cancelado": False, "resumo_arquivo": None,
                "detalhe": msg[:300],
            })
        finally:
            self._running.pop("lote", None)

    def _cb(self, evento: str, dados: dict):
        try:
            self._on_event(evento, dados)
        except Exception as e:
            log.error(f"Erro no callback de evento '{evento}': {e}")
