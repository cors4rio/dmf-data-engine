"""
logger_cb.py — Logger com handler duplo: arquivo + callback ao frontend.
"""

import logging
import os
import json
from datetime import datetime

_window = None


def set_window(window):
    global _window
    _window = window


class FrontendHandler(logging.Handler):
    """Envia cada registro de log ao JS via evaluate_js."""

    def emit(self, record):
        if _window is None:
            return
        try:
            payload = json.dumps({
                "time":   datetime.now().strftime("%H:%M:%S"),
                "level":  record.levelname,
                "msg":    record.getMessage(),
                "modulo": record.name,
            }, ensure_ascii=False).replace("`", "\\`")
            _window.evaluate_js(f"window._onLog({payload})")
        except Exception:
            pass


def setup_logger(base_dir: str) -> logging.Logger:
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    root = logging.getLogger()
    if root.handlers:           # evita duplicar handlers em recargas
        return logging.getLogger("App")

    root.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    fh = logging.FileHandler(
        os.path.join(logs_dir, "app.log"), encoding="utf-8"
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    fe = FrontendHandler()
    fe.setLevel(logging.INFO)

    root.addHandler(fh)
    root.addHandler(ch)
    root.addHandler(fe)

    return logging.getLogger("App")
