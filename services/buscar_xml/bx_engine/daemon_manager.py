"""
daemon_manager.py — Gerencia os daemons leitura_emails e nfe_arquivos.
Cada daemon roda em thread própria com threading.Event para stop limpo.
"""

import threading
import logging
from datetime import datetime

log = logging.getLogger("DaemonManager")


class DaemonManager:
    def __init__(self):
        self._reg: dict = {}   # nome -> {thread, stop, started_at, last_activity}

    def start(self, nome: str, config: dict = None, on_idle_cb=None, on_error_cb=None) -> dict:
        if nome in self._reg and self._reg[nome]["thread"].is_alive():
            return {"ok": False, "msg": f"'{nome}' já está rodando"}

        config = config or {}
        stop   = threading.Event()

        if nome == "emails":
            from bx_engine.nfe_emails import monitorar_emails
            target = lambda: monitorar_emails(stop_flag=stop, config=config,
                                              on_idle_cb=on_idle_cb, on_error_cb=on_error_cb)
        elif nome == "arquivos":
            from bx_engine.nfe_arquivos import processar_loop
            target = lambda: processar_loop(stop_flag=stop, config=config)
        else:
            return {"ok": False, "msg": f"Daemon desconhecido: '{nome}'"}

        t = threading.Thread(target=target, daemon=True, name=f"dmn_{nome}")
        t.start()

        self._reg[nome] = {
            "thread":        t,
            "stop":          stop,
            "started_at":    datetime.now().isoformat(),
            "last_activity": None,
        }
        log.info(f"Daemon '{nome}' iniciado.")
        return {"ok": True}

    def stop(self, nome: str) -> dict:
        d = self._reg.get(nome)
        if not d:
            return {"ok": False, "msg": f"'{nome}' não registrado"}
        d["stop"].set()
        d["thread"].join(timeout=15)
        alive = d["thread"].is_alive()
        log.info(f"Daemon '{nome}' {'ainda vivo (join timeout)' if alive else 'parado'}.")
        return {"ok": True, "alive_after_stop": alive}

    def update_activity(self, nome: str, info: str = ""):
        if nome in self._reg:
            self._reg[nome]["last_activity"] = {
                "time": datetime.now().isoformat(),
                "info": info,
            }

    def get_status(self, nome: str) -> dict:
        d = self._reg.get(nome)
        if not d:
            return {"nome": nome, "status": "parado", "alive": False,
                    "started_at": None, "last_activity": None}
        alive = d["thread"].is_alive()
        return {
            "nome":          nome,
            "status":        "rodando" if alive else "parado",
            "alive":         alive,
            "started_at":    d["started_at"],
            "last_activity": d["last_activity"],
        }

    def get_all_status(self) -> dict:
        return {
            "emails":   self.get_status("emails"),
            "arquivos": self.get_status("arquivos"),
        }
