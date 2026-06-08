"""
engine/notificador.py — Notificações Telegram (preservado do original).
"""

import os
import logging
import requests
from datetime import datetime

log = logging.getLogger("Notificador")


def _token_chat(config: dict = None):
    cfg = (config or {}).get("telegram", {})
    token   = cfg.get("bot_token", "") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = cfg.get("chat_id",   "") or os.getenv("TELEGRAM_CHAT_ID",   "")
    return token, chat_id


def enviar(mensagem: str, config: dict = None, parse_mode: str = "HTML") -> bool:
    token, chat_id = _token_chat(config)
    if not token or not chat_id:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": mensagem, "parse_mode": parse_mode},
            timeout=10,
        )
        return r.status_code == 200
    except Exception as e:
        log.error(f"Telegram: {e}")
        return False


def notificar_inicio(modulo: str, periodo: str = "", config: dict = None):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    enviar(
        f"<b>[INICIO]</b> {modulo}\nPeríodo: {periodo}\nHora: {agora}",
        config,
    )


def notificar_fim(modulo: str, suc: int, err: int,
                  destino: str = "", erros: list = None, config: dict = None):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    tag   = "[OK]" if err == 0 else "[ALERTA]"
    msg   = (f"<b>{tag} {modulo}</b>\nSucessos: {suc}\nErros: {err}"
             f"\nDestino: {destino}\nHora: {agora}")
    if erros:
        msg += "\n\n<b>Erros:</b>\n" + "\n".join(f"- {e}" for e in erros[:10])
        if len(erros) > 10:
            msg += f"\n... e mais {len(erros)-10}"
    enviar(msg, config)


def notificar_erro_critico(modulo: str, mensagem: str, config: dict = None):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    enviar(
        f"<b>[ERRO CRITICO] {modulo}</b>\n{mensagem}\nHora: {agora}",
        config,
    )
