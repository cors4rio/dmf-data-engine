"""
engine/nfe_emails.py
Daemon IMAP — monitora e-mails do ERP Bluesoft e baixa ZIPs de NF-e.
Fonte: AGROMIX_ATACADAO/DOWNLOAD NFE/leitura_emails.py
Adições: stop_flag (threading.Event), config como parâmetro.
PRESERVADO: log por Message-ID (RFC 5322), deduplicação, JSON persistente.
"""

import os
import re
import email
import json
import hashlib
import imaplib
import logging
import threading
import time
from email.header import decode_header
from datetime import datetime

log = logging.getLogger("NFE_Emails")


# ── log persistente de Message-IDs ──────────────────────────────────────────

def _carregar_log(log_file: str) -> dict:
    if not os.path.exists(log_file):
        return {}
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_log(log_dict: dict, log_file: str):
    tmp = log_file + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(log_dict, f, indent=2, ensure_ascii=False)
        os.replace(tmp, log_file)
    except Exception as e:
        log.error(f"Falha ao salvar email_log.json: {e}")


def _sanitizar_mid(raw: str) -> str:
    mid = (raw or "").strip()
    m = re.search(r"<([^>]+)>", mid)
    if m:
        return m.group(1).lower()
    return hashlib.md5(mid.encode()).hexdigest()


# ── helpers IMAP ─────────────────────────────────────────────────────────────

def _obter_data_imap() -> str:
    meses = ["Jan","Feb","Mar","Apr","May","Jun",
             "Jul","Aug","Sep","Oct","Nov","Dec"]
    hoje = datetime.now()
    return f"{hoje.day:02d}-{meses[hoje.month-1]}-{hoje.year}"


def _decodificar_assunto(raw: str) -> str:
    dec, charset = decode_header(raw)[0]
    if isinstance(dec, bytes):
        return dec.decode(charset or "utf-8", errors="ignore")
    return dec or ""


# ── loop principal ───────────────────────────────────────────────────────────

def monitorar_emails(stop_flag: threading.Event, config: dict = None, on_idle_cb=None, download_dir: str = ""):
    config     = config or {}
    _dl_dir    = download_dir or config.get("_download_dir") or \
                 os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads")
    _log_file  = os.path.join(_dl_dir, "email_log.json")
    imap_cfg   = config.get("imap", {})
    servidor   = imap_cfg.get("servidor", "imap.gmail.com")
    porta      = int(imap_cfg.get("porta", 993))
    usuario    = imap_cfg.get("usuario", "") or os.getenv("EMAIL_USUARIO", "")
    senha      = imap_cfg.get("senha",    "") or os.getenv("EMAIL_SENHA",   "")
    idle_max   = int(imap_cfg.get("idle_max_ciclos", 5))

    os.makedirs(_dl_dir, exist_ok=True)
    log_proc = _carregar_log(_log_file)
    log.info(f"Daemon emails iniciado. {len(log_proc)} Message-IDs já registrados.")

    idle_ciclos = 0

    try:
        mail = imaplib.IMAP4_SSL(servidor, porta)
        mail.login(usuario, senha)
        log.info("IMAP: login realizado.")

        while not stop_flag.is_set():
            novos_neste_ciclo = 0
            try:
                mail.select("inbox")
                data_b = _obter_data_imap()
                # UNSEEN: ignora e-mails já lidos (evita reprocesso quando
                # email_log.json é perdido/limpo). Quando há novo anexo,
                # mail.store(..., "\\Seen") marca como lido ao final.
                status, msgs = mail.search(
                    None,
                    f'(UNSEEN SINCE "{data_b}" FROM "erp@bluesoft.com.br" SUBJECT "Agromix Atalaia")'
                )
                if status != "OK":
                    time.sleep(30)
                    continue

                for eid in (msgs[0].split() if msgs[0] else []):
                    if stop_flag.is_set():
                        break
                    # busca só cabeçalhos
                    s2, hdr = mail.fetch(eid, "(BODY[HEADER.FIELDS (MESSAGE-ID SUBJECT)])")
                    if s2 != "OK":
                        continue
                    raw_hdr = b""
                    for part in hdr:
                        if isinstance(part, tuple):
                            raw_hdr = part[1]
                    msg_hdr = email.message_from_bytes(raw_hdr)
                    mid     = _sanitizar_mid(msg_hdr.get("Message-ID", ""))

                    if mid in log_proc:
                        continue

                    assunto = _decodificar_assunto(msg_hdr.get("Subject", ""))
                    log.info(f"Novo e-mail | MID: {mid} | {assunto}")

                    s3, msg_data = mail.fetch(eid, "(RFC822)")
                    if s3 != "OK":
                        continue

                    # Nome de arquivo NEUTRO (sem mês): o mes_ano correto é
                    # derivado depois pelo XML em nfe_arquivos._derivar_mes_ano().
                    mid_hash  = mid[:12].replace("/","_").replace("@","_")
                    nome_arq  = f"Carga_NFe_ERP_{mid_hash}.zip"
                    caminho   = os.path.join(_dl_dir, nome_arq)

                    baixado = False
                    for rp in msg_data:
                        if not isinstance(rp, tuple):
                            continue
                        msg_obj = email.message_from_bytes(rp[1])
                        for part in msg_obj.walk():
                            if part.get_content_maintype() == "multipart":
                                continue
                            if part.get("Content-Disposition") is None:
                                continue
                            n_anexo = part.get_filename()
                            if n_anexo and n_anexo.endswith(".zip"):
                                with open(caminho, "wb") as f:
                                    f.write(part.get_payload(decode=True))
                                log.info(f"ZIP salvo: {caminho}")
                                log_proc[mid] = {"arquivo": nome_arq,
                                                 "data": datetime.now().isoformat()}
                                _salvar_log(log_proc, _log_file)
                                baixado = True
                                novos_neste_ciclo += 1
                                break
                        if baixado:
                            break

                    if not baixado:
                        log.warning(f"E-mail {mid} sem anexo ZIP.")
                        log_proc[mid] = {"arquivo": "SEM_ANEXO",
                                         "data": datetime.now().isoformat()}
                        _salvar_log(log_proc)

                    mail.store(eid, "+FLAGS", "\\Seen")

            except Exception as e:
                log.error(f"Emails loop: {e}")

            # Contagem de ciclos idle para auto-encerramento da sessão
            if novos_neste_ciclo == 0:
                idle_ciclos += 1
                if idle_ciclos >= idle_max:
                    log.info(f"Daemon emails: {idle_ciclos} ciclos sem novos e-mails — encerrando sessão.")
                    if on_idle_cb:
                        on_idle_cb()
                    break
            else:
                idle_ciclos = 0

            stop_flag.wait(timeout=60)

    except Exception as e:
        log.error(f"Daemon emails falhou: {e}")
    finally:
        try:
            mail.logout()
        except Exception:
            pass
        log.info("Daemon emails encerrado.")
