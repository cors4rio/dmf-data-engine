"""
sm_engine/sm_captcha.py — Resolução de CAPTCHA de imagem via Anti-Captcha.

API: https://anti-captcha.com/apidoc/image-to-text
  1. POST /createTask  com base64 da imagem → retorna taskId
  2. POST /getTaskResult com taskId → polling até status "ready" ou erro
"""
import time
import base64
import logging
import requests

log = logging.getLogger("SemMovimento.Captcha")

URL_BASE   = "https://api.anti-captcha.com"
URL_CREATE = f"{URL_BASE}/createTask"
URL_RESULT = f"{URL_BASE}/getTaskResult"

POLL_INTERVAL_S = 5
MAX_ERROS       = 3


def resolver(img_bytes: bytes, api_key: str, timeout_s: int = 60) -> str:
    """
    Envia a imagem do CAPTCHA para o Anti-Captcha e retorna o texto resolvido.
    Levanta RuntimeError em caso de falha (timeout, API error, chave inválida etc.).
    """
    if not api_key:
        raise RuntimeError("Anti-Captcha: chave de API não configurada (sm_anticaptcha_api_key)")

    img_b64 = base64.b64encode(img_bytes).decode()

    # 1. Cria a tarefa
    resp = requests.post(URL_CREATE, json={
        "clientKey": api_key,
        "task": {
            "type": "ImageToTextTask",
            "body": img_b64,
        },
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if data.get("errorId", 0) != 0:
        raise RuntimeError(f"Anti-Captcha createTask erro: {data.get('errorCode')} — {data.get('errorDescription')}")

    task_id = data["taskId"]
    log.info(f"Anti-Captcha: tarefa criada — taskId={task_id}")

    # 2. Polling até resolver ou timeout
    deadline = time.time() + timeout_s
    erros    = 0
    time.sleep(POLL_INTERVAL_S)  # espera inicial antes do primeiro poll

    while time.time() < deadline:
        try:
            resp = requests.post(URL_RESULT, json={
                "clientKey": api_key,
                "taskId":    task_id,
            }, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            erros += 1
            log.warning(f"Anti-Captcha poll erro ({erros}/{MAX_ERROS}): {e}")
            if erros >= MAX_ERROS:
                raise RuntimeError(f"Anti-Captcha: {MAX_ERROS} erros consecutivos de rede") from e
            time.sleep(POLL_INTERVAL_S)
            continue

        erros = 0

        if data.get("errorId", 0) != 0:
            raise RuntimeError(f"Anti-Captcha erro: {data.get('errorCode')} — {data.get('errorDescription')}")

        if data.get("status") == "ready":
            texto = data["solution"]["text"]
            log.info(f"Anti-Captcha: resolvido → {texto!r}")
            return texto

        # status == "processing" — ainda não pronto
        time.sleep(POLL_INTERVAL_S)

    raise RuntimeError(f"Anti-Captcha: timeout após {timeout_s}s sem resposta")
