"""
sm_engine/sm_portal.py — Automação Playwright do portal NFS-e Salvador.

Fluxo por empresa:
  1. login()         — preenche CNPJ+senha+CAPTCHA (Anti-Captcha), clica Acessar
  2. _dispensar_aviso() — clica #imbFechar se aparecer tela de aviso pós-login
  3. emitir_documentos() — navega para emitidas e recebidas, captura popup via
                           context.expect_page(), dispara download via #btGerar
  4. executar_lote()  — orquestra o loop de empresas com stop_flag e callbacks

Seletores confirmados por mapeamento ao vivo (sm_debug_mapear.py):
  Login:      #txtLogin, #txtSenha, #img1, #tbCaptcha, #cmdLogin
  Aviso:      #imbFechar  (input[type=image] title="Acessar Nota Salvador")
  Emitidas:   /site/contribuinte/nota/consulta.aspx
              #ddlExercicio, #ddlMes, #btNFe (Visualizar)
              → popup via ConsultarNotas → notasrecapuradas.aspx
  Recebidas:  /site/contribuinte/notatomador/consulta.aspx
              #ddlExercicio, #ddlMes, #btNFe (Visualizar)
              → #btRecebidas (ConsultarNotas) → notasrecapuradasnfts.aspx
  Popup:      capturado via context.expect_page(); PDF via page.pdf()
              quantidade em texto da página (ex: "Quantidade NFS-e: 0")
"""
import os
import re
import logging

log = logging.getLogger("SemMovimento.Portal")

URL_BASE  = "https://nfse.salvador.ba.gov.br"
URL_LOGIN = f"{URL_BASE}/default.aspx"

# ── Seletores confirmados ────────────────────────────────────────────────────
SEL_LOGIN_CNPJ    = "#txtLogin"
SEL_LOGIN_SENHA   = "#txtSenha"
SEL_LOGIN_CAPTCHA_IMG = "#img1"
SEL_LOGIN_CAPTCHA_TXT = "#tbCaptcha"
SEL_LOGIN_BTN     = "#cmdLogin"

SEL_AVISO_BTN     = "#imbFechar"          # input[type=image] pós-login

# Tela de filtros (mesma estrutura em emitidas e recebidas)
SEL_ANO           = "#ddlExercicio"
SEL_MES           = "#ddlMes"
SEL_VISUALIZAR    = "#btNFe"

# Botão que abre popup de recebidas
SEL_BTN_RECEBIDAS = "#btRecebidas"        # onclick=ConsultarNotas('notasrecapuradasnfts.aspx')
# Botão equivalente para emitidas (mesmo padrão, id diferente — descoberto por inferência)
SEL_BTN_EMITIDAS  = "#btEmitidas"         # fallback: input[onclick*='ConsultarNotas']

URL_EMITIDAS  = "/site/contribuinte/nota/consulta.aspx"
URL_RECEBIDAS = "/site/contribuinte/notatomador/consulta.aspx"


# ── Login ────────────────────────────────────────────────────────────────────

def login(page, cnpj: str, senha: str, cfg: dict) -> None:
    """
    Faz login no portal. Resolve CAPTCHA via Anti-Captcha (ImageToTextTask).
    Sem chave configurada, cai em modo manual (usuário resolve no navegador).
    Levanta RuntimeError se login falhar após retries.
    """
    log.info(f"[{cnpj}] Iniciando login...")
    page.goto(URL_LOGIN, wait_until="domcontentloaded")
    page.wait_for_timeout(1200)

    page.fill(SEL_LOGIN_CNPJ, cnpj)
    page.fill(SEL_LOGIN_SENHA, senha)

    api_key = cfg.get("sm_anticaptcha_api_key", "").strip()

    if not api_key:
        # Modo manual: navegador visível, usuário resolve o CAPTCHA
        _login_manual(page, cnpj)
        return

    # Modo automático: Anti-Captcha
    from sm_captcha import resolver as resolver_captcha
    timeout_s      = int(cfg.get("sm_captcha_timeout_s", 60))
    max_tentativas = 2

    for tentativa in range(1, max_tentativas + 1):
        log.info(f"[{cnpj}] CAPTCHA — tentativa {tentativa}/{max_tentativas}")

        captcha_el = page.locator(SEL_LOGIN_CAPTCHA_IMG)
        captcha_el.wait_for(state="visible", timeout=15_000)
        img_bytes = captcha_el.screenshot()

        texto = resolver_captcha(img_bytes, api_key, timeout_s)
        log.info(f"[{cnpj}] CAPTCHA resolvido: {texto!r}")

        page.fill(SEL_LOGIN_CAPTCHA_TXT, texto)
        page.click(SEL_LOGIN_BTN)

        try:
            page.wait_for_url(
                lambda url: "default.aspx" not in url,
                timeout=20_000
            )
            page.wait_for_load_state("domcontentloaded")
            log.info(f"[{cnpj}] Login OK — {page.url}")
            _dispensar_aviso(page)
            return
        except Exception:
            log.warning(f"[{cnpj}] Login falhou (CAPTCHA incorreto?), tentativa {tentativa}")
            if tentativa < max_tentativas:
                page.goto(URL_LOGIN, wait_until="domcontentloaded")
                page.wait_for_timeout(1000)
                page.fill(SEL_LOGIN_CNPJ, cnpj)
                page.fill(SEL_LOGIN_SENHA, senha)

    raise RuntimeError(f"Login falhou após {max_tentativas} tentativas (CAPTCHA)")


def _login_manual(page, cnpj: str) -> None:
    """
    Modo manual (sem Anti-Captcha): aguarda o usuário resolver o CAPTCHA e logar.
    O navegador deve estar visível (headless=False).
    Timeout de 3 minutos por empresa.
    """
    log.info(f"[{cnpj}] Modo manual — resolva o CAPTCHA no navegador (timeout 3 min).")
    try:
        page.wait_for_url(
            lambda url: "default.aspx" not in url,
            timeout=180_000
        )
    except Exception:
        raise RuntimeError(f"[{cnpj}] Timeout aguardando login manual (3 min).")
    page.wait_for_load_state("domcontentloaded")
    log.info(f"[{cnpj}] Login manual OK — {page.url}")
    _dispensar_aviso(page)


def _dispensar_aviso(page) -> None:
    """Clica em #imbFechar se a tela de aviso pós-login aparecer."""
    try:
        el = page.locator(SEL_AVISO_BTN).first
        if el.is_visible(timeout=4000):
            log.info("Tela de aviso detectada — clicando #imbFechar")
            el.click()
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(800)
    except Exception:
        pass  # aviso não apareceu — normal


# ── Nome do contribuinte ─────────────────────────────────────────────────────


def extrair_nome_contribuinte(page) -> str:
    """
    Lê o nome do contribuinte do <select id="ddlContribuinte"> pós-login.
    O texto da opção selecionada tem o formato "00.000.000/0001-00 - RAZAO SOCIAL LTDA".
    Extrai apenas a parte após o primeiro " - ".
    Fallbacks: lblNomeContribuinte, lblContribuinte, regex no body.
    Retorna string vazia se não encontrado.
    """
    # 1. Select ddlContribuinte — disabled no portal, então lemos via JS
    try:
        texto = page.evaluate(
            "() => {"
            "  const s = document.getElementById('ddlContribuinte');"
            "  if (!s) return '';"
            "  const opt = s.options[s.selectedIndex];"
            "  return opt ? opt.text : '';"
            "}"
        )
        texto = (texto or "").strip()
        if texto and " - " in texto:
            nome = texto.split(" - ", 1)[1].strip()
            if nome:
                log.info(f"Nome do contribuinte (ddlContribuinte JS): {nome!r}")
                return nome
        elif texto and texto != "Selecione o contribuinte desejado...":
            log.info(f"Nome do contribuinte (ddlContribuinte JS, sem CNPJ): {texto!r}")
            return texto
    except Exception as e:
        log.debug(f"ddlContribuinte JS falhou: {e}")

    # 2. Labels ASP.NET WebForms comuns
    for sel in ("#lblNomeContribuinte", "#lblContribuinte", "#lblRazaoSocial",
                "#ctl00_body_lblNomeContribuinte", "#ctl00_body_lblContribuinte",
                "span[id*='NomeContribuinte']", "span[id*='RazaoSocial']"):
        try:
            el = page.locator(sel).first
            if el.count() and el.is_visible(timeout=1500):
                texto = el.inner_text().strip()
                if texto:
                    log.info(f"Nome do contribuinte ({sel}): {texto!r}")
                    return texto
        except Exception:
            continue

    # 3. Regex no body: "Contribuinte\n<NOME>" ou "Contribuinte: <NOME>"
    try:
        body = page.inner_text("body")
        m = re.search(
            r"Contribuinte\s*[:\-]?\s*\n?\s*([A-ZÀ-Ú][A-Za-zÀ-úÃãÕõÉéÍíÓóÚú &.,\-]{2,80})",
            body, re.IGNORECASE
        )
        if m:
            nome = m.group(1).strip()
            log.info(f"Nome do contribuinte (regex body): {nome!r}")
            return nome
    except Exception:
        pass

    log.warning("Nome do contribuinte não encontrado na página.")
    return ""


# ── Emissão de documentos ─────────────────────────────────────────────────────

def _nome_arquivo(cnpj: str, nome_empresa: str, ponta: str, mes: int, ano: int) -> str:
    """Monta o nome do arquivo PDF: {nome}_{6digitos}_{ponta}_{MMAAAA}.pdf"""
    sufixo6 = cnpj[-6:] if len(cnpj) >= 6 else cnpj
    if nome_empresa:
        # Sanitiza: remove caracteres inválidos para nome de arquivo
        nome_limpo = re.sub(r'[\\/*?:"<>|]', '', nome_empresa).strip().replace(' ', '_')
        base = f"{nome_limpo}_{sufixo6}"
    else:
        base = sufixo6
    return f"{base}_{ponta}_{mes:02d}{ano}.pdf"


def emitir_documentos(ctx, cnpj: str, mes: int, ano: int, pasta_destino: str) -> dict:
    """
    Navega pelas telas de emitidas e recebidas, captura o popup e salva PDF.
    O nome da empresa é extraído do #ddlContribuinte na tela de emitidas e
    reaproveitado para recebidas.

    ctx: playwright BrowserContext (já autenticado, com cookies de sessão)
    Retorna: {
        "emitidas":  {"arquivo": str|None, "qtd": int, "status": "ok"|"erro"|"sem_botao", "detalhe": str},
        "recebidas": {"arquivo": str|None, "qtd": int, "status": "ok"|"erro"|"sem_botao", "detalhe": str},
    }
    """
    # Emitidas — extrai o nome do contribuinte nesta tela e repassa para recebidas
    res_emit, nome_empresa = _processar_ponta(
        ctx, cnpj, mes, ano, pasta_destino, "emitidas", URL_EMITIDAS, SEL_BTN_EMITIDAS, ""
    )
    res_receb, _ = _processar_ponta(
        ctx, cnpj, mes, ano, pasta_destino, "recebidas", URL_RECEBIDAS, SEL_BTN_RECEBIDAS, nome_empresa
    )
    return {"emitidas": res_emit, "recebidas": res_receb}


def _processar_ponta(ctx, cnpj, mes, ano, pasta_destino, ponta, url_path, sel_btn_principal,
                     nome_empresa=""):
    """
    Processa uma ponta (emitidas ou recebidas).
    Retorna (resultado_dict, nome_empresa).
    Para emitidas, extrai o nome do #ddlContribuinte e o retorna para reuso em recebidas.
    """
    page = ctx.new_page()
    try:
        log.info(f"[{cnpj}] {ponta} — navegando para {url_path}")
        page.goto(URL_BASE + url_path, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        # Extrai nome do contribuinte na tela de emitidas (ddlContribuinte disponível aqui)
        if ponta == "emitidas" and not nome_empresa:
            nome_empresa = extrair_nome_contribuinte(page)

        # Preenche filtros de competência
        page.locator(SEL_ANO).select_option(str(ano))
        page.locator(SEL_MES).select_option(str(mes))
        log.info(f"[{cnpj}] {ponta} — competência {mes:02d}/{ano}")

        # Clica Visualizar (carrega resultados na mesma página)
        page.click(SEL_VISUALIZAR)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1500)

        # Clica no botão que abre o popup de resumo
        btn = _localizar_btn_consultar(page, ponta, sel_btn_principal)
        if btn is None:
            log.info(f"[{cnpj}] {ponta} — botão não encontrado; empresa não possui esta ponta.")
            return ({"arquivo": None, "qtd": 0, "status": "sem_botao",
                     "detalhe": "Empresa não possui esta ponta no portal"}, nome_empresa)

        # Captura o popup que abre via window.open (ConsultarNotas)
        with ctx.expect_page(timeout=15_000) as popup_info:
            btn.click()
        popup = popup_info.value
        popup.wait_for_load_state("domcontentloaded")
        popup.wait_for_timeout(1500)

        qtd = _ler_quantidade(popup)
        log.info(f"[{cnpj}] {ponta} — quantidade: {qtd}")

        # Seleciona formato PDF e dispara download via botão nativo do portal
        nome_arquivo = _nome_arquivo(cnpj, nome_empresa, ponta, mes, ano)
        caminho = os.path.join(pasta_destino, nome_arquivo)
        popup.locator("#ddlTipoArquivo").select_option("5")  # 5 = PDF
        with popup.expect_download(timeout=30_000) as dl_info:
            popup.click("#btGerar")
        download = dl_info.value
        download.save_as(caminho)
        log.info(f"[{cnpj}] {ponta} — PDF salvo: {caminho}")

        popup.close()
        return ({"arquivo": caminho, "qtd": qtd, "status": "ok", "detalhe": ""}, nome_empresa)

    except Exception as e:
        log.error(f"[{cnpj}] {ponta} — erro: {e}")
        return ({"arquivo": None, "qtd": 0, "status": "erro", "detalhe": str(e)}, nome_empresa)
    finally:
        try:
            page.close()
        except Exception:
            pass


def _localizar_btn_consultar(page, ponta, sel_principal):
    """Localiza o botão que dispara ConsultarNotas para a ponta correta."""
    # 1. Seletor principal confirmado
    try:
        el = page.locator(sel_principal).first
        if el.is_visible(timeout=2000):
            return el
    except Exception:
        pass

    # 2. Fallback: qualquer input com ConsultarNotas no onclick
    try:
        els = page.locator("input[onclick*='ConsultarNotas']").all()
        if els:
            log.warning(f"[{ponta}] Seletor principal não encontrado — usando fallback ConsultarNotas")
            return els[0]
    except Exception:
        pass

    # 3. Para emitidas: tenta texto do botão
    if ponta == "emitidas":
        for sel in ["input[value*='Emitida']", "input[value*='EMITIDA']",
                    "button:has-text('Emitidas')"]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=1000):
                    return el
            except Exception:
                pass

    return None


def _ler_quantidade(popup_page) -> int:
    """Extrai a quantidade de NFS-e do resumo do popup."""
    try:
        texto = popup_page.inner_text("body")
        # "Quantidade NFS-e: 0" ou "Quantidade NFS-e:\n0"
        m = re.search(r"Quantidade\s+NFS-e[:\s]+(\d+)", texto, re.IGNORECASE)
        if m:
            return int(m.group(1))
        # Fallback: primeiro número isolado após "Quantidade"
        m = re.search(r"Quantidade[^\d]*(\d+)", texto, re.IGNORECASE)
        if m:
            return int(m.group(1))
    except Exception as e:
        log.warning(f"Não consegui ler quantidade: {e}")
    return 0


# ── Lote ─────────────────────────────────────────────────────────────────────

def executar_lote(empresas: list, mes: int, ano: int, pasta_destino: str,
                  stop_flag, progress_cb, empresa_cb, cfg: dict) -> dict:
    """
    Processa um lote de empresas sequencialmente.

    empresas:    [{"cnpj": str, "senha": str}, ...]
    stop_flag:   threading.Event — set() para cancelar
    progress_cb: fn(pct, msg, cnpj)
    empresa_cb:  fn(cnpj, status, emitidas, recebidas, indice, total)
    cfg:         dict de configuração (Anti-Captcha key, headless, etc.)

    Retorna: {"total": int, "ok": int, "erros": int, "cancelado": bool}
    """
    from playwright.sync_api import sync_playwright

    total     = len(empresas)
    ok_count  = 0
    err_count = 0
    modo_manual = not cfg.get("sm_anticaptcha_api_key", "").strip()
    headless    = False if modo_manual else cfg.get("sm_headless", True)
    pausa_s   = float(cfg.get("sm_pausa_entre_empresas_s", 2))

    progress_cb(0, f"Iniciando lote de {total} empresa(s)...", "")

    import sys as _sys, asyncio as _asyncio
    if _sys.platform == "win32":
        _loop = _asyncio.ProactorEventLoop()
        _asyncio.set_event_loop(_loop)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            for idx, empresa in enumerate(empresas, start=1):
                if stop_flag.is_set():
                    log.info("Lote cancelado pelo usuário.")
                    progress_cb(None, "Cancelado pelo usuário.", "")
                    return {"total": total, "ok": ok_count,
                            "erros": err_count, "cancelado": True}

                cnpj  = empresa["cnpj"]
                senha = empresa["senha"]
                pct   = int((idx - 1) / total * 100)
                progress_cb(pct, f"[{idx}/{total}] {cnpj}", cnpj)

                # Contexto isolado por empresa (sem vazamento de sessão)
                ctx = browser.new_context(accept_downloads=True)
                page = ctx.new_page()
                page.set_default_timeout(60_000)

                status    = "ok"
                detalhe   = ""
                res_emit  = {"arquivo": None, "qtd": 0, "status": "pendente", "detalhe": ""}
                res_receb = {"arquivo": None, "qtd": 0, "status": "pendente", "detalhe": ""}

                try:
                    login(page, cnpj, senha, cfg)
                    res = emitir_documentos(ctx, cnpj, mes, ano, pasta_destino)
                    res_emit  = res["emitidas"]
                    res_receb = res["recebidas"]

                    if res_emit["status"] == "erro" or res_receb["status"] == "erro":
                        status  = "erro"
                        detalhe = " | ".join(filter(None, [
                            res_emit.get("detalhe") if res_emit["status"] == "erro" else None,
                            res_receb.get("detalhe") if res_receb["status"] == "erro" else None,
                        ]))
                    ok_count += 1

                except RuntimeError as e:
                    # Captcha falhou
                    status  = "captcha_falhou"
                    detalhe = str(e)
                    err_count += 1
                    log.error(f"[{cnpj}] captcha_falhou: {e}")

                except Exception as e:
                    status  = "erro"
                    detalhe = str(e)
                    err_count += 1
                    log.error(f"[{cnpj}] erro inesperado: {e}")

                finally:
                    try:
                        ctx.close()
                    except Exception:
                        pass

                empresa_cb(
                    cnpj=cnpj,
                    status=status,
                    emitidas=res_emit,
                    recebidas=res_receb,
                    detalhe=detalhe,
                    indice=idx,
                    total=total,
                )

                pct_pos = int(idx / total * 100)
                progress_cb(pct_pos, f"[{idx}/{total}] {cnpj} — {status}", cnpj)

                # Pausa interruptível entre empresas
                if idx < total and not stop_flag.is_set():
                    if stop_flag.wait(timeout=pausa_s):
                        break

        finally:
            try:
                browser.close()
            except Exception:
                pass

    cancelado = stop_flag.is_set()
    progress_cb(100 if not cancelado else None,
                "Lote concluído." if not cancelado else "Cancelado.", "")
    return {"total": total, "ok": ok_count, "erros": err_count, "cancelado": cancelado}
