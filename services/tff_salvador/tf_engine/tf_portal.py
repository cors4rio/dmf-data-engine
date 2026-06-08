"""
tf_engine/tf_portal.py — Automação Playwright do portal TFF Salvador.

Portal: https://www2.sefaz.salvador.ba.gov.br/servico/2-via-tff-tll
O formulário real está dentro de um iframe:
  https://servicosweb.sefaz.salvador.ba.gov.br/sistema/dam/TFF/servicos_DamTFF.asp

CAPTCHA: é falso. O valor correto está em input[name="form2"] (campo hidden, texto claro).
Basta ler esse valor e preencher input[name="form"] com ele.

Fluxo por cliente:
  1. Navega ao portal, localiza o iframe
  2. Lê captcha de input[name="form2"], preenche input[name="form"]
  3. Preenche CGA em input[name="cdCGA"] (apenas dígitos, sem separadores)
  4. Seleciona exercício em select[name="opcExercicio"]
  5. Clica input[name="Submit"] para consultar
  6. Verifica mensagem de retorno (div.PS_MSG):
     - "Não há DAM a emitir: todas as parcelas estão pagas." → status "pago"
     - "Não há dívida gerada para o exercício selecionado." → status "sem_divida"
     - Tabela de cotas presente → emite cada cota
  7. Para cada cota disponível no select#opcCotas:
     - Seleciona a cota
     - Clica input[name="bt_dam"] → form submete para Servicos_DamTFF_Tunel_Form.asp
     - Captura popup/nova aba → imprime como PDF → salva
  8. Retorna lista de {"nome","arquivo"} por cota

Seletores confirmados por mapeamento ao vivo (2026-06-05):
  Iframe:      servicosweb.sefaz.salvador.ba.gov.br/sistema/dam/TFF/servicos_DamTFF.asp
  CGA:         input[name="cdCGA"]
  Exercício:   select[name="opcExercicio"]
  Captcha img: input[name="form"]  (onde se digita)
  Captcha val: input[name="form2"] (hidden, valor em claro)
  Botão:       input[name="Submit"]
  MSG retorno: div.PS_MSG
  Cotas:       select#opcCotas  (options: Única=0, 1, 2, 3)
  Emitir DAM:  input[name="bt_dam"]  (onclick=emitir('dam'))
  Contribuinte: div.PS_label:nth-of-type(3) — "Contribuinte:RAZAO SOCIAL"
"""
import os
import re
import logging

log = logging.getLogger("TffSalvador.Portal")

URL_PORTAL     = "https://www2.sefaz.salvador.ba.gov.br/servico/2-via-tff-tll"
URL_FRAME_BASE = "servicosweb.sefaz.salvador.ba.gov.br/sistema/dam/TFF/"

# ── Mensagens de retorno do portal ──────────────────────────────────────────
MSG_PAGO       = "parcelas est"   # "todas as parcelas estão pagas"
MSG_SEM_DIVIDA = "dívida gerada"  # "Não há dívida gerada para o exercício"
MSG_NAO_EXISTE = "não existe"     # CGA não cadastrado


# ── Helpers de frame ─────────────────────────────────────────────────────────

def _get_frame(page):
    """Retorna o frame do portal TFF (iframe interno)."""
    for f in page.frames:
        if URL_FRAME_BASE in f.url:
            return f
    raise RuntimeError("Frame do portal TFF não encontrado. Verifique se a página carregou corretamente.")


# ── Consulta principal ────────────────────────────────────────────────────────

def consultar(page, cga: str, ano: int) -> dict:
    """
    Navega ao portal, preenche o formulário e retorna o estado da consulta.

    Retorna:
        {"status": "cotas", "cotas": [...], "contribuinte": str}  — tem DAM a emitir
        {"status": "pago",  "contribuinte": ""}                   — tudo pago
        {"status": "sem_divida", "contribuinte": ""}              — sem dívida no exercício
        {"status": "captcha_erro", "detalhe": str}                — captcha inválido
        {"status": "erro", "detalhe": str}                        — erro inesperado

    cotas: [{"value": "0", "label": "ÚNICA"}, {"value": "1", "label": "1"}, ...]
    """
    log.info(f"[CGA {cga}] Consultando exercício {ano}...")
    page.goto(URL_PORTAL, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(1500)

    frame = _get_frame(page)

    # Lê o captcha do campo hidden
    captcha_val = frame.locator('input[name="form2"]').get_attribute("value", timeout=10_000)
    if not captcha_val:
        raise RuntimeError(f"[CGA {cga}] Campo form2 (captcha hidden) não encontrado.")
    log.debug(f"[CGA {cga}] Captcha lido: {captcha_val!r}")

    # Preenche formulário
    frame.fill('input[name="cdCGA"]', cga)
    frame.select_option('select[name="opcExercicio"]', str(ano))
    frame.fill('input[name="form"]', captcha_val)

    # Submete
    frame.click('input[name="Submit"]')
    page.wait_for_timeout(2500)

    # Lê o frame de resultado (pode ter URL diferente após submit)
    result_frame = _get_frame(page)

    # Verifica mensagem de retorno
    try:
        msg_els = result_frame.locator("div.PS_MSG").all()
        for el in msg_els:
            txt = el.inner_text(timeout=2000).lower()
            if MSG_PAGO in txt:
                log.info(f"[CGA {cga}] Status: pago (todas as parcelas pagas)")
                return {"status": "pago", "contribuinte": ""}
            if MSG_SEM_DIVIDA in txt:
                log.info(f"[CGA {cga}] Status: sem_divida (sem dívida no exercício {ano})")
                return {"status": "sem_divida", "contribuinte": ""}
            if MSG_NAO_EXISTE in txt:
                log.info(f"[CGA {cga}] Status: nao_existe (CGA não cadastrado)")
                return {"status": "nao_existe", "contribuinte": ""}
    except Exception:
        pass

    # Verifica se o select de cotas está presente (página de emissão)
    try:
        cotas_el = result_frame.locator("select#opcCotas")
        if cotas_el.count() == 0:
            # Ainda está na página do formulário — captcha pode ter falhado
            captcha_novo = result_frame.locator('input[name="form2"]')
            if captcha_novo.count() > 0:
                return {"status": "captcha_erro", "detalhe": "CAPTCHA inválido — portal devolveu formulário"}
            return {"status": "erro", "detalhe": "Resposta inesperada do portal."}
    except Exception as e:
        return {"status": "erro", "detalhe": str(e)}

    # Lê as cotas disponíveis
    cotas = []
    try:
        opts = result_frame.locator("select#opcCotas option").all()
        for opt in opts:
            val   = opt.get_attribute("value")
            label = opt.inner_text(timeout=2000).strip()
            cotas.append({"value": val, "label": label})
    except Exception as e:
        return {"status": "erro", "detalhe": f"Erro ao ler cotas: {e}"}

    # Extrai nome do contribuinte
    contribuinte = ""
    try:
        labels = result_frame.locator("div.PS_label").all()
        for el in labels:
            txt = el.inner_text(timeout=1000)
            if txt.startswith("Contribuinte:"):
                contribuinte = txt.replace("Contribuinte:", "").strip()
                break
    except Exception:
        pass

    log.info(f"[CGA {cga}] {len(cotas)} cota(s) a emitir. Contribuinte: {contribuinte!r}")
    return {"status": "cotas", "cotas": cotas, "contribuinte": contribuinte}


# ── Emissão por cota ─────────────────────────────────────────────────────────

def _consultar_frame(page, cga: str, ano: int):
    """
    Navega ao portal e submete o formulário. Retorna o result_frame com
    select#opcCotas disponível, ou lança RuntimeError.

    Usado internamente por emitir_cota para cada cota — após clicar bt_dam
    o portal navega para Principal.aspx e não tem botão Voltar, então cada
    cota requer uma nova consulta do zero.
    """
    page.goto(URL_PORTAL, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(1500)

    frame = _get_frame(page)
    captcha_val = frame.locator('input[name="form2"]').get_attribute("value", timeout=10_000)
    if not captcha_val:
        raise RuntimeError("Campo form2 (captcha hidden) não encontrado.")

    frame.fill('input[name="cdCGA"]', cga)
    frame.select_option('select[name="opcExercicio"]', str(ano))
    frame.fill('input[name="form"]', captcha_val)
    frame.click('input[name="Submit"]')
    page.wait_for_timeout(2500)

    result_frame = _get_frame(page)

    cotas_el = result_frame.locator("select#opcCotas")
    if cotas_el.count() == 0:
        raise RuntimeError("select#opcCotas não encontrado após submit (captcha falhou ou CGA inválido).")

    return result_frame


def emitir_cota(page, cga: str, cota: dict, razao_social: str,
                ano: int, pasta_destino: str) -> dict:
    """
    Consulta o portal do zero e emite UMA cota como PDF.

    O portal não tem botão Voltar após emitir — cada cota exige nova
    navegação completa (goto + captcha + submit). O PDF está embutido
    como data:Application/pdf;base64,... no <embed id="pdfID"> da página
    de resultado (Principal.aspx), dentro de um iframe filho.

    cota: {"value": "0", "label": "ÚNICA"}
    Retorna: {"nome": str, "arquivo": str|None, "detalhe": str}
    """
    import base64

    label    = cota["label"].strip().upper()
    valor    = cota["value"]
    nome_arq = _nome_arquivo(cga, razao_social, label, ano)
    caminho  = os.path.join(pasta_destino, nome_arq)

    log.info(f"[CGA {cga}] Emitindo cota {label} (nova consulta)...")

    try:
        result_frame = _consultar_frame(page, cga, ano)

        # Seleciona a cota e clica bt_dam
        result_frame.select_option("select#opcCotas", valor)
        page.wait_for_timeout(500)
        result_frame.click('input[name="bt_dam"]')

        # Aguarda embed#pdfID em qualquer frame (Principal.aspx carrega em iframe filho)
        embed_el = None
        for _ in range(30):  # até 15s
            page.wait_for_timeout(500)
            for f in page.frames:
                try:
                    el = f.locator("embed#pdfID")
                    if el.count() > 0:
                        embed_el = el
                        break
                except Exception:
                    continue
            if embed_el:
                break

        if not embed_el:
            return {"nome": f"Cota {label}", "arquivo": None,
                    "detalhe": "embed#pdfID não encontrado após bt_dam"}

        # src = "data:Application/pdf;base64,<B64>"
        src = embed_el.get_attribute("src", timeout=10_000) or ""
        if not src.startswith("data:"):
            return {"nome": f"Cota {label}", "arquivo": None,
                    "detalhe": f"src inesperado: {src[:80]}"}

        b64_data  = src.split(",", 1)[1]
        pdf_bytes = base64.b64decode(b64_data)

        with open(caminho, "wb") as fh:
            fh.write(pdf_bytes)

        log.info(f"[CGA {cga}] Cota {label} salva: {caminho} ({len(pdf_bytes)} bytes)")
        return {"nome": f"Cota {label}", "arquivo": caminho, "detalhe": ""}

    except Exception as e:
        log.error(f"[CGA {cga}] Erro ao emitir cota {label}: {e}")
        return {"nome": f"Cota {label}", "arquivo": None, "detalhe": str(e)}


def _nome_arquivo(cga: str, razao_social: str, cota_label: str, ano: int) -> str:
    """Monta o nome do arquivo: {razao}_{cga}_cota{LABEL}_{ano}.pdf"""
    cota_safe = re.sub(r"\s+", "", cota_label)  # "ÚNICA" → "ÚNICA", "1" → "1"
    if razao_social:
        razao_limpa = re.sub(r'[\\/*?:"<>|]', "", razao_social).strip().replace(" ", "_")
        base = f"{razao_limpa}_{cga}"
    else:
        base = cga
    return f"{base}_cota{cota_safe}_{ano}.pdf"


# ── Lote ─────────────────────────────────────────────────────────────────────

def executar_lote(clientes: list, ano: int, pasta_destino: str,
                  stop_flag, progress_cb, cliente_cb, cfg: dict) -> dict:
    """
    Processa um lote de clientes sequencialmente.

    clientes:    [{"cga","razao_social","cnpj","municipio"}, ...]
    stop_flag:   threading.Event
    progress_cb: fn(pct, msg, cga)
    cliente_cb:  fn(cga, razao_social, cnpj, municipio, status, guias, detalhe, indice, total)
    cfg:         dict de configuração

    Retorna: {"total": int, "ok": int, "erros": int, "cancelado": bool}
    """
    from playwright.sync_api import sync_playwright

    total     = len(clientes)
    ok_count  = 0
    err_count = 0
    headless  = cfg.get("tf_headless", True)
    pausa_s   = float(cfg.get("tf_pausa_entre_clientes_s", 3))

    progress_cb(0, f"Iniciando lote de {total} cliente(s)...", "")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            for idx, cliente in enumerate(clientes, start=1):
                if stop_flag.is_set():
                    log.info("Lote cancelado pelo usuário.")
                    progress_cb(None, "Cancelado pelo usuário.", "")
                    return {"total": total, "ok": ok_count,
                            "erros": err_count, "cancelado": True}

                cga       = cliente["cga"]
                razao     = cliente.get("razao_social", "")
                cnpj      = cliente.get("cnpj", "")
                municipio = cliente.get("municipio", "")
                pct       = int((idx - 1) / total * 100)
                progress_cb(pct, f"[{idx}/{total}] CGA {cga} — {razao}", cga)

                # Contexto isolado por cliente
                ctx  = browser.new_context(accept_downloads=True)
                page = ctx.new_page()
                page.set_default_timeout(60_000)

                status  = "ok"
                detalhe = ""
                guias   = []

                try:
                    resultado = consultar(page, cga, ano)
                    portal_status = resultado["status"]

                    if portal_status == "cotas":
                        cotas        = resultado["cotas"]
                        contribuinte = resultado.get("contribuinte", razao)
                        nome_final   = contribuinte or razao

                        for cota in cotas:
                            if stop_flag.is_set():
                                break
                            g = emitir_cota(page, cga, cota, nome_final, ano, pasta_destino)
                            guias.append(g)

                        guias_ok = sum(1 for g in guias if g.get("arquivo"))
                        if guias_ok == 0:
                            status  = "erro"
                            detalhe = "Nenhuma cota emitida com sucesso."
                            err_count += 1
                        elif guias_ok < len(guias):
                            status  = "parcial"
                            detalhe = f"{guias_ok}/{len(guias)} cotas emitidas."
                            ok_count += 1
                        else:
                            ok_count += 1

                    elif portal_status == "pago":
                        status  = "pago"
                        detalhe = "Todas as parcelas já estão pagas."
                        ok_count += 1

                    elif portal_status == "sem_divida":
                        status  = "sem_divida"
                        detalhe = f"Sem dívida gerada para {ano}."
                        ok_count += 1

                    elif portal_status == "nao_existe":
                        status  = "nao_existe"
                        detalhe = "CGA não cadastrado no portal."
                        err_count += 1

                    elif portal_status == "captcha_erro":
                        status    = "captcha_erro"
                        detalhe   = resultado.get("detalhe", "CAPTCHA inválido.")
                        err_count += 1

                    else:
                        status    = "erro"
                        detalhe   = resultado.get("detalhe", "Erro desconhecido.")
                        err_count += 1

                except Exception as e:
                    status    = "erro"
                    detalhe   = str(e)
                    err_count += 1
                    log.error(f"[CGA {cga}] Erro inesperado: {e}")

                finally:
                    try:
                        ctx.close()
                    except Exception:
                        pass

                cliente_cb(
                    cga=cga,
                    razao_social=razao,
                    cnpj=cnpj,
                    municipio=municipio,
                    status=status,
                    guias=guias,
                    detalhe=detalhe,
                    indice=idx,
                    total=total,
                )

                pct_pos = int(idx / total * 100)
                progress_cb(pct_pos, f"[{idx}/{total}] CGA {cga} — {status}", cga)

                if idx < total and not stop_flag.is_set():
                    if stop_flag.wait(timeout=pausa_s):
                        break

        finally:
            try:
                browser.close()
            except Exception:
                pass

    cancelado = stop_flag.is_set()
    progress_cb(
        100 if not cancelado else None,
        "Lote concluído." if not cancelado else "Cancelado.",
        "",
    )
    return {"total": total, "ok": ok_count, "erros": err_count, "cancelado": cancelado}
