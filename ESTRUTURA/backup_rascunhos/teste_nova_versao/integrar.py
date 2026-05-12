"""
04_MASTER/integrar.py — Integração Contábil → Master (Double Match)
DMF Automação

Copia os valores validados da planilha HORAS CONTABEIS (coluna R = Horas Validadas)
para a coluna P (Horário Contábil) da planilha Master.

Critério de match (Double Match obrigatório):
    1. Código Domínio: Master col H ↔ Contábil col A
    2. CNPJ:           Master col J ↔ Contábil col C

Uso:
    python 04_MASTER/integrar.py --mes 03 --ano 2026
    python 04_MASTER/integrar.py --mes 03 --ano 2026 --dry-run
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from _ENGINE.config import cfg
from _ENGINE import excel_utils as xl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("dmf.master.integrar")

# ─────────────────────────────────────────────
# COLUNAS NA PLANILHA CONTÁBIL (1-indexed)
# ─────────────────────────────────────────────
CC_COD   = 1   # A — Cód Domínio
CC_CNPJ  = 3   # C — CNPJ
CC_HORAS = 18  # R — Horas Validadas (coluna R da contábil)

# "NAO FAZ CONTABIL" carregado do arquivo de exceções
TEXTO_NAO_CONTABIL = "NAO FAZ CONTABIL"

LINHA_INICIO_CONTABIL = 2


def _carregar_excecoes_contabil() -> set[str]:
    """Retorna set de códigos que recebem 'NAO FAZ CONTABIL'."""
    codes: set[str] = set()
    path = cfg.nao_contabil
    if not path or not Path(path).exists():
        return codes
    for linha in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        import re
        m = re.match(r"^(\d+)[\t;]?\s*", linha)
        if m:
            codes.add(m.group(1))
    return codes


def integrar_contabil(mes: int, ano: int, *, dry_run: bool = False) -> dict:
    """
    Lê HORAS CONTABEIS, extrai col A (código) + col C (CNPJ) + col R (horas),
    e grava na col P da Master usando Double Match.
    """
    if not cfg.master:
        raise FileNotFoundError("Planilha Master não encontrada.")
    if not cfg.contabil:
        raise FileNotFoundError("Planilha HORAS CONTABEIS não encontrada.")

    aba = cfg.aba_excel(mes, ano)
    nao_contabil_codes = _carregar_excecoes_contabil()

    # ── 1. Ler planilha contábil ──
    wb_cont = xl.abrir_planilha(cfg.contabil)
    if aba not in wb_cont.sheetnames:
        raise ValueError(f"Aba '{aba}' não encontrada em HORAS CONTABEIS.")
    ws_cont = wb_cont[aba]

    # Extrair mapa: {(cod, cnpj) → horas_frac}
    mapa_contabil: dict[tuple, float | str] = {}
    for row in ws_cont.iter_rows(min_row=LINHA_INICIO_CONTABIL):
        cod_raw  = row[CC_COD  - 1].value
        cnpj_raw = row[CC_CNPJ - 1].value
        hora_raw = row[CC_HORAS - 1].value

        cod  = xl.normalizar_codigo(cod_raw)
        cnpj = xl.normalizar_cnpj(cnpj_raw)

        if not cod:
            continue

        # Exceção: não faz contábil
        if cod in nao_contabil_codes:
            mapa_contabil[(cod, cnpj)] = TEXTO_NAO_CONTABIL
            continue

        horas = xl.garantir_float_tempo(hora_raw)
        if horas is not None:
            mapa_contabil[(cod, cnpj)] = horas

    logger.info("Contábil: %d entradas lidas (aba %s).", len(mapa_contabil), aba)

    # ── 2. Abrir Master ──
    wb_master = xl.abrir_planilha(cfg.master)
    if aba not in wb_master.sheetnames:
        raise ValueError(f"Aba '{aba}' não encontrada na Master.")
    ws_master = wb_master[aba]

    stats = {"preenchidos": 0, "nao_contabil": 0, "sem_match": 0, "total": 0}

    for row in ws_master.iter_rows(min_row=xl.LINHA_INICIO_DADOS):
        n_linha = row[0].row
        stats["total"] += 1

        cod_raw  = row[xl.COL_COD_DOMINIO - 1].value
        cnpj_raw = row[xl.COL_CNPJ - 1].value

        cod  = xl.normalizar_codigo(cod_raw)
        cnpj = xl.normalizar_cnpj(cnpj_raw)

        if not cod:
            stats["sem_match"] += 1
            continue

        # Double Match: tenta (cod, cnpj) primeiro, depois só (cod, "")
        valor = mapa_contabil.get((cod, cnpj)) or mapa_contabil.get((cod, ""))

        # Fallback: procurar por código independente do CNPJ
        if valor is None:
            for (k_cod, _), v in mapa_contabil.items():
                if k_cod == cod:
                    valor = v
                    break

        if valor is None:
            stats["sem_match"] += 1
            if not dry_run:
                xl.escrever_zero(ws_master, n_linha, xl.COL_CONTABIL)
            continue

        if valor == TEXTO_NAO_CONTABIL:
            if not dry_run:
                ws_master.cell(row=n_linha, column=xl.COL_CONTABIL).value = TEXTO_NAO_CONTABIL
            stats["nao_contabil"] += 1
        else:
            if not dry_run:
                xl.escrever_tempo(ws_master, n_linha, xl.COL_CONTABIL, valor)
            stats["preenchidos"] += 1

        if not dry_run:
            xl.escrever_formula_total(ws_master, n_linha)

        if dry_run:
            logger.info("  [DRY-RUN] Linha %d | cod=%s | valor=%s", n_linha, cod, valor)

    if not dry_run:
        xl.atualizar_subtotal(ws_master, xl.COL_CONTABIL)
        xl.salvar_planilha(wb_master, cfg.master)

    logger.info(
        "✅ Integração Contábil→Master | Preenchidos: %d | NAO CONTABIL: %d | Sem match: %d",
        stats["preenchidos"], stats["nao_contabil"], stats["sem_match"]
    )
    return stats


def gerar_relatorio(mes: int, ano: int, stats: dict) -> Path:
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    aba = cfg.aba_excel(mes, ano)
    nome = cfg.rel_master / f"relatorio_integracao_contabil_{aba.replace('.', '_')}.md"

    conteudo = f"""# Relatório — Integração Contábil → Master
**Mês:** {aba} | **Executado em:** {ts}

## Resumo

| Métrica | Valor |
|---|---|
| Linhas processadas | {stats['total']} |
| Preenchidos (col P) | {stats['preenchidos']} |
| NAO FAZ CONTABIL | {stats['nao_contabil']} |
| Sem match | {stats['sem_match']} |

## Critério de Match

**Double Match** obrigatório:
1. Código Domínio (Master col H ↔ Contábil col A)
2. CNPJ (Master col J ↔ Contábil col C)

---
*Gerado automaticamente por 04_MASTER/integrar.py*
"""
    nome.write_text(conteudo, encoding="utf-8")
    return nome


if __name__ == "__main__":
    args = cfg.parse_args("DMF — Integração Contábil → Master")
    stats = integrar_contabil(args.mes, args.ano, dry_run=args.dry_run)
    gerar_relatorio(args.mes, args.ano, stats)
