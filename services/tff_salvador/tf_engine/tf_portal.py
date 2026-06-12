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
     - Clica input[name="bt_dam"]
     - Captura o PDF (modo varia por tipo, ver abaixo) → salva
  8. Retorna lista de {"nome","arquivo"} por cota

TFF vs TLL (mesmo sistema, captura de PDF diferente):
  - TFF: bt_dam carrega Principal.aspx na MESMA página; o PDF vem embutido como
    data:Application/pdf;base64,... em <embed id="pdfID"> (iframe filho).
  - TLL: bt_dam abre uma NOVA ABA (DAMFormTLL.asp) com o DAM renderizado em HTML,
    sem embed nem download. Capturamos via page.pdf() (imprime a página). O portal
    pode abrir abas duplicadas do mesmo DAM — fechamos as extras. TLL é cota única.
    Confirmado por mapeamento ao vivo (2026-06-10, CGA 0105965900258 exercício 2026).

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
import traceback
import logging

log = logging.getLogger("TffSalvador.Portal")


def _configurar_browsers_path():
    """
    Garante que o Playwright encontre o Chromium antes de sync_playwright().

    No exe (frozen): o Chromium headless é empacotado em _internal/ms-playwright
    (ver dmf_engine.spec). O Playwright bundled procuraria em
    _internal/.../.local-browsers (vazio) → chromium.launch() travaria. Apontamos
    PLAYWRIGHT_BROWSERS_PATH para a pasta empacotada — funciona offline, sem
    depender de download na máquina de destino.

    Em dev: o site-packages do Playwright resolve o ms-playwright do usuário
    sozinho; só apontamos como fallback se a env não estiver definida.
    """
    import sys
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return

    if getattr(sys, "frozen", False):
        bundled = os.path.join(sys._MEIPASS, "ms-playwright")
        if os.path.isdir(bundled):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = bundled
            log.info(f"PLAYWRIGHT_BROWSERS_PATH (empacotado) = {bundled}")
            return
        log.warning(f"ms-playwright empacotado não encontrado em {bundled}")

    # Fallback (dev ou exe sem bundle): ms-playwright do usuário
    user_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if os.path.isdir(user_dir):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = user_dir
        log.info(f"PLAYWRIGHT_BROWSERS_PATH (usuário) = {user_dir}")


# ── Tipos de guia suportados ────────────────────────────────────────────────
# TFF e TLL são o MESMO sistema (mesmos seletores, captcha e mensagens); muda só
# a URL externa e o segmento do iframe (.../dam/TFF/ vs .../dam/TLL/). Confirmado
# por mapeamento ao vivo (2026-06-10). TLL sempre traz cota única no select#opcCotas.
TIPOS = {
    "TFF": {
        "url":   "https://www2.sefaz.salvador.ba.gov.br/servico/2-via-tff-tll",
        "frame": "servicosweb.sefaz.salvador.ba.gov.br/sistema/dam/TFF/",
    },
    "TLL": {
        "url":   "https://www2.sefaz.salvador.ba.gov.br/servico/2-via-dam-tll",
        "frame": "servicosweb.sefaz.salvador.ba.gov.br/sistema/dam/TLL/",
    },
}

# Defaults legados (TFF) — mantidos para chamadas antigas sem 'tipo'.
URL_PORTAL     = TIPOS["TFF"]["url"]
URL_FRAME_BASE = TIPOS["TFF"]["frame"]


def _cfg_tipo(tipo: str) -> dict:
    """Retorna {url, frame} para o tipo (TFF|TLL). Default TFF se desconhecido."""
    return TIPOS.get((tipo or "TFF").upper(), TIPOS["TFF"])

# ── Mensagens de retorno do portal ──────────────────────────────────────────
MSG_PAGO       = "parcelas est"   # "todas as parcelas estão pagas"
MSG_SEM_DIVIDA = "dívida gerada"  # "Não há dívida gerada para o exercício"
MSG_NAO_EXISTE = "não existe"     # CGA não cadastrado


# ── Helpers de frame ─────────────────────────────────────────────────────────

def _get_frame(page, frame_base: str = URL_FRAME_BASE):
    """Retorna o frame do portal (iframe interno) para o tipo dado."""
    for f in page.frames:
        if frame_base in f.url:
            return f
    raise RuntimeError("Frame do portal não encontrado. Verifique se a página carregou corretamente.")


# ── Consulta principal ────────────────────────────────────────────────────────

def consultar(page, cga: str, ano: int, tipo: str = "TFF") -> dict:
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
    cfg_t = _cfg_tipo(tipo)
    log.info(f"[CGA {cga}] Consultando {tipo} exercício {ano}...")
    page.goto(cfg_t["url"], wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(1500)

    frame = _get_frame(page, cfg_t["frame"])

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
    result_frame = _get_frame(page, cfg_t["frame"])

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

def _consultar_frame(page, cga: str, ano: int, tipo: str = "TFF"):
    """
    Navega ao portal e submete o formulário. Retorna o result_frame com
    select#opcCotas disponível, ou lança RuntimeError.

    Usado internamente por emitir_cota para cada cota — após clicar bt_dam
    o portal navega para Principal.aspx e não tem botão Voltar, então cada
    cota requer uma nova consulta do zero.
    """
    cfg_t = _cfg_tipo(tipo)
    page.goto(cfg_t["url"], wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(1500)

    frame = _get_frame(page, cfg_t["frame"])
    captcha_val = frame.locator('input[name="form2"]').get_attribute("value", timeout=10_000)
    if not captcha_val:
        raise RuntimeError("Campo form2 (captcha hidden) não encontrado.")

    frame.fill('input[name="cdCGA"]', cga)
    frame.select_option('select[name="opcExercicio"]', str(ano))
    frame.fill('input[name="form"]', captcha_val)
    frame.click('input[name="Submit"]')
    page.wait_for_timeout(2500)

    result_frame = _get_frame(page, cfg_t["frame"])

    cotas_el = result_frame.locator("select#opcCotas")
    if cotas_el.count() == 0:
        raise RuntimeError("select#opcCotas não encontrado após submit (captcha falhou ou CGA inválido).")

    return result_frame


def _capturar_pdf_tff(page, caminho: str) -> dict:
    """TFF: o PDF vem embutido como data:Application/pdf;base64,... em
    <embed id="pdfID"> num iframe filho da página de resultado (Principal.aspx)."""
    import base64

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
        return {"arquivo": None, "detalhe": "embed#pdfID não encontrado após bt_dam"}

    src = embed_el.get_attribute("src", timeout=10_000) or ""
    if not src.startswith("data:"):
        return {"arquivo": None, "detalhe": f"src inesperado: {src[:80]}"}

    pdf_bytes = base64.b64decode(src.split(",", 1)[1])
    with open(caminho, "wb") as fh:
        fh.write(pdf_bytes)
    return {"arquivo": caminho, "detalhe": "", "bytes": len(pdf_bytes)}


def _capturar_pdf_tll(popup, caminho: str) -> dict:
    """TLL: o bt_dam abre uma NOVA ABA (DAMFormTLL.asp) com o DAM em HTML —
    sem embed/download. Captura imprimindo a página como PDF (page.pdf()),
    que é o "imprimir e salvar" do portal. `popup` é a aba já aberta."""
    try:
        popup.wait_for_load_state("networkidle", timeout=20_000)
    except Exception:
        pass
    popup.wait_for_timeout(1500)
    # page.pdf() exige Chromium headless; o lote roda headless por padrão.
    try:
        popup.emulate_media(media="print")
        popup.pdf(path=caminho, print_background=True)
    except Exception as e:
        # page.pdf() não é suportado com janela visível (headful).
        if "headless" in str(e).lower() or "non-headless" in str(e).lower():
            return {"arquivo": None,
                    "detalhe": ("TLL exige modo headless para gerar o PDF. "
                                "Ative 'Modo headless' na Configuração.")}
        return {"arquivo": None, "detalhe": f"Falha em page.pdf(): {e}"}
    tam = os.path.getsize(caminho) if os.path.exists(caminho) else 0
    if tam <= 0:
        return {"arquivo": None, "detalhe": "page.pdf() gerou arquivo vazio"}
    return {"arquivo": caminho, "detalhe": "", "bytes": tam}


def emitir_cota(page, cga: str, cota: dict, razao_social: str,
                ano: int, pasta_destino: str, tipo: str = "TFF") -> dict:
    """
    Consulta o portal do zero e emite UMA cota como PDF.

    O portal não tem botão Voltar após emitir — cada cota exige nova
    navegação completa (goto + captcha + submit).

    Captura do PDF difere por tipo:
      - TFF: <embed id="pdfID"> com data:base64 na própria página (Principal.aspx).
      - TLL: o bt_dam abre uma NOVA ABA (DAMFormTLL.asp) com o DAM em HTML;
             capturamos via page.pdf() (imprimir a página).

    cota: {"value": "0", "label": "ÚNICA"}
    Retorna: {"nome": str, "arquivo": str|None, "detalhe": str}
    """
    tipo     = (tipo or "TFF").upper()
    label    = cota["label"].strip().upper()
    valor    = cota["value"]
    nome_arq = _nome_arquivo(cga, razao_social, label, ano, tipo)
    caminho  = os.path.join(pasta_destino, nome_arq)

    log.info(f"[CGA {cga}] Emitindo {tipo} cota {label} (nova consulta)...")

    try:
        result_frame = _consultar_frame(page, cga, ano, tipo)

        # Seleciona a cota
        result_frame.select_option("select#opcCotas", valor)
        page.wait_for_timeout(500)

        if tipo == "TLL":
            # bt_dam abre nova aba; capturamos o popup no momento do clique.
            ctx = page.context
            with ctx.expect_page(timeout=20_000) as novapag:
                result_frame.click('input[name="bt_dam"]')
            popup = novapag.value
            res = _capturar_pdf_tll(popup, caminho)
            try:
                popup.close()
            except Exception:
                pass
            # O portal pode abrir abas duplicadas (mesmo DAM); fecha as extras.
            for extra in list(ctx.pages):
                if "DAMFormTLL.asp" in extra.url:
                    try:
                        extra.close()
                    except Exception:
                        pass
        else:
            result_frame.click('input[name="bt_dam"]')
            res = _capturar_pdf_tff(page, caminho)

        if not res.get("arquivo"):
            return {"nome": f"Cota {label}", "arquivo": None,
                    "detalhe": res.get("detalhe", "Falha ao capturar PDF.")}

        log.info(f"[CGA {cga}] Cota {label} salva: {caminho} ({res.get('bytes', 0)} bytes)")
        return {"nome": f"Cota {label}", "arquivo": caminho, "detalhe": ""}

    except Exception as e:
        log.error(f"[CGA {cga}] Erro ao emitir cota {label}: {e}")
        return {"nome": f"Cota {label}", "arquivo": None, "detalhe": str(e)}


def _nome_arquivo(cga: str, razao_social: str, cota_label: str, ano: int,
                  tipo: str = "TFF") -> str:
    """Monta o nome do arquivo: {razao}_{cga}_{TIPO}_cota{LABEL}_{ano}.pdf

    O tipo (TFF|TLL) entra no nome para evitar que um lote TLL sobrescreva os
    PDFs de um lote TFF do mesmo CGA/cota/ano na mesma pasta.
    """
    cota_safe = re.sub(r"\s+", "", cota_label)  # "ÚNICA" → "ÚNICA", "1" → "1"
    tipo_safe = (tipo or "TFF").upper()
    if razao_social:
        razao_limpa = re.sub(r'[\\/*?:"<>|]', "", razao_social).strip().replace(" ", "_")
        base = f"{razao_limpa}_{cga}"
    else:
        base = cga
    return f"{base}_{tipo_safe}_cota{cota_safe}_{ano}.pdf"


# ── Lote ─────────────────────────────────────────────────────────────────────

def executar_lote(clientes: list, ano: int, pasta_destino: str,
                  stop_flag, progress_cb, cliente_cb, cfg: dict,
                  tipo: str = "TFF") -> dict:
    """
    Processa um lote de clientes sequencialmente.

    clientes:    [{"cga","razao_social","cnpj","municipio"}, ...]
    stop_flag:   threading.Event
    progress_cb: fn(pct, msg, cga)
    cliente_cb:  fn(cga, razao_social, cnpj, municipio, status, guias, detalhe, indice, total)
    cfg:         dict de configuração
    tipo:        "TFF" ou "TLL" — define o portal/URL (seletores idênticos)

    Retorna: {"total": int, "ok": int, "erros": int, "cancelado": bool}
    """
    _configurar_browsers_path()
    from playwright.sync_api import sync_playwright

    tipo      = (tipo or "TFF").upper()
    total     = len(clientes)
    ok_count  = 0
    err_count = 0
    headless  = cfg.get("tf_headless", True)
    pausa_s   = float(cfg.get("tf_pausa_entre_clientes_s", 3))

    progress_cb(0, f"Iniciando lote {tipo} de {total} cliente(s)...", "")

    # No exe (PyInstaller+pywebview), o main.py seta WindowsSelectorEventLoopPolicy
    # globalmente. O Playwright sync_api cria seu loop via asyncio.new_event_loop(),
    # que lê a POLICY (não o loop setado manualmente) — e o SelectorEventLoop não
    # implementa subprocessos no Windows (_make_subprocess_transport →
    # NotImplementedError) que o Playwright usa p/ lançar node.exe. Provado em teste
    # isolado: set_event_loop(Proactor) NÃO resolve; só trocar a POLICY resolve.
    # Como a policy é global ao processo, trocamos para Proactor durante o lote e
    # restauramos no finally. O pywebview usa winforms (message loop nativo, não
    # asyncio), então não é afetado pela troca.
    import asyncio as _asyncio
    import sys as _sys
    _policy_anterior = None
    if _sys.platform == "win32":
        _policy_anterior = _asyncio.get_event_loop_policy()
        _asyncio.set_event_loop_policy(_asyncio.WindowsProactorEventLoopPolicy())

    try:
      with sync_playwright() as p:
        log.info(f"Iniciando Chromium (headless={headless})...")
        # timeout explícito: se o launch travar (browser não encontrado, IOCP
        # preso), lança TimeoutError em vez de pendurar a thread para sempre.
        browser = p.chromium.launch(headless=headless, timeout=60_000)
        log.info("Chromium pronto.")
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
                    resultado = consultar(page, cga, ano, tipo)
                    portal_status = resultado["status"]

                    if portal_status == "cotas":
                        cotas        = resultado["cotas"]
                        contribuinte = resultado.get("contribuinte", razao)
                        nome_final   = contribuinte or razao

                        for cota in cotas:
                            if stop_flag.is_set():
                                break
                            # Nova page por cota: o portal auto-fecha a página
                            # após exibir o PDF (Principal.aspx), invalidando
                            # o objeto page se reutilizado entre cotas.
                            cota_page = ctx.new_page()
                            cota_page.set_default_timeout(60_000)
                            try:
                                g = emitir_cota(cota_page, cga, cota, nome_final, ano, pasta_destino, tipo)
                            finally:
                                try:
                                    cota_page.close()
                                except Exception:
                                    pass
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
                    log.error(f"[CGA {cga}] Erro inesperado: {e}\n{traceback.format_exc()}")

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
    finally:
        if _policy_anterior is not None:
            _asyncio.set_event_loop_policy(_policy_anterior)

    cancelado = stop_flag.is_set()
    progress_cb(
        100 if not cancelado else None,
        "Lote concluído." if not cancelado else "Cancelado.",
        "",
    )
    return {"total": total, "ok": ok_count, "erros": err_count, "cancelado": cancelado}
