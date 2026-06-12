import os
import requests
from datetime import datetime
from loguru import logger

class NotificadorService:
    """
    Serviço de notificações via Telegram Bot API.
    Removido suporte a WhatsApp conforme solicitado.
    Utiliza as credenciais TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID do .env.
    """
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.modulo = "Auto Tokai (SharePoint)"
        
        if self.token:
            self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        else:
            self.api_url = None

    def _enviar_telegram(self, mensagem: str):
        """Envia uma mensagem para o chat do Telegram configurado usando HTML parse mode."""
        if not self.token or not self.chat_id:
            logger.warning("Telegram insuficiente no .env (TOKEN ou CHAT_ID ausente).")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": mensagem,
            "parse_mode": "HTML"
        }

        try:
            resp = requests.post(self.api_url, json=payload, timeout=15)
            if resp.status_code == 200:
                logger.info("Notificação Telegram enviada com sucesso.")
                return True
            else:
                logger.error(f"Erro Telegram: HTTP {resp.status_code} - {resp.text[:150]}")
                return False
        except Exception as e:
            logger.error(f"Falha na conexão com API do Telegram: {e}")
            return False

    def notify_start(self, periodo=""):
        """Notifica o início da execução."""
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        msg = (
            f"<b>[INICIO] Execucao Iniciada: {self.modulo}</b>\n"
            f"Periodo: {periodo}\n"
            f"Inicio: {agora}"
        )
        self._enviar_telegram(msg)

    def notify_end(self, sucessos: int, erros: int, lista_erros: list = None):
        """Notifica o fim da execução com resumo resumido."""
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        status_tag = "[OK]" if erros == 0 else "[ALERTA]"
        
        msg = (
            f"<b>{status_tag} Execucao Concluida: {self.modulo}</b>\n"
            f"Sucessos: {sucessos}\n"
            f"Erros: {erros}\n"
            f"Fim: {agora}"
        )
        
        if lista_erros and len(lista_erros) > 0:
            msg += "\n\n<b>Detalhes dos Erros:</b>\n"
            for erro in lista_erros[:10]:
                msg += f"- {erro}\n"
            if len(lista_erros) > 10:
                msg += f"\n<i>... e mais {len(lista_erros) - 10} erros ocultados.</i>"
                
        self._enviar_telegram(msg)

    def notify_error(self, erro_msg: str):
        """Notifica um erro crítico que interrompeu o robô."""
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        msg = (
            f"<b>[ERRO CRITICO] {self.modulo}</b>\n"
            f"Descricao: {erro_msg}\n"
            f"Hora: {agora}"
        )
        self._enviar_telegram(msg)
