import imaplib
import email
from email.header import decode_header
import re
import datetime
import time
from loguru import logger

class GmailService:
    def __init__(self, username, app_password):
        self.username = username
        self.password = app_password
        self.mail = imaplib.IMAP4_SSL("imap.gmail.com")

    def connect(self):
        try:
            self.mail.login(self.username, self.password)
            logger.info("Conectado ao Gmail via IMAP com sucesso.")
        except Exception as e:
            logger.error(f"Erro na conexão com o Gmail: {e}")
            raise

    def wait_for_sharepoint_code(self, timeout_minutes=5, folder="INBOX"):
        """
        Aguarda a chegada do e-mail do SharePoint contendo o código de verificação
        (O remetente geralmente é no-reply@notify.microsoft.com ou similar)
        """
        # Se a label tiver espaços, o IMAP exige aspas duplas, ex: '"TOKAI - XML"'
        try:
            folder_formatted = f'"{folder}"' if ' ' in folder else folder
            status, _ = self.mail.select(folder_formatted)
            if status != "OK":
                logger.warning(f"Não foi possível selecionar a pasta/marcador {folder_formatted}. Tentando INBOX...")
                self.mail.select("INBOX")
        except Exception as e:
            logger.error(f"Erro ao selecionar marcador {folder}: {e}")
            self.mail.select("INBOX")
            
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        logger.info(f"Buscando código de verificação. Timeout: {timeout_minutes} min...")

        while time.time() - start_time < timeout_seconds:
            # Buscar emails UNSEEN (não lidos) do remetente específico ou com assunto de código
            # O assunto de exemplo foi: "*Código de verificação da conta: 58488919*" 
            # ou "30082006 é o seu código de verificação da Microsoft OneDrive."
            status, messages = self.mail.search(None, '(UNSEEN)')
            
            if status == "OK" and messages[0]:
                email_ids = messages[0].split()
                # Processa os emails, idealmente o último/mais recente (email_ids[-1])
                for e_id in reversed(email_ids):
                    status, msg_data = self.mail.fetch(e_id, "(RFC822)")
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            subject, encoding = decode_header(msg["Subject"])[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding if encoding else "utf-8")
                                
                            sender = msg.get("From", "")
                            
                            # Filtro: microsoft ou onedrive
                            if "microsoft" in sender.lower() or "sharepoint" in sender.lower():
                                logger.debug(f"Assunto do email Microsoft recebido: {subject}")
                                # Procura na mensagem algum número de 8 digitos.
                                code = self._extract_code_from_subject_or_body(subject, msg)
                                if code:
                                    logger.success(f"Código encontrado: {code}")
                                    return code

            # Espera 10 segundos antes de tentar novamente para não dar rate limit
            time.sleep(10)

        logger.warning("Timeout: Nenhum código do SharePoint foi recebido no tempo limite.")
        return None

    def _extract_code_from_subject_or_body(self, subject, msg):
        """Extrai um código OTP de 8 dígitos do assunto ou corpo do e-mail."""
        # Tenta no assunto primeiro (ex: "30082006 é o seu código de verificação...")
        match = re.search(r'\b(\d{8})\b', subject)
        if match:
            return match.group(1)

        # Procura no corpo
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" or content_type == "text/html":
                    body = part.get_payload(decode=True).decode()
                    match = re.search(r'\b(\d{8})\b', body)
                    if match:
                        return match.group(1)
        else:
            body = msg.get_payload(decode=True).decode()
            match = re.search(r'\b(\d{8})\b', body)
            if match:
                return match.group(1)
        
        return None
