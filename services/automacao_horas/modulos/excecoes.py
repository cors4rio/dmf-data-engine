"""
Leitura compartilhada das listas de exceção por setor.

Arquivos esperados em `config/nao_faz_setor/`:
  - DP_NAO.txt
  - CONTABIL_NAO.txt
  - FISCAL_NAO.txt

Cada arquivo é uma lista livre de códigos `codi_emp` (um por linha; sufixos
descritivos como ' LTDA', '1:30' ou anotações são ignorados pelo parser).
"""

import os
import re
import sys
import logging

def _resolver_pasta():
    """Resolve a pasta de exceções tanto em dev quanto após PyInstaller.
    Em frozen: ao lado do .exe. Em dev: 1 nível acima de modulos/."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "config", "nao_faz_setor")

PASTA = _resolver_pasta()
NOMES = {
    "dp": "DP_NAO.txt",
    "contabil": "CONTABIL_NAO.txt",
    "fiscal": "FISCAL_NAO.txt",
}


def caminho_excecao(setor):
    nome = NOMES.get(setor)
    if not nome:
        return None
    return os.path.join(PASTA, nome)


def ler_codigos_setor(setor):
    """Retorna set[str] com os códigos `codi_emp` listados no arquivo do setor.
    Códigos não-numéricos / comentários são ignorados silenciosamente.
    """
    caminho = caminho_excecao(setor)
    if not caminho or not os.path.exists(caminho):
        return set()
    codigos = set()
    try:
        with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith("#"):
                    continue
                if "Não entra" in linha or "Nao entra" in linha:
                    continue
                m = re.search(r"^\s*(\d+)", linha.replace(";", " ").replace("\t", " "))
                if m:
                    try:
                        codigos.add(str(int(m.group(1))))
                    except (ValueError, TypeError):
                        pass
    except Exception as e:
        logging.error(f"[EXCECOES] Falha ao ler {caminho}: {e}")
    return codigos


def metadados_setor(setor):
    """Para a UI: caminho, existe, total de códigos, mtime formatado."""
    from datetime import datetime
    caminho = caminho_excecao(setor)
    info = {"setor": setor, "caminho": caminho, "existe": False,
            "total": 0, "modificado_em": None}
    if caminho and os.path.exists(caminho):
        info["existe"] = True
        try:
            st = os.stat(caminho)
            info["modificado_em"] = datetime.fromtimestamp(st.st_mtime).strftime("%d/%m/%Y %H:%M")
        except Exception:
            pass
        info["total"] = len(ler_codigos_setor(setor))
    return info
