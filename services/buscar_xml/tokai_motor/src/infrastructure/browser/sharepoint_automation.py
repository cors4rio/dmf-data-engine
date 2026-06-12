import os
import re
import time
import json
import shutil
import requests
import urllib.parse as urlparse
from datetime import datetime
from loguru import logger
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
from src.infrastructure.file_system.robust_extractor import extrair_arquivo_robusto

# ---------------------------------------------------------------
# Constantes de Timeout (em milissegundos)
# ---------------------------------------------------------------
TIMEOUT_NAVEGACAO = 120_000   # 2 min para carregar página
TIMEOUT_ELEMENTO  = 60_000   # 1 min para um elemento aparecer
TIMEOUT_DOWNLOAD  = 600_000  # 10 min para download finalizar (arquivos grandes)
ESPERA_RENDER     = 10_000   # 10s de espera para JS renderizar
MAX_RETRIES       = 3        # Tentativas por operação

DEBUG_SCREENSHOTS = os.getenv("DEBUG_SCREENSHOTS", "False") == "True"

# ---------------------------------------------------------------
# CORREÇÃO — TASK 2 › Segurança: caracteres inválidos em nomes de arquivo
# Regex de sanitização centralizada para safe_name usado em paths de debug.
# Cobre todos os caracteres proibidos em Windows e Linux além de / e espaço.
# ---------------------------------------------------------------
_SAFE_NAME_RE = re.compile(r'[\\/:*?"<>|\s]')


def _sanitize_name(name: str) -> str:
    """Remove/substitui caracteres inválidos de sistema de arquivos."""
    return _SAFE_NAME_RE.sub('_', name)


class SharePointBrowserAuth:
    def __init__(self, target_email, app_password, storage_state_path):
        self.email = target_email
        # CORREÇÃO — TASK 2 › Segurança: password pode ser None (instanciado assim
        # em download_sharepoint_files.py). Armazenamos como está, mas _login_gmail
        # agora valida antes de usar, evitando TypeError silencioso.
        self.password = app_password
        self.storage_path = storage_state_path
        self.gmail_url = "https://accounts.google.com/ServiceLogin?service=mail"

    # ------------------------------------------------------------------
    # CORREÇÃO — TASK 1: Dismiss do modal "Compartilhar" do SharePoint
    # O link recebido do Gmail contém `openShare=true` na URL, fazendo o
    # OneDrive abrir automaticamente o painel de compartilhamento. Esse
    # overlay bloqueia todos os cliques nos arquivos e causa os timeouts
    # relatados nos logs. Este método detecta e fecha o modal antes de
    # qualquer interação com a lista de arquivos.
    # Também remove o parâmetro `openShare` da URL base para evitar que
    # ele se propague às subpastas navegadas em navigate_and_download.
    # ------------------------------------------------------------------
    def _fechar_modal_compartilhar(self, page: Page) -> bool:
        """
        Detecta e fecha o modal "Compartilhar" do OneDrive/SharePoint.
        Tenta três estratégias em ordem de especificidade:
          1. Botão de fechar via data-automationid (mais robusto)
          2. Botão aria-label="Fechar" (i18n PT-BR)
          3. Tecla Escape como fallback universal

        Retorna True se o modal foi detectado (e fechado ou tentativa feita),
        False se o modal não estava presente.
        """
        MODAL_SELECTORS = [
            '[data-automationid="SharingDialog"]',
            '[role="dialog"]:has-text("Compartilhar")',
            '[role="dialog"]:has-text("Share")',
        ]

        CLOSE_SELECTORS = [
            'button[data-automationid="sharingDialogClose"]',
            'button[aria-label="Fechar"]',
            'button[aria-label="Close"]',
            '[role="dialog"] button[title="Fechar"]',
            # Fallback: botão × genérico dentro de qualquer dialog
            '[role="dialog"] button:has-text("×")',
        ]

        modal_presente = False
        for sel in MODAL_SELECTORS:
            try:
                if page.locator(sel).is_visible(timeout=3_000):
                    modal_presente = True
                    logger.warning(
                        "Modal 'Compartilhar' detectado (seletor: %s). "
                        "Fechando antes de prosseguir...", sel
                    )
                    break
            except PlaywrightTimeout:
                continue

        if not modal_presente:
            return False

        # Tenta fechar pelo botão
        fechado = False
        for close_sel in CLOSE_SELECTORS:
            try:
                btn = page.locator(close_sel).first
                if btn.is_visible(timeout=2_000):
                    btn.click(timeout=5_000)
                    # Aguarda o modal desaparecer
                    page.wait_for_selector(
                        '[data-automationid="SharingDialog"], [role="dialog"]:has-text("Compartilhar")',
                        state="hidden",
                        timeout=5_000,
                    )
                    logger.success("Modal 'Compartilhar' fechado via botão (%s).", close_sel)
                    fechado = True
                    break
            except Exception:
                continue

        # Fallback: Escape
        if not fechado:
            logger.info("Botão de fechar não encontrado. Tentando Escape...")
            try:
                page.keyboard.press("Escape")
                page.wait_for_timeout(1_500)
                logger.success("Modal dispensado via Escape.")
                fechado = True
            except Exception as e:
                logger.error("Falha ao fechar modal via Escape: %s", e)

        return True  # Modal foi detectado independentemente do resultado do close

    def run_auth_flow(self, gmail_label="TOKAI - XML", navigation_params=None, direct_url=None):
        """Fluxo: Link Direto (via API) ou Login Manual -> SharePoint -> Navegação"""
        with sync_playwright() as p:
            has_state = os.path.exists(self.storage_path)

            browser = p.chromium.launch(
                headless=os.getenv("HEADLESS_MODE", "False") == "True",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    # Flags de baixo consumo de RAM (importante em máquinas modestas):
                    "--disable-gpu",                       # sem aceleração gráfica (headless)
                    "--disable-dev-shm-usage",             # não usa /dev/shm (evita pico)
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--disable-renderer-backgrounding",
                    "--disable-features=site-per-process,TranslateUI",  # menos processos
                    "--js-flags=--max-old-space-size=128",  # limita heap do V8
                    "--renderer-process-limit=1",
                ]
            )

            context_kwargs = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "accept_downloads": True
            }
            if has_state:
                logger.info("Estado anterior encontrado. Carregando sessão...")
                context_kwargs["storage_state"] = self.storage_path

            context = browser.new_context(**context_kwargs)
            context.set_default_timeout(TIMEOUT_ELEMENTO)
            page = context.new_page()

            try:
                if direct_url:
                    # CORREÇÃO — TASK 2 › Integridade: remove `openShare=true` da URL
                    # antes de navegar, evitando que o modal seja ativado e que o
                    # parâmetro se propague para todas as subpastas via base_nav_url.
                    clean_url = self._remover_param_url(direct_url, "openShare")
                    if clean_url != direct_url:
                        logger.info("Parâmetro 'openShare' removido da URL de entrada.")

                    logger.info("Acessando SharePoint diretamente: %s", clean_url)
                    page.goto(clean_url, wait_until="commit", timeout=TIMEOUT_NAVEGACAO)
                    self._esperar_sharepoint_carregar(page)

                    # CORREÇÃO — TASK 1: Fecha o modal de compartilhamento antes de qualquer
                    # outra ação. Chamado aqui (entrada) e também em navigate_and_download
                    # (antes de cada cliente) para cobrir reaparições.
                    self._fechar_modal_compartilhar(page)

                else:
                    self._login_gmail(page)
                    logger.info("Navegando para o marcador: %s", gmail_label)
                    page.goto(
                        f"https://mail.google.com/mail/u/0/#label/{gmail_label.replace(' ', '+')}",
                        wait_until="networkidle"
                    )
                    page.wait_for_selector("tr.zA", timeout=20000)
                    page.locator("tr.zA").first.click()
                    page.wait_for_load_state("networkidle")
                    btn_abrir = page.locator("a", has_text="Abrir").first
                    with context.expect_page() as new_page_info:
                        btn_abrir.click()
                    page = new_page_info.value
                    self._fechar_modal_compartilhar(page)

                self._handle_sharepoint_otp(page)

                # CORREÇÃO — TASK 2 › Segurança: salva backup do storage_state antes
                # de sobrescrever, permitindo rollback manual se o novo estado for inválido.
                self._salvar_storage_state_com_backup(context)

                if navigation_params:
                    logger.info("Iniciando fase de navegação e download de arquivos...")
                    return self.navigate_and_download(
                        page,
                        navigation_params['year'],
                        navigation_params['month_sp'],
                        navigation_params['network_path'],
                        navigation_params['mapping'],
                        navigation_params.get('allowed_clients')
                    )
                return None

            except Exception as e:
                logger.exception("Falha na automação visual: %s", e)
                try:
                    page.screenshot(path="erro_automacao_fatal.png")
                except Exception:
                    pass
            finally:
                browser.close()

    # ------------------------------------------------------------------
    # CORREÇÃO — TASK 2 › Segurança: backup do storage_state antes de
    # sobrescrever. Evita perda total de sessão válida em caso de falha
    # durante uma execução que corromperia o estado persistido.
    # ------------------------------------------------------------------
    def _salvar_storage_state_com_backup(self, context):
        """Salva storage_state com backup rotacionado (.bak)."""
        try:
            if os.path.exists(self.storage_path):
                backup_path = self.storage_path + ".bak"
                shutil.copy2(self.storage_path, backup_path)
                logger.debug("Backup do storage_state salvo em: %s", backup_path)
            context.storage_state(path=self.storage_path)
            logger.success("Sessão e cookies persistidos.")
        except Exception as e:
            logger.warning("Não foi possível persistir storage_state: %s", e)

    # ------------------------------------------------------------------
    # CORREÇÃO — TASK 2 › Integridade: helper para remover parâmetros
    # indesejados da URL sem quebrar o resto da query string.
    # ------------------------------------------------------------------
    @staticmethod
    def _remover_param_url(url: str, param: str) -> str:
        """Remove um parâmetro específico da query string de uma URL."""
        try:
            parsed = urlparse.urlparse(url)
            params = urlparse.parse_qs(parsed.query, keep_blank_values=True)
            params.pop(param, None)
            nova_query = urlparse.urlencode(params, doseq=True)
            return urlparse.urlunparse(parsed._replace(query=nova_query))
        except Exception:
            return url  # Falha suave: retorna URL original

    def _esperar_sharepoint_carregar(self, page: Page):
        """Aguarda o SharePoint renderizar a interface de arquivos."""
        logger.info("Aguardando renderização do SharePoint...")
        page.wait_for_timeout(ESPERA_RENDER)
        try:
            page.wait_for_selector(
                '[data-automationid="DetailsList"], [role="presentation"], .od-ItemsScopeList',
                timeout=30_000
            )
            logger.success("Interface de arquivos detectada.")
        except PlaywrightTimeout:
            logger.warning("Lista de arquivos não detectada em 30s. Continuando mesmo assim...")

    def _login_gmail(self, page: Page):
        # CORREÇÃO — TASK 2 › Segurança: valida password antes de usar,
        # evitando TypeError obscuro se instanciado com password=None.
        if not self.password:
            raise ValueError(
                "app_password não configurado. Defina EMAIL_APP_PASSWORD no .env "
                "antes de usar o fluxo de login manual do Gmail."
            )

        logger.info("Iniciando processo de login no Google...")
        page.goto(self.gmail_url)

        if page.locator('input[type="email"]').is_visible(timeout=10000):
            logger.info("Preenchendo e-mail...")
            page.fill('input[type="email"]', self.email)
            page.press('input[type="email"]', "Enter")
            page.wait_for_timeout(3000)

            if page.locator('input[type="password"]').is_visible(timeout=10000):
                logger.info("Preenchendo senha...")
                page.fill('input[type="password"]', self.password)
                page.press('input[type="password"]', "Enter")
                page.wait_for_load_state("networkidle")
            else:
                logger.error("Falha ao avançar para a tela de senha.")
                page.screenshot(path="google_login_error.png")
                raise Exception("Bloqueio de segurança do Google detectado.")

    def _handle_sharepoint_otp(self, sp_page: Page):
        """
        Trata o desafio OTP do SharePoint.
        CORREÇÃO — TASK 2 › Escalada: após submeter o código, verifica se o
        formulário OTP desapareceu. Se ainda estiver visível, o código foi
        rejeitado (expirado ou inválido) e a execução é abortada com erro
        explícito, evitando que o fluxo continue sem autenticação válida.
        """
        btn_send = sp_page.locator("#btnRequestCode").first
        if not btn_send.is_visible(timeout=5000):
            return  # Sem desafio OTP, segue normalmente

        logger.info("SharePoint solicitou verificação de identidade. Clicando em Enviar Código...")
        btn_send.click()

        logger.info("Aguardando e-mail com código OTP via Gmail API (até 2 minutos)...")
        from src.infrastructure.email.gmail_api_service import GmailApiService
        gmail_api = GmailApiService()

        otp_requested_at = int(time.time())

        code = None
        for tentativa in range(1, 13):
            time.sleep(10)
            logger.info("Buscando OTP... (tentativa %d/12)", tentativa)
            code = gmail_api.get_latest_otp_code(min_timestamp=otp_requested_at)
            if code:
                break

        if not code:
            logger.error(
                "CRÍTICO: Não foi possível obter o código OTP após 2 minutos. "
                "Abortando para evitar falhas em cascata."
            )
            raise RuntimeError(
                "Autenticação SharePoint falhou: código OTP não obtido após 12 tentativas."
            )

        logger.success("Código OTP capturado: %s", code)
        input_otp = sp_page.locator(
            "input[name='otc'], input[id*='Code'], input[placeholder*='código']"
        ).first
        input_otp.wait_for(state="visible", timeout=10000)
        input_otp.fill(code)
        sp_page.locator(
            "button:has-text('Verificar'), button[id*='Verify'], input[type='submit']"
        ).first.click()

        # CORREÇÃO — TASK 2 › Escalada: valida que o formulário OTP sumiu.
        # Se ainda estiver visível após 10s, o código foi rejeitado.
        try:
            sp_page.wait_for_selector(
                "input[name='otc'], input[id*='Code']",
                state="hidden",
                timeout=10_000,
            )
            logger.success("OTP aceito — formulário de verificação dispensado.")
        except PlaywrightTimeout:
            logger.error(
                "CRÍTICO: Formulário OTP ainda visível após submissão. "
                "Código rejeitado (expirado ou inválido). Abortando."
            )
            raise RuntimeError(
                "Autenticação SharePoint falhou: código OTP submetido mas rejeitado pelo servidor."
            )

        logger.info("Aguardando carregamento da estrutura de arquivos...")
        self._esperar_sharepoint_carregar(sp_page)

    def navigate_and_download(
        self, sp_page: Page, target_year: str, target_month_sp: str,
        network_base_path: str, client_mapping: dict, allowed_clients: list = None
    ):
        """Navega via Mapa JSON e realiza o download/extração nos caminhos da rede."""
        from src.domain.config import get_target_month_disk

        map_path = os.path.join("config", f"sharepoint_map_{target_year}.json")
        if not os.path.exists(map_path):
            logger.error(
                "Arquivo de mapa '%s' nao encontrado. "
                "Execute: python scripts/generate_map.py --ano %s", map_path, target_year
            )
            return

        with open(map_path, 'r', encoding='utf-8') as f:
            mapa = json.load(f)

        parsed = urlparse.urlparse(sp_page.url)
        params = urlparse.parse_qs(parsed.query)
        xml_id = params.get('id', [''])[0]

        if not xml_id:
            logger.error("Falha ao capturar ID da pasta raiz na URL.")
            return

        # CORREÇÃO — TASK 2 › Integridade: base_nav_url reconstruída via
        # urlparse em vez de split frágil. Remove também `openShare` para
        # não propagar o parâmetro nas navegações de subpastas.
        params_base = {k: v for k, v in params.items() if k != 'id' and k != 'openShare'}
        base_nav_url = urlparse.urlunparse(
            parsed._replace(query=urlparse.urlencode(params_base, doseq=True))
        )
        # Garante que a URL base termina com '&' ou '?' para concatenar &id=
        separator = '&' if '?' in base_nav_url else '?'
        base_nav_url = base_nav_url + separator

        FILE_LIST_SELECTORS = [
            '[data-automationid="DetailsList"]',
            '[data-automationid="FieldRenderer-name"]',
            '[role="grid"]',
            '[role="row"]',
            '.ms-DetailsList',
            '.od-ItemsScopeList',
            '.ms-List',
        ]

        FILE_NAME_SELECTORS = [
            '[data-automationid="FieldRenderer-name"]',
            'button[data-automationid="name"]',
            '[role="gridcell"] button',
            '.ms-DetailsRow-cell button',
            'span.ms-DetailsRow-cell',
        ]

        def navigate_to_path(sub_path):
            """Navega para uma subpasta com retries automáticos."""
            full_id = f"{xml_id}/{sub_path}".replace("//", "/")
            target_url = f"{base_nav_url}id={urlparse.quote(full_id)}"

            for attempt in range(1, MAX_RETRIES + 1):
                logger.info("Navegando: %s... (tentativa %d/%d)", sub_path, attempt, MAX_RETRIES)
                try:
                    sp_page.goto(target_url, wait_until="commit", timeout=TIMEOUT_NAVEGACAO)
                    sp_page.wait_for_timeout(ESPERA_RENDER)

                    # CORREÇÃO — TASK 1: Fecha modal de compartilhamento que pode
                    # reaparecer em qualquer navegação de subpasta.
                    self._fechar_modal_compartilhar(sp_page)

                    lista_encontrada = False
                    for sel in FILE_LIST_SELECTORS:
                        try:
                            sp_page.wait_for_selector(sel, timeout=10_000)
                            logger.success("Pasta %s carregada (seletor: %s).", sub_path, sel)
                            lista_encontrada = True
                            break
                        except PlaywrightTimeout:
                            continue

                    if not lista_encontrada:
                        logger.warning("Nenhum seletor de lista encontrado para %s. Aguardando 10s...", sub_path)
                        sp_page.wait_for_timeout(10_000)

                    return True

                except PlaywrightTimeout as e:
                    logger.warning("Timeout na tentativa %d para %s: %s", attempt, sub_path, e)
                    if attempt < MAX_RETRIES:
                        sp_page.wait_for_timeout(5000)
                    else:
                        logger.error("Falha definitiva ao navegar para %s após %d tentativas.", sub_path, MAX_RETRIES)
                        return False
                except Exception as e:
                    logger.error("Erro inesperado ao navegar para %s: %s", sub_path, e)
                    return False

        def _encontrar_arquivos_zip_rar():
            """Busca elementos de arquivo .zip/.rar usando múltiplas estratégias."""
            for sel in FILE_NAME_SELECTORS:
                locators = sp_page.locator(
                    f'{sel}:has-text(".zip"), {sel}:has-text(".rar")'
                ).all()
                if locators:
                    logger.info("Arquivos encontrados via seletor CSS: %s (%d arquivo(s))", sel, len(locators))
                    return locators

            logger.info("Seletores CSS falharam. Tentando busca por texto em buttons...")
            encontrados = []
            all_buttons = sp_page.locator('button').all()
            for btn in all_buttons:
                try:
                    text = btn.inner_text(timeout=2000).strip()
                    if text and ('.zip' in text.lower() or '.rar' in text.lower()):
                        encontrados.append(btn)
                except Exception:
                    continue
            if encontrados:
                logger.info("Arquivos encontrados via busca em buttons (%d arquivo(s))", len(encontrados))
                return encontrados

            logger.info("Busca em buttons falhou. Escaneando DOM via JavaScript...")
            js_result = sp_page.evaluate("""
                () => {
                    const results = [];
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_ELEMENT, null, false
                    );
                    while (walker.nextNode()) {
                        const el = walker.currentNode;
                        const text = (el.textContent || '').trim();
                        const title = el.getAttribute('title') || '';
                        const combined = text + ' ' + title;
                        if ((/\\.zip/i.test(combined) || /\\.rar/i.test(combined)) && el.offsetParent !== null) {
                            const childHasSame = Array.from(el.children).some(c =>
                                /\\.(zip|rar)/i.test((c.textContent || '') + ' ' + (c.getAttribute('title') || ''))
                            );
                            if (!childHasSame || el.children.length === 0) {
                                results.push({
                                    tag: el.tagName,
                                    text: text.substring(0, 150),
                                    classes: (el.className || '').substring(0, 200),
                                    automationId: el.getAttribute('data-automationid'),
                                    role: el.getAttribute('role'),
                                    title: title,
                                    id: el.id
                                });
                            }
                        }
                    }
                    return results;
                }
            """)

            if js_result:
                logger.info("JavaScript encontrou %d elemento(s) com .zip/.rar no DOM.", len(js_result))
                for item in js_result:
                    logger.debug(
                        "  Tag=%s | automationId=%s | role=%s | text=%s",
                        item['tag'], item.get('automationId'), item.get('role'), item['text'][:80]
                    )

                encontrados_js = []
                for item in js_result:
                    aid = item.get('automationId')
                    title = item.get('title', '')
                    if aid:
                        loc = sp_page.locator(f'[data-automationid="{aid}"]').all()
                        for l in loc:
                            try:
                                t = l.inner_text(timeout=2000)
                                if '.zip' in t.lower() or '.rar' in t.lower():
                                    encontrados_js.append(l)
                            except Exception:
                                continue
                    elif title and ('.zip' in title.lower() or '.rar' in title.lower()):
                        loc = sp_page.locator(f'[title="{title}"]').first
                        encontrados_js.append(loc)

                if encontrados_js:
                    logger.info("Locators criados via JS: %d arquivo(s)", len(encontrados_js))
                    return encontrados_js
            else:
                logger.warning("JavaScript não encontrou nenhum elemento com .zip/.rar no DOM.")

            return []

        def baixar_e_extrair(nome_cliente_sp, mapping_real_name):
            """Baixa e extrai arquivos compactados com tratamento robusto de erros."""
            logger.info("Buscando arquivos compactados para %s...", nome_cliente_sp)
            sp_page.wait_for_timeout(5000)

            # CORREÇÃO — TASK 2 › Segurança: usa _sanitize_name centralizado
            # em vez de replace(' ','_').replace('/','_') que omitia outros
            # caracteres inválidos no Windows (\, :, *, ?, ", <, >, |).
            safe_name = _sanitize_name(nome_cliente_sp)

            if DEBUG_SCREENSHOTS:
                sp_page.screenshot(path=f"debug_{safe_name}.png")
                logger.info("[DEBUG] Screenshot salvo: debug_%s.png", safe_name)

            zips_locators = _encontrar_arquivos_zip_rar()

            if not zips_locators:
                msg = "Nenhum arquivo .zip/.rar encontrado na pasta"
                logger.warning("%s para %s.", msg, nome_cliente_sp)
                _registrar_erro(nome_cliente_sp, mapping_real_name, 'SEM_ARQUIVOS', msg)
                try:
                    html = sp_page.content()
                    html_path = f"debug_html_{safe_name}.html"
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(html)
                    logger.info("HTML da página salvo em %s para análise.", html_path)
                except Exception:
                    pass
                return

            logger.info("Encontrados %d arquivo(s) para %s.", len(zips_locators), nome_cliente_sp)

            for idx, zip_el in enumerate(zips_locators, 1):
                try:
                    nome_arquivo = zip_el.inner_text().strip() or zip_el.get_attribute('title')
                    match = re.search(r'[\w\-. ]+\.(zip|rar)', nome_arquivo, re.IGNORECASE)
                    if not match:
                        continue
                    nome_arquivo = match.group()

                    logger.info(f"[{idx}/{len(zips_locators)}] Fazendo download de: {nome_arquivo}")

                    zip_el.scroll_into_view_if_needed()
                    zip_el.wait_for(state="visible", timeout=TIMEOUT_ELEMENTO)

                    for click_attempt in range(1, MAX_RETRIES + 1):
                        try:
                            zip_el.click(button="right", timeout=TIMEOUT_ELEMENTO)
                            break
                        except PlaywrightTimeout:
                            logger.warning("Timeout no clique direito (tentativa %d/%d)", click_attempt, MAX_RETRIES)
                            if click_attempt < MAX_RETRIES:
                                sp_page.wait_for_timeout(3000)
                            else:
                                raise

                    sp_page.wait_for_timeout(2000)

                    btn_download = sp_page.locator(
                        'button[data-automationid="downloadCommand"], button[name="Baixar"]'
                    ).first
                    if not btn_download.is_visible(timeout=5000):
                        btn_download = sp_page.get_by_text("Baixar", exact=True).first

                    if btn_download.is_visible(timeout=10000):
                        for d_attempt in range(1, 4):
                            try:
                                with sp_page.expect_download(timeout=TIMEOUT_DOWNLOAD) as download_info:
                                    btn_download.click()
                                download = download_info.value

                                download_url = download.url
                                # CORREÇÃO — TASK 2 › Segurança: cookies não são logados.
                                # A variável é capturada aqui mas nunca impressa em logs.
                                cookies = sp_page.context.cookies()

                                logger.info(f"Aguardando download de {nome_arquivo} (Tentativa {d_attempt}/3)...")

                                data_disco = get_target_month_disk()
                                caminho_final = os.path.join(network_base_path, mapping_real_name, data_disco)
                                os.makedirs(caminho_final, exist_ok=True)
                                file_path = os.path.join(caminho_final, nome_arquivo)

                                try:
                                    temp_path = download.path()
                                    if temp_path:
                                        logger.info(
                                            f"Download via browser concluído "
                                            f"({os.path.getsize(temp_path) / 1024 / 1024:.1f} MB)"
                                        )
                                        download.save_as(file_path)
                                    else:
                                        raise Exception("Temp path vazio")
                                except Exception as e_path:
                                    logger.warning(
                                        "Download via browser falhou (%s). Iniciando fallback via Streaming...", e_path
                                    )
                                    success_req = self._download_via_requests(download_url, cookies, file_path)
                                    if not success_req:
                                        if d_attempt == 3:
                                            _registrar_erro(
                                                nome_cliente_sp, mapping_real_name,
                                                'DOWNLOAD_FALHOU', "Nativo e Fallback falharam", nome_arquivo
                                            )
                                        continue

                                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                    saved_size = os.path.getsize(file_path)
                                    logger.success(
                                        f"Salvo com sucesso: {nome_arquivo} ({saved_size / 1024 / 1024:.1f} MB)"
                                    )
                                else:
                                    msg = "Arquivo ausente ou vazio após download"
                                    logger.error("%s: %s", msg, file_path)
                                    if d_attempt == 3:
                                        _registrar_erro(
                                            nome_cliente_sp, mapping_real_name, 'SAVE_FALHOU', msg, nome_arquivo
                                        )
                                    continue

                                resultado_extracao = extrair_arquivo_robusto(
                                    file_path, caminho_final, nome_cliente_sp
                                )
                                if not resultado_extracao['sucesso']:
                                    _registrar_erro(
                                        nome_cliente_sp, mapping_real_name, 'EXTRACAO_FALHOU',
                                        resultado_extracao['mensagem'], nome_arquivo
                                    )
                                else:
                                    # CORREÇÃO — TASK 2 › Integridade: só achata se XMLs
                                    # foram confirmados na extração. Evita achatar pastas
                                    # que produziram apenas arquivos não-XML (corrompidos
                                    # ou formato inesperado).
                                    if resultado_extracao['xmls_encontrados'] > 0:
                                        logger.info(
                                            f"Extração: {resultado_extracao['arquivos_extraidos']} arquivo(s), "
                                            f"{resultado_extracao['xmls_encontrados']} XML(s). Nivelando pastas..."
                                        )
                                        self._achatar_pastas(caminho_final)
                                        # Validação pós-nivelamento: confirma XMLs no destino final
                                        try:
                                            xmls_finais = [
                                                f for f in os.listdir(caminho_final)
                                                if f.lower().endswith('.xml')
                                            ]
                                            if xmls_finais:
                                                logger.success(
                                                    f"[VALIDAÇÃO] {len(xmls_finais)} XML(s) confirmados "
                                                    f"em '{caminho_final}' — processamento OK."
                                                )
                                            else:
                                                logger.error(
                                                    f"[VALIDAÇÃO] ATENÇÃO: 0 XMLs em '{caminho_final}' "
                                                    f"após nivelamento — verificar manualmente!"
                                                )
                                        except Exception as _e_val:
                                            logger.warning(f"[VALIDAÇÃO] Erro ao contar XMLs finais: {_e_val}")
                                    else:
                                        logger.warning(
                                            "Extração concluída mas NENHUM XML encontrado em '%s'. "
                                            "Achatamento ignorado para preservar estrutura original.",
                                            caminho_final
                                        )
                                        _registrar_erro(
                                            nome_cliente_sp, mapping_real_name,
                                            'SEM_XML_APOS_EXTRACAO',
                                            f"Extração OK mas xmls_encontrados=0. "
                                            f"Arquivos extraídos: {resultado_extracao['arquivos_extraidos']}",
                                            nome_arquivo
                                        )

                                sp_page.wait_for_timeout(3000)
                                break

                            except Exception as e_down:
                                msg = f"Erro no processo de download: {e_down}"
                                logger.warning("%s - %s (Tentativa %d/3)", msg, nome_arquivo, d_attempt)
                                if d_attempt < 3:
                                    sp_page.wait_for_timeout(5000)
                                    try:
                                        zip_el.click(button="right", timeout=TIMEOUT_ELEMENTO)
                                        sp_page.wait_for_timeout(2000)
                                        btn_download = sp_page.locator(
                                            'button[data-automationid="downloadCommand"], button[name="Baixar"]'
                                        ).first
                                        if not btn_download.is_visible(timeout=5000):
                                            btn_download = sp_page.get_by_text("Baixar", exact=True).first
                                    except Exception:
                                        pass
                                else:
                                    _registrar_erro(
                                        nome_cliente_sp, mapping_real_name, 'DOWNLOAD_ERRO', msg, nome_arquivo
                                    )
                    else:
                        msg = "Botão 'Baixar' não localizado"
                        logger.error("%s para %s.", msg, nome_arquivo)
                        _registrar_erro(nome_cliente_sp, mapping_real_name, 'BTN_NAO_ENCONTRADO', msg, nome_arquivo)
                        sp_page.mouse.click(0, 0)

                except Exception as e_file:
                    logger.error("Erro ao processar arquivo %d de %s: %s", idx, nome_cliente_sp, e_file)
                    try:
                        sp_page.mouse.click(0, 0)
                        sp_page.wait_for_timeout(1000)
                    except Exception:
                        pass
                    continue

        # ================================================================
        # Processamento baseado no MAPA
        # ================================================================
        if target_year not in mapa:
            logger.error("Ano %s não mapeado no JSON.", target_year)
            return

        if target_month_sp not in mapa[target_year]:
            logger.error("Mês %s não mapeado no JSON.", target_month_sp)
            return

        estrutura_mes = mapa[target_year][target_month_sp]
        total_clientes = sum(len(c) for c in estrutura_mes.values())
        cliente_atual = 0
        clientes_ok = 0
        clientes_erro = 0

        erros_por_cliente = []

        def _registrar_erro(cliente_sp, cliente_pasta, tipo_erro, mensagem, arquivo=None):
            erro = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'cliente_sp': cliente_sp,
                'cliente_pasta': cliente_pasta,
                'tipo_erro': tipo_erro,
                'mensagem': mensagem,
                'arquivo': arquivo or '-'
            }
            erros_por_cliente.append(erro)
            logger.warning("[ERRO REGISTRADO] %s | %s | %s", tipo_erro, cliente_sp, mensagem)

        for reg, clientes in estrutura_mes.items():
            logger.info("=== Processando Regional: %s (%d clientes) ===", reg, len(clientes))
            for cl_sp in clientes:
                if allowed_clients is not None and cl_sp not in allowed_clients:
                    continue
                
                cliente_atual += 1
                mapping_real_name = client_mapping.get(cl_sp, cl_sp)

                logger.info("--- [%d/%d] Cliente: %s -> %s ---", cliente_atual, total_clientes, cl_sp, mapping_real_name)

                data_disco = get_target_month_disk()
                caminho_final_checker = os.path.join(network_base_path, mapping_real_name, data_disco)

                # CORREÇÃO — TASK 2 › Integridade: Skip mais rigoroso.
                # Verifica não apenas existência de XMLs, mas que pelo menos 1 deles
                # foi modificado nas últimas 24h (criado nesta execução ou em reexecução
                # recente). Isso evita skip indevido causado por XMLs residuais de
                # execuções anteriores corrompidas ou de meses diferentes.
                if os.path.exists(caminho_final_checker):
                    agora = time.time()
                    xmls_recentes = [
                        f for f in os.listdir(caminho_final_checker)
                        if f.lower().endswith('.xml')
                        and (agora - os.path.getmtime(os.path.join(caminho_final_checker, f))) < 86_400
                    ]
                    if xmls_recentes:
                        logger.success(
                            "  >> [SKIP] Cliente %s: %d XML(s) recentes em '%s'. Pulando...",
                            cl_sp, len(xmls_recentes), data_disco
                        )
                        clientes_ok += 1
                        continue
                    elif os.listdir(caminho_final_checker):
                        # Pasta existe mas sem XMLs recentes: avisa e reprocessa
                        logger.warning(
                            "  >> Pasta '%s' existe mas sem XMLs recentes (< 24h). "
                            "Reprocessando cliente %s...",
                            data_disco, cl_sp
                        )

                path_navegacao = f"{target_year}/{target_month_sp}/{reg}/{cl_sp}"

                try:
                    if navigate_to_path(path_navegacao):
                        baixar_e_extrair(cl_sp, mapping_real_name)
                        clientes_ok += 1
                    else:
                        msg = f"Falha ao acessar pasta do cliente após {MAX_RETRIES} tentativas"
                        logger.error(msg)
                        _registrar_erro(cl_sp, mapping_real_name, 'NAVEGACAO_FALHOU', msg)
                        clientes_erro += 1
                except Exception as e_cliente:
                    msg = f"Erro inesperado: {e_cliente}"
                    logger.error("%s - cliente %s", msg, cl_sp)
                    _registrar_erro(cl_sp, mapping_real_name, 'ERRO_INESPERADO', msg)
                    clientes_erro += 1
                    continue

        # ================================================================
        # Relatório Final
        # ================================================================
        logger.success("--- Automação de download concluída via Mapa JSON ---")
        logger.info("Resumo: %d/%d clientes processados. %d com erro.", clientes_ok, total_clientes, clientes_erro)

        if erros_por_cliente:
            logger.warning("\n%s", "=" * 70)
            logger.warning("RELATÓRIO DE ERROS - %d erro(s) encontrado(s)", len(erros_por_cliente))
            logger.warning("%s", "=" * 70)

            erros_por_tipo: dict = {}
            for erro in erros_por_cliente:
                erros_por_tipo.setdefault(erro['tipo_erro'], []).append(erro)

            for tipo, lista in erros_por_tipo.items():
                logger.warning("\n  [%s] (%d ocorrência(s)):", tipo, len(lista))
                for e in lista:
                    logger.warning(
                        "    - %s (%s) | Arquivo: %s | %s",
                        e['cliente_sp'], e['cliente_pasta'], e['arquivo'], e['mensagem']
                    )

            logger.warning("%s\n", "=" * 70)

            relatorio_data = {
                'data_execucao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'mes_referencia': target_month_sp,
                'total_clientes': total_clientes,
                'clientes_ok': clientes_ok,
                'clientes_erro': clientes_erro,
                'erros': erros_por_cliente
            }

            # CORREÇÃO — TASK 2 › Segurança: salva relatório com fallback duplo
            # garantido. Primeiro tenta o drive de rede; se falhar, salva localmente
            # em diretório garantidamente gravável no container.
            report_nome = f"_RELATORIO_ERROS_{target_month_sp.replace('-', '')}.json"
            salvou = False
            for destino in [
                os.path.join(network_base_path, report_nome),
                os.path.join(os.getcwd(), report_nome),
            ]:
                try:
                    os.makedirs(os.path.dirname(destino) or '.', exist_ok=True)
                    with open(destino, 'w', encoding='utf-8') as f:
                        json.dump(relatorio_data, f, ensure_ascii=False, indent=2)
                    logger.info("Relatório de erros salvo em: %s", destino)
                    salvou = True
                    break
                except Exception as ex_report:
                    logger.warning("Falha ao salvar relatório em '%s': %s", destino, ex_report)

            if not salvou:
                logger.error(
                    "ATENÇÃO: Relatório de erros NÃO pôde ser persistido em nenhum destino. "
                    "Os erros foram exibidos no log acima."
                )
        else:
            logger.success("Nenhum erro registrado! Todos os %d clientes processados com sucesso.", total_clientes)

        # Retorna o resumo para o UseCase/Notificador
        return clientes_ok, clientes_erro, [f"{e['cliente_sp']}: {e['mensagem']}" for e in erros_por_cliente]

    def _achatar_pastas(self, diretorio_base):
        """
        Move todos os arquivos de subpastas para a raiz da pasta do mês.
        CORREÇÃO — TASK 2 › Robustez: followlinks=False explicitado para
        evitar loop infinito em caso de symlink apontando para pasta pai
        (cenário possível em ambientes de rede Linux/NFS).
        """
        arquivos_movidos = 0

        try:
            for root, dirs, files in os.walk(diretorio_base, topdown=False, followlinks=False):
                if root == diretorio_base:
                    continue

                for file in files:
                    source_path = os.path.join(root, file)
                    dest_path = os.path.join(diretorio_base, file)

                    try:
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                        shutil.move(source_path, dest_path)
                        arquivos_movidos += 1
                    except Exception as e:
                        logger.warning("Não foi possível mover '%s': %s", file, e)

                try:
                    os.rmdir(root)
                except Exception:
                    pass  # Diretório não vazio — ignorado silenciosamente

            if arquivos_movidos > 0:
                logger.success(
                    f"Nivelamento concluído: {arquivos_movidos} arquivo(s) movidos para {diretorio_base}."
                )
        except Exception as ex:
            logger.error("Erro ao nivelar pastas: %s", ex)

    def _download_via_requests(self, url, playwright_cookies, save_path):
        """
        Fallback: Faz o download via requests usando os cookies do Playwright.
        CORREÇÃO — TASK 2 › Segurança: cookies não são logados em nenhuma
        circunstância (nem em exceções). O log de erro omite a URL completa
        que pode conter tokens de acesso temporários do SharePoint.
        """
        try:
            logger.info("Iniciando download via Requests (Streaming): %s", os.path.basename(save_path))
            session = requests.Session()
            for cookie in playwright_cookies:
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            with session.get(url, headers=headers, stream=True, timeout=600) as response:
                response.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                logger.success("Download via Requests finalizado com sucesso.")
                return True
            return False

        except requests.HTTPError as e:
            # CORREÇÃO: Loga apenas status code, não a URL completa (pode conter tokens).
            logger.error("Falha no fallback de download: HTTP %s", e.response.status_code if e.response else "?")
            return False
        except Exception as e:
            logger.error("Falha no fallback de download: %s", type(e).__name__)
            return False

