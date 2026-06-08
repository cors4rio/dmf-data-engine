"""
engine/sped.py
Geração e download de SPED Fiscal via ERP Bluesoft.
Fonte: AGROMIX_ATACADAO/SPED/main.py
Adições: stop_flag, progress_cb, lojas/periodo como parâmetros, config.json.
PRESERVADO: login async Playwright, polling Drive, download S3, extração ZIP.
"""

import asyncio
import io
import os
import re
import time
import logging
import threading
import zipfile
import requests
from playwright.async_api import async_playwright

log = logging.getLogger("SPED")

URL_LOGIN  = "https://erp.bluesoft.com.br/agromixatalaia/seguranca/login/login"
URL_DRIVE  = "https://erp.bluesoft.com.br/agromixatalaia/ferramentas/drive/listarArquivos.action"
URL_GERAR  = "https://erp.bluesoft.com.br/agromixatalaia//contabil/spedFiscal/gerar.action"
URL_INDEX  = "https://erp.bluesoft.com.br/agromixatalaia//contabil/spedFiscal/index.action"
URL_COMP   = "https://erp.bluesoft.com.br/agromixatalaia//contabil/spedFiscal/listarCompetencias.action"
URL_INV    = "https://erp.bluesoft.com.br/agromixatalaia//contabil/spedFiscal/listarInventarios.action"


# ── autenticação (async Playwright) ─────────────────────────────────────────

async def _login_async(config: dict, progress_cb) -> requests.Session:
    usuario = config.get("erp", {}).get("usuario", "icaro.dmf")
    senha   = config.get("erp", {}).get("senha", "") or os.getenv("BLUESOFT_PASS", "")
    if not senha:
        raise ValueError("Senha ERP não configurada.")

    progress_cb(5, "SPED: autenticando no ERP...", "")
    session = requests.Session()
    session.headers.update({
        "User-Agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "Accept":           "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Origin":           "https://erp.bluesoft.com.br",
        "Referer":          "https://erp.bluesoft.com.br/agromixatalaia//contabil/spedFiscal/index.action",
    })

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx     = await browser.new_context()
        page    = await ctx.new_page()

        await page.goto(URL_LOGIN)
        await page.locator("#j_username").fill(usuario)
        await page.locator("#j_password").fill(senha)
        await page.get_by_role("button", name="Entrar").click()

        progress_cb(12, "SPED: aguardando validação de credenciais...", "")
        try:
            await page.wait_for_load_state("networkidle", timeout=45_000)
        except Exception:
            pass
        await page.wait_for_timeout(5_000)

        for c in await ctx.cookies():
            session.cookies.set(c["name"], c["value"], domain=c["domain"])

        await browser.close()

    if len(session.cookies) == 0:
        raise Exception("ERP não liberou cookies para SPED.")

    progress_cb(15, f"Login SPED OK — {len(session.cookies)} cookies", "")
    return session


# ── disparo de geração ───────────────────────────────────────────────────────

def _gerar_sped(session: requests.Session, loja_key: str, competencia: str) -> bool:
    resp_idx = session.get(URL_INDEX)
    agendamento_id = "690dff074c238735902389b6"  # fallback
    m = re.search(r'value="([a-f0-9]{24})"|agendamentoId["\':\s]+([a-f0-9]{24})',
                  resp_idx.text)
    if m:
        agendamento_id = m.group(1) or m.group(2)

    session.get(f"{URL_COMP}?lojaKey={loja_key}")
    session.get(f"{URL_INV}?lojaKey={loja_key}")

    data = {
        "tarefa":                    "SPED_FISCAL_ICMS",
        "SPED_FISCAL_ICMS":          agendamento_id,
        "SPED_FISCAL_CONTRIBUICOES": "",
        "agendamentoId":             agendamento_id,
        "tipoArquivoKey":            "7",
        "tipoDeEscrituracao":        "ORIGINAL",
        "finalidadeDoArquivoCommons":"REMESSA_DO_ARQUIVO_ORIGINAL",
        "numeroDaEscrituracaoAnteriorASerRetificada": "",
        "lojaKey":                   str(loja_key),
        "competenciaKey":            competencia,
        "informacoesComplementares['codigoDeAjusteSaidaIsento']": "-1",
        "informacoesComplementares['codigoDeAjusteSaidaOutros']": "-1",
        "tipoInventarioKey":         "0",
        "tipoInventarioBlocoKKey":   "0",
        "movimentosExtemporaneos":   "on",
    }
    resp = session.post(URL_GERAR, data=data)
    return resp.status_code in (200, 302, 204)


# ── polling Drive + download S3 ──────────────────────────────────────────────

def _monitorar_e_baixar(session: requests.Session, loja_key: str, nome_alvo: str,
                        mes_ano: str, pasta_final_sped: str,
                        stop_flag: threading.Event,
                        max_tent: int, seg_espera: int) -> tuple:
    payload = {
        "nome": "", "local": "/", "diretorioKey": 1,
        "gruposAcessoKeys": [], "lojaKey": str(loja_key),
        "pagination": {"currentPage": 0},
    }

    for tent in range(max_tent):
        if stop_flag.is_set():
            return False, "Cancelado"
        try:
            resp = session.post(URL_DRIVE, json=payload)
            if resp.status_code != 200:
                time.sleep(seg_espera)
                continue

            for item in resp.json().get("result", []):
                nome_item = item.get("nome", "").lower()
                if nome_alvo.lower() in nome_item and ".zip" in nome_item:
                    url_s3 = item.get("tempUrl")
                    log.info(f"SPED: arquivo encontrado no Drive: {nome_item}")
                    return _baixar_s3(url_s3, loja_key, mes_ano, pasta_final_sped)

        except Exception as e:
            log.error(f"SPED polling Drive: {e}")

        log.info(f"SPED loja {loja_key}: tentativa {tent+1}/{max_tent} — aguardando {seg_espera}s...")
        time.sleep(seg_espera)

    return False, f"Timeout: arquivo não apareceu no Drive após {max_tent} tentativas"


def _baixar_s3(url_s3: str, loja_key: str, mes_ano: str,
               pasta_final_sped: str) -> tuple:
    from bx_config.lojas import LOJAS_CADASTRO, BLUESOFT_PARA_CODIGO
    codigo    = BLUESOFT_PARA_CODIGO.get(str(loja_key), "")
    loja_info = LOJAS_CADASTRO.get(codigo, {})
    apelido   = loja_info.get("apelido", f"LOJA_{loja_key}")
    pasta_nome = f"{codigo}-{apelido}" if codigo else f"LOJA_{loja_key}_DESCONHECIDA"
    destino   = os.path.join(pasta_final_sped, pasta_nome, mes_ano)

    try:
        if os.path.exists(destino):
            import shutil
            for item in os.listdir(destino):
                c = os.path.join(destino, item)
                try:
                    if os.path.isfile(c):
                        os.remove(c)
                    else:
                        shutil.rmtree(c)
                except Exception:
                    pass
        else:
            os.makedirs(destino, exist_ok=True)

        r = requests.get(url_s3, stream=True, timeout=300)
        r.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            lista = zf.namelist()
            zf.extractall(destino)

        log.info(f"SPED: {len(lista)} arquivo(s) extraídos em {destino}")
        return True, f"{len(lista)} arquivo(s) extraídos"
    except Exception as e:
        return False, f"Falha no download/extração S3: {e}"


# ── executor principal ───────────────────────────────────────────────────────

def executar_sped(lojas: list, periodo: dict, stop_flag: threading.Event,
                  progress_cb, config: dict = None) -> dict:
    """
    lojas: [{"codigo","apelido","id_bluesoft"}, ...]
    periodo: {"competencia":"MM-YYYY","comp_formatada":"YYYYMM","mes_ano":"MMYYYY"}
    """
    config   = config or {}
    cfg_sped = config.get("sped", {})
    max_tent = int(cfg_sped.get("timeout_drive_tentativas", 30))
    seg_esp  = int(cfg_sped.get("timeout_drive_segundos",   20))
    pasta_final = config.get("paths", {}).get("sped", r"Z:\#ROTINA AUTOMATICA NF\SPED")

    # Normaliza periodo: aceita tanto o formato legado {competencia, comp_formatada, mes_ano}
    # quanto o formato do bxGetPeriodo {data_inicio, data_fim, mes_ano:"MMYYYY"}.
    mes_ano = periodo.get("mes_ano", "")  # "MMYYYY"
    if "competencia" not in periodo and len(mes_ano) == 6:
        mm, yyyy = mes_ano[:2], mes_ano[2:]
        periodo = dict(periodo)
        periodo["competencia"]    = f"{mm}-{yyyy}"   # MM-YYYY (formato ERP)
        periodo["comp_formatada"] = f"{yyyy}{mm}"    # YYYYMM  (nome de arquivo Drive)

    # Login via async Playwright
    session = asyncio.run(_login_async(config, progress_cb))

    total = len(lojas)
    suc = err = 0

    for i, loja in enumerate(lojas):
        if stop_flag.is_set():
            progress_cb(None, "Cancelado pelo usuário.", "")
            break

        loja_key = loja.get("id_bluesoft")
        nome     = loja.get("apelido", loja.get("codigo", "?"))

        if not loja_key:
            continue

        pct = 15 + int((i / total) * 78)
        progress_cb(pct, f"SPED: disparando geração para {nome}...", nome)
        log.info(f"SPED: loja {nome} (key={loja_key})")

        try:
            # 1. Disparo de geração
            ok_disp = _gerar_sped(session, loja_key, periodo["competencia"])
            if not ok_disp:
                err += 1
                log.warning(f"SPED: falha ao disparar geração para {nome}")
                continue

            progress_cb(pct, f"SPED: aguardando Drive — {nome}...", nome)

            # 2. Polling Drive + download S3
            nome_alvo = f"mes{periodo['comp_formatada']}-loja{loja_key}"
            ok_dl, msg = _monitorar_e_baixar(
                session, loja_key, nome_alvo,
                periodo["mes_ano"], pasta_final,
                stop_flag, max_tent, seg_esp,
            )
            if ok_dl:
                suc += 1
                log.info(f"SPED OK: {nome} — {msg}")
            else:
                err += 1
                log.warning(f"SPED ERRO: {nome} — {msg}")
            progress_cb(pct, f"{nome}: {msg}", nome)

        except Exception as e:
            err += 1
            log.error(f"SPED FALHA: {nome} — {e}")

        time.sleep(2)

    progress_cb(100, f"Concluído: {suc} ok, {err} erros", "")
    return {"sucessos": suc, "erros": err}
