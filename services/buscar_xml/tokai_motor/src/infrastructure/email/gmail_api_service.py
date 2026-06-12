import os
import base64
import re
import time
from loguru import logger
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class GmailApiService:
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    # O limite de dias aceito para o e-mail do SharePoint (MAX_EMAIL_AGE_DAYS)
    # agora é lido dinamicamente de os.getenv() no momento da validação, 
    # para evitar problemas de escopo de importação em testes manuais.

    def __init__(self, credentials_path='config/credentials.json', token_path='config/token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Arquivo {self.credentials_path} não encontrado. "
                        "Baixe as credenciais OAuth2 do Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)

            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)

    def get_latest_sharepoint_link(self, label_name="TOKAI - XML"):
        """
        Busca o link do SharePoint no e-mail mais recente com a etiqueta informada.

        CORREÇÃO — TASK 2 › Escalada: valida a data do e-mail encontrado.
        Se o e-mail mais recente for mais antigo que MAX_EMAIL_AGE_DAYS dias,
        a execução é abortada com erro explícito em vez de navegar com um link
        potencialmente revogado — o que causaria falha silenciosa em todos os
        clientes com SEM_ARQUIVOS sem indicação clara da causa raiz.
        """
        logger.info("Buscando e-mail mais recente com a etiqueta: %s", label_name)

        results = self.service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        label_id = None
        for label in labels:
            if label['name'].upper() == label_name.upper():
                label_id = label['id']
                break

        q = f'label:{label_id}' if label_id else f'label:"{label_name}"'
        logger.info("Executando query na API: %s", q)

        messages_res = self.service.users().messages().list(userId='me', q=q, maxResults=5).execute()
        messages = messages_res.get('messages', [])

        if not messages:
            logger.warning("Nenhuma mensagem encontrada com a query '%s'. Tentando fallback por assunto...", q)
            q_fallback = 'subject:"compartilhou a pasta \\"XML\\" com você" OR subject:"compartilhou a pasta"'
            logger.info("Executando query de fallback: %s", q_fallback)
            messages_res = self.service.users().messages().list(userId='me', q=q_fallback, maxResults=5).execute()
            messages = messages_res.get('messages', [])

        if not messages:
            logger.error("Nenhum e-mail de SharePoint/OneDrive localizado na conta.")
            return None

        msg_id = messages[0]['id']
        msg = self.service.users().messages().get(userId='me', id=msg_id).execute()

        body = self._get_message_body(msg)

        links = re.findall(r'https?://[^\s<>"]+sharepoint\.com/[^\s<>"]*', body)
        if not links:
            links = [l for l in re.findall(r'https?://[^\s<>"]+', body) if 'sharepoint.com' in l]

        if links:
            target_link = max(links, key=len)
            target_link = target_link.rstrip('.').replace('&amp;', '&')
            logger.success("Link do SharePoint encontrado.")
            # Não logamos a URL completa pois pode conter tokens de acesso.
            return target_link

        logger.error("Link do SharePoint não localizado no corpo do e-mail.")
        return None

    # ------------------------------------------------------------------
    # CORREÇÃO — TASK 2 › Escalada: método de validação de frescor do
    # e-mail. Rejeita e-mails mais antigos que MAX_EMAIL_AGE_DAYS para
    # evitar uso de links de compartilhamento expirados ou revogados.
    # ------------------------------------------------------------------
    def _validar_frescor_email(self, msg: dict, label_name: str) -> bool:
        """
        Valida se o e-mail foi recebido nos últimos MAX_EMAIL_AGE_DAYS dias.

        Usa `internalDate` do Gmail (ms epoch) que é sempre confiável,
        independente do fuso horário do remetente ou do formato do header Date.

        Retorna True se o e-mail é recente o suficiente, False caso contrário.
        """
        try:
            internal_date_ms = int(msg.get('internalDate', 0))
            if internal_date_ms == 0:
                logger.warning(
                    "Não foi possível determinar a data do e-mail (internalDate ausente). "
                    "Prosseguindo com o link encontrado sem validação de frescor."
                )
                return True  # Falha suave

            email_age_seconds = time.time() - (internal_date_ms / 1000)
            email_age_days = email_age_seconds / 86_400

            limite_dias = int(os.getenv("MAX_EMAIL_AGE_DAYS", 35))

            if email_age_days > limite_dias:
                logger.error(
                    f"CRÍTICO: E-mail mais recente com etiqueta '{label_name}' tem {email_age_days:.0f} dias de idade "
                    f"(limite: {limite_dias} dias). O link de compartilhamento pode estar expirado ou "
                    f"revogado. Abortando para evitar falhas em cascata em todos os clientes.\n"
                    f"Ação necessária: verifique se um novo e-mail de compartilhamento foi "
                    f"enviado e se a etiqueta '{label_name}' está aplicada corretamente."
                )
                return False

            logger.info(
                "E-mail de compartilhamento com %.0f dia(s) de idade — dentro do limite de %d dias.",
                email_age_days, limite_dias
            )
            return True

        except Exception as e:
            logger.warning("Erro ao validar frescor do e-mail: %s. Prosseguindo sem validação.", e)
            return True  # Falha suave

    def get_latest_otp_code(self, min_timestamp: int = None):
        """
        Busca o código de verificação de 8 dígitos mais recente.
        Filtro `after:` garante que apenas e-mails pós-solicitação sejam considerados.
        """
        logger.info("Buscando código de verificação OTP (8 dígitos) via API...")
        q = 'from:no-reply@notify.microsoft.com "código de verificação"'

        if min_timestamp is not None:
            q += f' after:{min_timestamp}'
            logger.info("Filtro de tempo aplicado: somente e-mails após timestamp %d.", min_timestamp)

        messages_res = self.service.users().messages().list(userId='me', q=q, maxResults=1).execute()
        messages = messages_res.get('messages', [])

        if not messages:
            return None

        msg_id = messages[0]['id']
        msg = self.service.users().messages().get(userId='me', id=msg_id).execute()

        subject = ""
        for header in msg['payload']['headers']:
            if header['name'] == 'Subject':
                subject = header['value']
                break

        body = self._get_message_body(msg)

        match = re.search(r'\b(\d{8})\b', subject)
        if match:
            return match.group(1)

        match = re.search(r'\b(\d{8})\b', body)
        if match:
            return match.group(1)

        return None

    def _get_message_body(self, msg):
        payload = msg['payload']
        html = self._recursive_body_extract(payload, 'text/html')
        if html:
            return html
        return self._recursive_body_extract(payload, 'text/plain')

    def _recursive_body_extract(self, payload, target_mime):
        if 'parts' in payload:
            for part in payload['parts']:
                body = self._recursive_body_extract(part, target_mime)
                if body:
                    return body

        mime_type = payload.get('mimeType')
        if mime_type == target_mime:
            data = payload.get('body', {}).get('data')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        return ""
