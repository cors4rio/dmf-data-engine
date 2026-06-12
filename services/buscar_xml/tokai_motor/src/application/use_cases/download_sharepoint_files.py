import os
import json
import datetime
from dateutil.relativedelta import relativedelta
from loguru import logger
from src.infrastructure.email.gmail_api_service import GmailApiService
from src.infrastructure.browser.sharepoint_automation import SharePointBrowserAuth
# FALHA 7 CORRIGIDA: FileManager removido — era instanciado mas nunca chamado.
# Toda a lógica de extração foi migrada para robust_extractor.py.
from src.domain.config import CLIENT_MAPPING

class DownloadSharePointFilesUseCase:
    def __init__(self):
        # Carregando variáveis do .env
        self.email_user = os.environ.get("EMAIL_USER")
        self.sp_url = os.environ.get("SHAREPOINT_BASE_URL")
        self.storage_path = os.environ.get("STORAGE_STATE_PATH", "./playwright_storage.json")
        self.net_drive = os.environ.get("NETWORK_DRIVE_Z")
        self.gmail_label = os.environ.get("GMAIL_LABEL", "TOKAI - XML")

        # Novo fluxo via API
        self.gmail_api = GmailApiService()
        self.sp_auth = SharePointBrowserAuth(self.email_user, None, self.storage_path)
        # FALHA 7: FileManager não é mais instanciado aqui.

    def execute(self, unidade_alvo: str = None, allowed_clients_override: list = None, periodo: dict = None):
        logger.info("Iniciando rotina de automação RPA Visual (Gmail -> SharePoint -> Z:)")

        from src.domain.config import CLIENT_MAPPING

        if periodo and periodo.get("mes") and periodo.get("ano"):
            # Período escolhido pelo usuário na UI
            mes = int(periodo["mes"])
            ano = int(periodo["ano"])
            target_month_sp = f"{mes:02d}-{ano}"   # Ex: "03-2026"
            target_year     = str(ano)              # Ex: "2026"
            logger.info(f"Mês alvo (UI): {target_month_sp} (ano: {target_year})")
        else:
            # Comportamento padrão: mês anterior
            hoje = datetime.datetime.now()
            mes_alvo = hoje - relativedelta(months=1)
            target_month_sp = mes_alvo.strftime("%m-%Y")
            target_year     = mes_alvo.strftime("%Y")
            logger.info(f"Mês alvo (automático): {target_month_sp} (ano: {target_year})")

        # Alerta antecipado: verifica se o mapa JSON tem o mês alvo antes de iniciar o browser.
        # Isso evita que o robô faça login, navegue e só então descubra que o mapa está desatualizado.
        # O nome do arquivo de mapa é dinâmico — carrega 'sharepoint_map_{ano}.json' para o ano alvo.
        map_path = os.path.join("config", f"sharepoint_map_{target_year}.json")
        if os.path.exists(map_path):
            with open(map_path, 'r', encoding='utf-8') as f:
                mapa = json.load(f)
            if target_year not in mapa or target_month_sp not in mapa.get(target_year, {}):
                logger.error(
                    f"ATENCAO: O mes '{target_month_sp}' NAO esta no mapa '{map_path}'. "
                    f"Execute: python scripts/generate_map.py --ano {target_year}"
                )
                return
        else:
            logger.error(
                f"Arquivo de mapa '{map_path}' nao encontrado. "
                f"Execute: python scripts/generate_map.py --ano {target_year}"
            )
            return

        # Valida e normaliza o caminho de destino antes de abrir qualquer browser
        if not self.net_drive or not self.net_drive.strip():
            logger.error(
                "CRÍTICO: Variável NETWORK_DRIVE_Z não definida no .env. "
                "Caminho de destino desconhecido — abortando para não salvar em local incorreto."
            )
            return 0, 0, ["NETWORK_DRIVE_Z não definida no .env"]

        self.net_drive = os.path.normpath(self.net_drive.strip().strip('"'))

        if not os.path.exists(self.net_drive):
            logger.error(
                f"CRÍTICO: Drive de rede '{self.net_drive}' inacessível. "
                f"Verifique se Z: está mapeado — abortando."
            )
            return 0, 0, [f"Drive de rede inacessível: {self.net_drive}"]

        logger.info(f"Drive de rede validado: '{self.net_drive}'")

        # allowed_clients_override: lista direta passada pelo adapter (multi-seleção da UI)
        if allowed_clients_override is not None:
            allowed_clients = allowed_clients_override
            logger.info(f"Filtro de unidades (override): {allowed_clients}")
        elif unidade_alvo:
            allowed_clients = []
            for reg, clientes in mapa[target_year][target_month_sp].items():
                for cl_sp in clientes:
                    mapping_name = CLIENT_MAPPING.get(cl_sp, cl_sp)
                    if unidade_alvo.lower() in cl_sp.lower() or unidade_alvo.lower() in mapping_name.lower():
                        allowed_clients.append(cl_sp)
            if not allowed_clients:
                logger.error(f"Unidade alvo '{unidade_alvo}' não encontrada no mapa do SharePoint para o mês {target_month_sp}.")
                return 0, 0, [f"Unidade alvo '{unidade_alvo}' não encontrada."]
            logger.info(f"Filtro de unidade aplicado. Clientes permitidos: {allowed_clients}")
        else:
            allowed_clients = None

        # Parâmetros para a navegação visual completa e download
        navigation_params = {
            'year': target_year,
            'month_sp': target_month_sp,
            'network_path': self.net_drive,  # Z:\#ROTINA AUTOMATICA NF\NFCe
            'mapping': CLIENT_MAPPING,
            'allowed_clients': allowed_clients
        }

        # O link vem da API do Gmail, eliminando o bloqueio de login visual
        sp_direct_link = self.gmail_api.get_latest_sharepoint_link(self.gmail_label)

        if not sp_direct_link:
            logger.error("Não foi possível obter o link do SharePoint via API. Abortando.")
            return

        # O fluxo agora recebe a URL direta
        # Modificado para retornar os resultados da execução
        resultados = self.sp_auth.run_auth_flow(self.gmail_label, navigation_params=navigation_params, direct_url=sp_direct_link)

        logger.success("Execução do UseCase de Download finalizada.")
        return resultados or (0, 0, [])

