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
import logging
from datetime import datetime


NOME_ARQUIVO = "estado_compartilhado.json"


def _caminho(master_path):
    """JSON fica na mesma pasta da master (pasta sincronizada)."""
    if not master_path:
        return None
    return os.path.join(os.path.dirname(master_path), NOME_ARQUIVO)


def ler(master_path):
    """Lê o estado compartilhado. Retorna dict vazio se não existir / inválido."""
    p = _caminho(master_path)
    if not p or not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"[ESTADO] Falha ao ler {p}: {e}")
        return {}


def _gravar(master_path, data):
    p = _caminho(master_path)
    if not p:
        return False
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"[ESTADO] Falha ao gravar {p}: {e}")
        return False


def marcar(master_path, modulo, competencia, evento, **extras):
    """Marca um evento de um módulo numa competência.

    Exemplo:
        marcar(path, "contabil", "2026-05", "processado", por="***", host="...")
    """
    if not all([master_path, modulo, competencia, evento]):
        return False
    data = ler(master_path)
    data.setdefault(modulo, {}).setdefault(competencia, {})
    registro = {"em": datetime.now().strftime("%d/%m/%Y %H:%M")}
    registro.update({k: v for k, v in extras.items() if v is not None})
    data[modulo][competencia][evento] = registro
    return _gravar(master_path, data)


def obter(master_path, modulo, competencia):
    """Retorna o dict de eventos do módulo na competência. Vazio se nada registrado."""
    data = ler(master_path)
    return data.get(modulo, {}).get(competencia, {})


def remover(master_path, modulo, competencia, evento=None):
    """Remove um evento específico ou toda a competência de um módulo."""
    data = ler(master_path)
    if modulo not in data or competencia not in data[modulo]:
        return False
    if evento is None:
        del data[modulo][competencia]
    else:
        data[modulo][competencia].pop(evento, None)
    return _gravar(master_path, data)
