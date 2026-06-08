"""Helpers para lidar com arquivos em pastas sincronizadas do OneDrive/SharePoint.

Problemas conhecidos no Windows + cliente OneDrive:
  - Arquivos podem estar como "Online-only" (placeholders) e só baixam no acesso.
  - Travas transitórias quando o cliente OneDrive está renomeando/sincronizando.
  - Lockfile `~$nome.xlsx` quando o Excel está com o arquivo aberto.

Esse módulo encapsula essas três situações para uso por leitores/escritores.
"""

import os
import time
import logging
import ctypes

# Atributos do Windows (FILE_ATTRIBUTE_*)
_RECALL_ON_DATA_ACCESS = 0x00400000  # arquivo Online-only do OneDrive
_RECALL_ON_OPEN       = 0x00040000   # placeholder antigo
_OFFLINE              = 0x00001000   # explicitamente offline (raro)


def lockfile_path(caminho):
    """Caminho do arquivo de lock do Excel para um dado arquivo."""
    return os.path.join(os.path.dirname(caminho), "~$" + os.path.basename(caminho))


def esta_aberto_no_excel(caminho):
    return os.path.exists(lockfile_path(caminho))


def atributos_arquivo(caminho):
    """Retorna inteiro com atributos do Windows ou None se não conseguir ler."""
    try:
        if os.name != "nt":
            return None
        attrs = ctypes.windll.kernel32.GetFileAttributesW(ctypes.c_wchar_p(caminho))
        if attrs == 0xFFFFFFFF:  # INVALID_FILE_ATTRIBUTES
            return None
        return attrs
    except Exception:
        return None


def esta_online_only(caminho):
    """True se o arquivo é placeholder do OneDrive (precisa baixar para usar)."""
    attrs = atributos_arquivo(caminho)
    if attrs is None:
        return False
    return bool(attrs & (_RECALL_ON_DATA_ACCESS | _RECALL_ON_OPEN | _OFFLINE))


def forcar_download(caminho, timeout=30):
    """Toca o arquivo para o cliente OneDrive baixá-lo localmente.
    Aguarda até `timeout` segundos para o atributo Online-only sumir."""
    if not os.path.exists(caminho):
        return False
    if not esta_online_only(caminho):
        return True
    logging.info(f"[ONEDRIVE] '{caminho}' está online-only. Forçando download...")
    try:
        # Abrir e ler 1 byte força o OneDrive a iniciar o download.
        with open(caminho, "rb") as f:
            f.read(1)
    except Exception as e:
        logging.warning(f"[ONEDRIVE] Falha ao tocar arquivo p/ download: {e}")
        return False
    inicio = time.time()
    while time.time() - inicio < timeout:
        if not esta_online_only(caminho):
            logging.info(f"[ONEDRIVE] Download concluído para '{caminho}'.")
            return True
        time.sleep(0.5)
    logging.warning(f"[ONEDRIVE] Timeout aguardando download de '{caminho}'.")
    return False


def chamar_com_retry(funcao, tentativas=4, intervalo_inicial=0.5, descricao=""):
    """Executa `funcao()` com retry exponencial em PermissionError/OSError.
    Útil para esperar o cliente OneDrive liberar o arquivo após sync."""
    intervalo = intervalo_inicial
    ultimo_erro = None
    for t in range(tentativas):
        try:
            return funcao()
        except PermissionError as e:
            ultimo_erro = e
            logging.warning(f"[ONEDRIVE] PermissionError (tentativa {t+1}/{tentativas}) "
                            f"em {descricao or 'operação'}: {e}")
            time.sleep(intervalo)
            intervalo *= 2
        except OSError as e:
            # WinError 33 (lock), 32 (sharing violation): também retentar.
            if getattr(e, "winerror", None) in (32, 33):
                ultimo_erro = e
                logging.warning(f"[ONEDRIVE] OSError WinError={e.winerror} "
                                f"(tentativa {t+1}/{tentativas}): {e}")
                time.sleep(intervalo)
                intervalo *= 2
            else:
                raise
    raise ultimo_erro if ultimo_erro else RuntimeError("retry esgotado")


def preparar_para_uso(caminho):
    """Pipeline padrão antes de abrir um arquivo do OneDrive:
       1. Verifica se existe.
       2. Verifica lockfile (arquivo aberto no Excel).
       3. Força download se for Online-only.
    Retorna (ok: bool, motivo: str|None).
    """
    if not os.path.exists(caminho):
        return False, "arquivo_nao_existe"
    if esta_aberto_no_excel(caminho):
        return False, "arquivo_aberto_no_excel"
    if esta_online_only(caminho):
        if not forcar_download(caminho):
            return False, "online_only_sem_download"
    return True, None
