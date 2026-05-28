"""Estado compartilhado entre os supervisores via arquivo no OneDrive.

Mantém um JSON ao lado da planilha master com o estado dos fluxos por
competência (processado / lançado, quem fez, quando). Substitui as flags
`contabil_processado_<YYYY-MM>`, `dp_lancado_<YYYY-MM>` etc que ficavam
apenas no `config.json` de cada máquina.

Formato:
{
  "contabil": {
    "2026-05": {
      "processado": {"em": "20/05/2026 14:33", "por": "***", "host": "..."},
      "lancado":    {"em": "20/05/2026 14:50", "por": "***", "host": "..."}
    }
  },
  "dp": {
    "2026-05": {
      "carol_importada": {"em": "...", "por": "***", "host": "...", "caminho": "..."},
      "lancado":         {"em": "...", "por": "***", "host": "..."}
    }
  },
  "fiscal": {
    "2026-04": {
      "lancado": {"em": "...", "por": "***", "host": "..."}
    }
  }
}
"""

import os
import json
import time
import logging
from datetime import datetime


NOME_ARQUIVO = "estado_compartilhado.json"
LOCK_SUFIXO = ".lock"
LOCK_TIMEOUT_SEGUNDOS = 30  # Lock órfão é removido após este tempo


def _caminho(master_path):
    """JSON fica na mesma pasta da master (pasta sincronizada)."""
    if not master_path:
        return None
    return os.path.join(os.path.dirname(master_path), NOME_ARQUIVO)


def _caminho_lock(master_path):
    p = _caminho(master_path)
    return (p + LOCK_SUFIXO) if p else None


def _adquirir_lock(master_path, tentativas=15, intervalo=0.3):
    """Lock cooperativo curto para serializar read-modify-write em estado_compartilhado.

    Diferente do lock da master (5min): este é de duração ~milissegundos.
    Limpa lock órfão se mais antigo que LOCK_TIMEOUT_SEGUNDOS.
    Retorna True se conseguiu adquirir.
    """
    p = _caminho_lock(master_path)
    if not p:
        return False
    for _ in range(tentativas):
        # Limpa lock órfão antes de tentar
        if os.path.exists(p):
            try:
                idade = time.time() - os.path.getmtime(p)
                if idade > LOCK_TIMEOUT_SEGUNDOS:
                    os.remove(p)
                    logging.warning(f"[ESTADO] Lock órfão removido ({idade:.0f}s).")
            except Exception:
                pass
        try:
            # open("x") falha se já existir — atômico no NTFS
            with open(p, "x") as f:
                f.write(f"{os.getpid()}\n{datetime.now().isoformat()}")
            return True
        except FileExistsError:
            time.sleep(intervalo)
        except Exception as e:
            logging.warning(f"[ESTADO] Falha ao adquirir lock: {e}")
            return False
    return False


def _liberar_lock(master_path):
    p = _caminho_lock(master_path)
    if p and os.path.exists(p):
        try:
            os.remove(p)
        except Exception as e:
            logging.warning(f"[ESTADO] Falha ao liberar lock {p}: {e}")


def ler(master_path):
    """Lê o estado compartilhado. Retorna dict vazio se não existir / inválido."""
    p = _caminho(master_path)
    if not p or not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        # Diferencia "corrompido" de "não existe" — preserva observabilidade.
        logging.error(f"[ESTADO] JSON corrompido em {p}: {e}")
        return {}
    except Exception as e:
        logging.warning(f"[ESTADO] Falha ao ler {p}: {e}")
        return {}


def _gravar(master_path, data):
    """Escrita atômica: grava num .tmp e usa os.replace (atômico no NTFS/ReFS).
    Garante que um crash mid-write não corrompe o arquivo original."""
    p = _caminho(master_path)
    if not p:
        return False
    temp_p = p + ".tmp"
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(temp_p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            try:
                os.fsync(f.fileno())  # garante flush ao disco antes do rename
            except OSError:
                pass  # alguns sistemas (OneDrive virtual) podem não suportar fsync
        os.replace(temp_p, p)  # atômico
        return True
    except Exception as e:
        logging.error(f"[ESTADO] Falha ao gravar {p}: {e}")
        # Limpa temp se restou
        try:
            if os.path.exists(temp_p):
                os.remove(temp_p)
        except Exception:
            pass
        return False


def marcar(master_path, modulo, competencia, evento, **extras):
    """Marca um evento de um módulo numa competência.

    Protegido por lock cooperativo: dois supervisores chamando simultaneamente
    são serializados (o segundo aguarda o primeiro liberar antes de ler/escrever).

    Exemplo:
        marcar(path, "contabil", "2026-05", "processado", por="***", host="...")
    """
    if not all([master_path, modulo, competencia, evento]):
        return False
    if not _adquirir_lock(master_path):
        logging.error(f"[ESTADO] Não conseguiu lock para marcar {modulo}/{competencia}/{evento}")
        return False
    try:
        data = ler(master_path)
        data.setdefault(modulo, {}).setdefault(competencia, {})
        registro = {"em": datetime.now().strftime("%d/%m/%Y %H:%M")}
        registro.update({k: v for k, v in extras.items() if v is not None})
        data[modulo][competencia][evento] = registro
        return _gravar(master_path, data)
    finally:
        _liberar_lock(master_path)


def obter(master_path, modulo, competencia):
    """Retorna o dict de eventos do módulo na competência. Vazio se nada registrado."""
    data = ler(master_path)
    return data.get(modulo, {}).get(competencia, {})


def remover(master_path, modulo, competencia, evento=None):
    """Remove um evento específico ou toda a competência de um módulo."""
    if not _adquirir_lock(master_path):
        logging.error(f"[ESTADO] Não conseguiu lock para remover {modulo}/{competencia}")
        return False
    try:
        data = ler(master_path)
        if modulo not in data or competencia not in data[modulo]:
            return False
        if evento is None:
            del data[modulo][competencia]
        else:
            data[modulo][competencia].pop(evento, None)
        return _gravar(master_path, data)
    finally:
        _liberar_lock(master_path)
