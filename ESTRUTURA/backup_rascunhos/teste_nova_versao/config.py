"""
config.py — Núcleo de Configuração Global
DMF Automação | Projeto de Controle de Horas

Uso:
    from _ENGINE.config import cfg

Passagem de parâmetros (via argparse ou direto):
    python processar.py --mes 03 --ano 2026
"""

import os
import argparse
from datetime import date, timedelta
from calendar import monthrange
from pathlib import Path
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# .env  (senhas nunca hardcoded)
# ─────────────────────────────────────────────
load_dotenv(Path(__file__).parent.parent / ".env")

# ─────────────────────────────────────────────
# RAIZ DO PROJETO
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent  # .../ESTRUTURA/

# ─────────────────────────────────────────────
# ODBC — Domínio Sistemas (Sybase/SQL Anywhere)
# ─────────────────────────────────────────────
ODBC_DSN   = os.getenv("ODBC_DSN",   "Contabil")
ODBC_USER  = os.getenv("ODBC_USER",  "EXTERNO")
ODBC_PASS  = os.getenv("ODBC_PASS",  "")         # Obrigatório no .env

ODBC_CONN_STRING = (
    f"DSN={ODBC_DSN};"
    f"UID={ODBC_USER};"
    f"PWD={ODBC_PASS};"
)

# ─────────────────────────────────────────────
# MÓDULO FISCAL — código sist_log no GELOGUSER
# ─────────────────────────────────────────────
SIST_LOG_FISCAL     = 5
SIST_LOG_FOLHA      = 12
SIST_LOG_CONTABIL   = 14
SIST_LOG_GERAL      = 2

ADICIONAL_FISCAL    = 1.80   # +80% sobre tempo bruto (v1.2 — 2026-04-12)

# ─────────────────────────────────────────────
# PLANILHAS
# ─────────────────────────────────────────────
def _resolve_planilha(candidates: list[str]) -> Path | None:
    """Retorna o primeiro caminho existente da lista."""
    for c in candidates:
        p = Path(c)
        if p.exists():
            return p
    return None

_MASTER_CANDIDATES = [
    r"C:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\CONTROLE_DE_HORAS_DMF.xlsm",
    str(BASE_DIR / "CONTROLE_DE_HORAS_DMF.xlsm"),
    str(BASE_DIR / "CONTROLE_DE_HORAS_DMF.xlsx"),
]
_CONTABIL_CANDIDATES = [
    r"C:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\HORAS CONTABEIS_.xlsx",
    str(BASE_DIR / "HORAS CONTABEIS_.xlsx"),
]

PLANILHA_MASTER   = _resolve_planilha(_MASTER_CANDIDATES)
PLANILHA_CONTABIL = _resolve_planilha(_CONTABIL_CANDIDATES)

# ─────────────────────────────────────────────
# PLANILHA CAROL  (template dinâmico por mês)
# ─────────────────────────────────────────────
def carol_path(mes: int, ano: int) -> Path | None:
    """Retorna o caminho da planilha Carol para o mês/ano informados."""
    mes_str = str(mes).zfill(2)
    candidates = [
        rf"C:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\Controle de Empregados {mes_str}(CAROL).xls",
        str(BASE_DIR / f"Controle de Empregados {mes_str}(CAROL).xls"),
        str(BASE_DIR / f"Controle de Empregados {mes_str}.{ano}(CAROL).xls"),
    ]
    return _resolve_planilha(candidates)

# ─────────────────────────────────────────────
# ARQUIVOS DE EXCEÇÃO
# ─────────────────────────────────────────────
EXCECAO_DP_NAO       = BASE_DIR / "nao_faz_setor" / "DP NAO.txt"
EXCECAO_NAO_CONTABIL = BASE_DIR / "nao_faz_setor" / "NAO FAZ CONTABIL.txt"

# ─────────────────────────────────────────────
# PASTAS DE RELATÓRIO
# ─────────────────────────────────────────────
RELATORIO_FISCAL   = BASE_DIR / "01_FISCAL"   / "relatorios"
RELATORIO_CONTABIL = BASE_DIR / "02_CONTABIL" / "relatorios"
RELATORIO_DP       = BASE_DIR / "03_DP"       / "relatorios"
RELATORIO_MASTER   = BASE_DIR / "04_MASTER"   / "relatorios"

for _d in [RELATORIO_FISCAL, RELATORIO_CONTABIL, RELATORIO_DP, RELATORIO_MASTER]:
    _d.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# HELPERS DE DATA
# ─────────────────────────────────────────────

def datas_mes(mes: int, ano: int) -> tuple[str, str]:
    """Retorna (DATA_INICIO, DATA_FIM) no formato 'YYYY-MM-DD'."""
    ultimo_dia = monthrange(ano, mes)[1]
    inicio = date(ano, mes, 1).strftime("%Y-%m-%d")
    fim    = date(ano, mes, ultimo_dia).strftime("%Y-%m-%d")
    return inicio, fim


def aba_excel(mes: int, ano: int) -> str:
    """Retorna o nome da aba no padrão 'MM.AAAA'."""
    return f"{str(mes).zfill(2)}.{ano}"


def mes_anterior(mes: int, ano: int) -> tuple[int, int]:
    """Retorna (mes, ano) do mês anterior."""
    d = date(ano, mes, 1) - timedelta(days=1)
    return d.month, d.year

# ─────────────────────────────────────────────
# ARGPARSE PADRÃO  (reutilizado por todos os scripts)
# ─────────────────────────────────────────────

def parse_args(descricao: str = "DMF Automação") -> argparse.Namespace:
    hoje = date.today()
    parser = argparse.ArgumentParser(description=descricao)
    parser.add_argument("-m", "--mes", type=int, default=hoje.month,
                        help="Mês de apuração (1-12). Padrão: mês atual.")
    parser.add_argument("-y", "--ano", type=int, default=hoje.year,
                        help="Ano de apuração. Padrão: ano atual.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Executa sem gravar na planilha (apenas leitura e log).")
    parser.add_argument("--verbose", action="store_true",
                        help="Log detalhado no terminal.")
    return parser.parse_args()


# ─────────────────────────────────────────────
# OBJETO DE CONFIGURAÇÃO (conveniente p/ importar)
# ─────────────────────────────────────────────
class _Config:
    # ODBC
    odbc_conn   = ODBC_CONN_STRING
    # Logs de módulo
    sist_fiscal = SIST_LOG_FISCAL
    adicional_fiscal = ADICIONAL_FISCAL
    # Planilhas
    master      = PLANILHA_MASTER
    contabil    = PLANILHA_CONTABIL
    # Exceções
    dp_nao      = EXCECAO_DP_NAO
    nao_contabil= EXCECAO_NAO_CONTABIL
    # Relatórios
    rel_fiscal  = RELATORIO_FISCAL
    rel_contabil= RELATORIO_CONTABIL
    rel_dp      = RELATORIO_DP
    rel_master  = RELATORIO_MASTER
    # Helpers
    datas_mes   = staticmethod(datas_mes)
    aba_excel   = staticmethod(aba_excel)
    mes_anterior= staticmethod(mes_anterior)
    carol_path  = staticmethod(carol_path)
    parse_args  = staticmethod(parse_args)

cfg = _Config()
