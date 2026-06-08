"""
dmf_engine/core/thread_runner.py
ThreadRunner — elimina o padrão _run() nested duplicado em cada método da Api.
"""
import threading
import logging

log = logging.getLogger("ThreadRunner")


class ThreadRunner:
    """
    Executa uma função em thread daemon e despacha resultados via EventBus.

    Antes: cada método da Api definia um _run() nested com try/except e
    threading.Thread(target=_run, daemon=True).start() duplicado ~5 vezes.

    Agora: ThreadRunner.run(module_id, fn, *args) cuida de tudo.
    - Sucesso  → bus.emit(module_id, "done",  resultado)
    - Exceção  → bus.emit(module_id, "erro",  {"msg": str(e)})
    """

    def __init__(self, bus):
        self._bus = bus  # EventBus

    def run(self, module_id: str, fn, *args, **kwargs) -> threading.Thread:
        def _target():
            try:
                result = fn(*args, **kwargs)
                payload = result if isinstance(result, dict) else {"ok": bool(result)}
                self._bus.emit(module_id, "done", payload)
            except Exception as e:
                log.error(f"[{module_id}] Exceção no ThreadRunner: {e}", exc_info=True)
                self._bus.emit(module_id, "erro", {"msg": str(e)})

        t = threading.Thread(target=_target, daemon=True, name=f"dmf-{module_id}")
        t.start()
        return t
