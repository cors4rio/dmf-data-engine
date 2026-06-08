"""Lock cooperativo para escrita concorrente na planilha master.

Como funciona:
  - Antes de gravar na master, o app cria um arquivo `<nome_master>.dmflock`
    ao lado dela (na pasta sincronizada do OneDrive).
  - O arquivo contém JSON com {usuario, host, modulo, iniciado_em, expira_em}.
  - Outro usuário que tente gravar vê o lock e é bloqueado com mensagem clara
    indicando quem está executando.
  - O lock expira em LOCK_TIMEOUT_MINUTOS para evitar lock órfão se o app crashar.
  - Após a gravação (ou falha), o app libera o lock.

NÃO é um lock cripto-forte: é cooperativo. Não impede um adversário, mas
impede colisão entre os 5 supervisores legítimos rodando ao mesmo tempo.
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta


LOCK_TIMEOUT_MINUTOS = 5
LOCK_SUFIXO = ".dmflock"


def _caminho_lock(caminho_master):
    return caminho_master + LOCK_SUFIXO


def _ler_lock(caminho_master):
    """Retorna dict do lock, ou None se ausente / inválido / expirado.

    B06: validação dupla contra clock skew entre máquinas (OneDrive):
      1. mtime do arquivo (visto localmente em todas as máquinas com o mesmo offset
         relativo) — se mais antigo que LOCK_TIMEOUT + margem, descarta.
      2. `expira_em` ISO interno — protege contra mtime alterado por OneDrive sync.
    Lock é considerado expirado se QUALQUER um dos dois disser que expirou.
    """
    p = _caminho_lock(caminho_master)
    if not os.path.exists(p):
        return None
    try:
        # Check 1: mtime do arquivo (resistente a clock skew, sensível a OneDrive sync delay)
        try:
            idade_segundos = time.time() - os.path.getmtime(p)
            limite = LOCK_TIMEOUT_MINUTOS * 60 + 60  # +60s de margem para skew
            if idade_segundos > limite:
                logging.info(f"[LOCK] Lock descartado por idade do arquivo "
                             f"({idade_segundos:.0f}s > {limite}s) em {p}.")
                return None
        except OSError:
            pass  # se mtime falhar, cai no check ISO

        with open(p, encoding="utf-8") as f:
            data = json.load(f)

        # Check 2: timestamp ISO interno (resistente a alterações de mtime pelo OneDrive)
        expira = datetime.fromisoformat(data["expira_em"])
        if datetime.now() >= expira:
            logging.info(f"[LOCK] Lock expirado encontrado em {p} (de {data.get('usuario')}). Ignorando.")
            return None
        return data
    except Exception as e:
        logging.warning(f"[LOCK] Lock inválido em {p}: {e}")
        return None


def verificar_lock(caminho_master):
    """Para a UI consultar se há lock ativo. Retorna dict do lock ou None."""
    return _ler_lock(caminho_master)


def adquirir_lock(caminho_master, usuario, host, modulo, tentativas=3, intervalo=1.0):
    """Tenta criar o lock. Retorna (True, info) se conseguiu,
    (False, info_do_lock_existente) caso contrário."""
    for tentativa in range(tentativas):
        lock_existente = _ler_lock(caminho_master)
        if lock_existente is not None:
            # Se o lock é nosso (mesmo usuário + host), aceitamos como já adquirido.
            if (lock_existente.get("usuario") == usuario
                    and lock_existente.get("host") == host):
                logging.info(f"[LOCK] Lock próprio encontrado, reutilizando.")
                return True, lock_existente
            if tentativa < tentativas - 1:
                time.sleep(intervalo)
                continue
            return False, lock_existente

        # Lock livre — tenta criar
        agora = datetime.now()
        info = {
            "usuario": usuario,
            "host": host,
            "modulo": modulo,
            "iniciado_em": agora.isoformat(timespec="seconds"),
            "expira_em": (agora + timedelta(minutes=LOCK_TIMEOUT_MINUTOS)).isoformat(timespec="seconds"),
        }
        try:
            # Escrita atômica (open com "x" falha se já existe — evita TOCTOU)
            p = _caminho_lock(caminho_master)
            with open(p, "x", encoding="utf-8") as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
            logging.info(f"[LOCK] Lock adquirido por {usuario} ({modulo}).")
            return True, info
        except FileExistsError:
            # Alguém criou entre a checagem e a escrita — tenta de novo
            if tentativa < tentativas - 1:
                time.sleep(intervalo)
                continue
            return False, _ler_lock(caminho_master) or {}
        except Exception as e:
            logging.error(f"[LOCK] Falha ao criar lock: {e}")
            return False, {"erro": str(e)}
    return False, {}


def liberar_lock(caminho_master, usuario=None, host=None):
    """Remove o lock. Se `usuario`/`host` forem fornecidos, só remove se for nosso."""
    p = _caminho_lock(caminho_master)
    if not os.path.exists(p):
        return True
    try:
        if usuario or host:
            atual = _ler_lock(caminho_master)
            if atual and (atual.get("usuario") != usuario or atual.get("host") != host):
                logging.warning(f"[LOCK] Tentativa de liberar lock de outro usuário "
                                f"({atual.get('usuario')}). Ignorada.")
                return False
        os.remove(p)
        logging.info(f"[LOCK] Lock liberado.")
        return True
    except Exception as e:
        logging.error(f"[LOCK] Falha ao liberar lock: {e}")
        return False


def renovar_lock(caminho_master, usuario, host):
    """Estende a expiração do lock atual (caso uma operação esteja demorando)."""
    atual = _ler_lock(caminho_master)
    if not atual or atual.get("usuario") != usuario or atual.get("host") != host:
        return False
    atual["expira_em"] = (datetime.now() + timedelta(minutes=LOCK_TIMEOUT_MINUTOS)).isoformat(timespec="seconds")
    try:
        with open(_caminho_lock(caminho_master), "w", encoding="utf-8") as f:
            json.dump(atual, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"[LOCK] Falha ao renovar lock: {e}")
        return False
