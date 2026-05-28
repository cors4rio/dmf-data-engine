"""
dmf_engine/core/event_bus.py
Canal único Python → JS.
Substitui todos os window.evaluate_js espalhados na classe Api.
"""
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

log = logging.getLogger("EventBus")


# ── Serializador JSON robusto (mesmo de main.py, centralizado aqui) ──────────

def _json_default(o):
    if isinstance(o, datetime):
        return o.isoformat()
    if isinstance(o, timedelta):
        return str(o)
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, bytes):
        return o.decode("utf-8", errors="replace")
    if isinstance(o, set):
        return list(o)
    return str(o)


def json_safe(obj, **kwargs) -> str:
    return json.dumps(obj, default=_json_default, ensure_ascii=False, **kwargs)


# ── EventBus ─────────────────────────────────────────────────────────────────

class EventBus:
    """
    Único canal de comunicação Python → JS.

    Todos os módulos chamam bus.emit(module_id, event, data) em vez de
    window.evaluate_js() diretamente — desacopla os módulos da janela PyWebView.

    O JS recebe via:
        window.__onEvent({ module, event, data })

    Retrocompatibilidade (wrappers deprecated durante transição):
        bus.legacy("window.fiscalIndividualConcluido", data)
    """

    def __init__(self, window_getter):
        self._get_win = window_getter  # callable → janela PyWebView atual

    def emit(self, module_id: str, event: str, data: dict = None):
        payload = json_safe({"module": module_id, "event": event, "data": data or {}})
        payload = payload.replace("`", "\\`")
        try:
            win = self._get_win()
            if win:
                win.evaluate_js(f"window.__onEvent({payload})")
        except Exception as e:
            log.debug(f"EventBus.emit falhou ({module_id}.{event}): {e}")

    def progress(self, module_id: str, pct: int, msg: str):
        self.emit(module_id, "progress", {"pct": pct, "msg": msg})

    def legacy(self, js_callback: str, data: dict = None):
        """
        Retrocompatibilidade: dispara callback JS nomeado diretamente.
        Ex: bus.legacy("window.fiscalIndividualConcluido", resultado)
        Usar apenas em wrappers deprecated até migração completa do index.html.
        """
        payload = json_safe(data or {})
        payload = payload.replace("`", "\\`")
        try:
            win = self._get_win()
            if win:
                win.evaluate_js(f"{js_callback}({payload})")
        except Exception as e:
            log.debug(f"EventBus.legacy falhou ({js_callback}): {e}")
