"""
engine/nfe_disparo.py
Lógica de disparo de NF-e no ERP Bluesoft.
Fonte: AGROMIX_ATACADAO/DOWNLOAD NFE/disparo_nfe_oficial.py
Adições: stop_flag, progress_cb, lojas/periodo como parâmetros, config.json.
PRESERVADO: autenticação Playwright híbrida, payloads de pesquisa e envio.
"""

import os
import re
import logging
import threading
import requests
from playwright.sync_api import sync_playwright
from .bx_playwright_compat import configurar_browsers_path, policy_proactor

log = logging.getLogger("NFE_Disparo")

URL_LOGIN    = "https://erp.bluesoft.com.br/agromixatalaia/seguranca/login/login"
URL_PESQUISA = "https://erp.bluesoft.com.br/agromixatalaia/comercial/consultaNotaFiscal/listar.action"
URL_ENVIO    = "https://erp.bluesoft.com.br/agromixatalaia/comercial/notaFiscalEletronicaEnvio/enviarVariasNotasPorEmail.action"

HEADERS = {
    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept":       "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin":       "https://erp.bluesoft.com.br",
    "Referer":      "https://erp.bluesoft.com.br/agromixatalaia/comercial/consultaNotaFiscal/index.action",
}


def _capturar_sessao(config: dict, progress_cb) -> requests.Session:
    """Playwright faz login, sequestra cookies, retorna requests.Session."""
    usuario = config.get("erp", {}).get("usuario", "icaro.dmf")
    senha   = config.get("erp", {}).get("senha", "") or os.getenv("BLUESOFT_PASS", "")
    if not senha:
        raise ValueError("Senha ERP não configurada em config.json (erp.senha) nem em BLUESOFT_PASS.")

    progress_cb(8, "Iniciando Chromium para autenticação no ERP...", "")
    sessao = requests.Session()
    sessao.headers.update(HEADERS)

    configurar_browsers_path()
    with policy_proactor(), sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx     = browser.new_context(user_agent=HEADERS["User-Agent"])
        page    = ctx.new_page()
        page.set_default_timeout(60_000)

        page.goto(URL_LOGIN)
        page.locator("#j_username").fill(usuario)
        page.locator("#j_password").fill(senha)
        page.get_by_role("button", name="Entrar").click()

        progress_cb(18, "Aguardando autorização do servidor ERP...", "")
        try:
            page.wait_for_load_state("networkidle", timeout=45_000)
        except Exception:
            pass
        page.wait_for_timeout(5_000)

        for c in ctx.cookies():
            sessao.cookies.set(c["name"], c["value"],
                               domain=c["domain"], path=c["path"])
        browser.close()

    if len(sessao.cookies) == 0:
        raise Exception("ERP não liberou cookies válidos após o login.")

    progress_cb(22, f"Login OK — {len(sessao.cookies)} cookies de sessão", "")
    return sessao


def _disparar_loja(nome: str, loja_key: str, dt_ini: str, dt_fim: str,
                   session: requests.Session, email_destino: str):
    """Pesquisa NF-e da loja e dispara e-mail de exportação. Retorna (ok, msg)."""
    payload_pesq = {
        "lgpdExibirDadosPessoais": "",
        "ordenacaoParaEntrada": "nf.dataEmissao asc, notaFiscalTotal.valorTotalNota asc",
        "ordenacaoParaSaida":   "nf.dataEmissao asc, notaFiscalTotal.valorTotalNota asc",
        "tabNumero": "0", "tipoConsulta": "1",
        "selecionaEntradaRecebimnetoDeMercadorias": "false",
        "lojaKey": str(loja_key), "nomeDestinatario": "",
        "dataInicial": dt_ini, "dataFinal": dt_fim,
        "chave": "", "nfNumero": "", "valor": "0,00",
        "cfopKey": "0", "notaFiscalTipoKey": "0",
        "statusReferencia": "TODAS", "statusCancelamento": "TODOS",
        "statusCartaDeCorrecao": "0", "tipoStatusNfeKey": "0",
        "protocoloAutorizacao": "", "statusEmail": "0",
        "statusEmailNotaFiscalCancelada": "0",
        "ordenar": "nf.dataEmissao,notaFiscalTotal.valorTotalNota",
    }

    try:
        r_pesq = session.post(URL_PESQUISA, data=payload_pesq, timeout=90)
        if r_pesq.status_code != 200:
            return False, f"HTTP {r_pesq.status_code} na pesquisa"

        matches  = re.findall(
            r'name="nfKeys"\s*value="(\d+)"|value="(\d+)"\s*name="nfKeys"'
            r'|nfKeys.*?value="(\d+)"|value="(\d+)".*?nfKeys',
            r_pesq.text, re.IGNORECASE,
        )
        nf_keys  = set(item for m in matches for item in m if item)

        if not nf_keys:
            return True, "Sem NF-e no período"

        payload_envio = [("emailNfe", email_destino), ("emailCopiaNfe", "")]
        for k in nf_keys:
            payload_envio.append(("nfKeys", k))

        r_envio = session.post(URL_ENVIO, data=payload_envio, timeout=180)
        if r_envio.status_code == 200:
            return True, f"{len(nf_keys)} notas disparadas"
        else:
            return False, f"HTTP {r_envio.status_code} no envio"

    except Exception as e:
        return False, f"Exceção: {e}"


def executar_nfe(lojas: list, periodo: dict, stop_flag: threading.Event,
                 progress_cb, config: dict = None) -> dict:
    """
    lojas: [{"codigo","apelido","id_bluesoft"}, ...]
    periodo: {"data_inicio":"DD/MM/YYYY","data_fim":"DD/MM/YYYY","mes_ano":"MMYYYY"}
    """
    config         = config or {}
    email_destino  = config.get("erp", {}).get("email_destino", "dmfautomacoes@gmail.com")

    sessao = _capturar_sessao(config, progress_cb)

    dt_ini = periodo["data_inicio"]
    dt_fim = periodo["data_fim"]
    total  = len(lojas)
    suc = err = 0
    # Lojas que realmente dispararam NF-e (terão ZIP para chegar)
    lojas_aguardando: list = []

    for i, loja in enumerate(lojas):
        if stop_flag.is_set():
            progress_cb(None, "Cancelado pelo usuário.", "")
            break

        nome     = loja.get("apelido", loja.get("codigo", "?"))
        loja_key = loja.get("id_bluesoft")
        if not loja_key:
            log.warning(f"Loja '{nome}' sem id_bluesoft — ignorada.")
            continue

        # Dispatch ocupa 22..50% — sobrando 50..100% para o aguardo dos arquivos
        pct = 22 + int((i / total) * 28)
        progress_cb(pct, f"Disparando {nome}...", nome)
        log.info(f"NFe disparo: {nome} (key={loja_key})")

        try:
            ok, msg = _disparar_loja(nome, loja_key, dt_ini, dt_fim, sessao, email_destino)
            if ok:
                suc += 1
                log.info(f"OK: {nome} — {msg}")
                # Se realmente disparou notas, esperamos o ZIP dessa loja
                if "disparadas" in msg.lower():
                    lojas_aguardando.append({
                        "codigo":  loja.get("codigo"),
                        "apelido": nome,
                    })
            else:
                err += 1
                log.warning(f"ERRO: {nome} — {msg}")
            progress_cb(pct, f"{nome}: {msg}", nome)
        except Exception as e:
            err += 1
            log.error(f"FALHA: {nome} — {e}")

        # sleep interrompível: respeita stop_flag de imediato
        if stop_flag.wait(timeout=3):
            progress_cb(None, "Cancelado pelo usuário.", "")
            break

    progress_cb(
        50,
        f"Disparo: {suc} ok, {err} erros. Aguardando {len(lojas_aguardando)} ZIP(s) chegarem por e-mail...",
        "",
    )
    return {
        "sucessos":         suc,
        "erros":            err,
        "aguardando_email": True,
        "lojas_aguardando": lojas_aguardando,
    }


def testar_login(config: dict) -> dict:
    """Testa autenticação sem disparar nada."""
    try:
        s = _capturar_sessao(config, lambda *a: None)
        return {"ok": True, "msg": f"Login OK — {len(s.cookies)} cookies"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}
