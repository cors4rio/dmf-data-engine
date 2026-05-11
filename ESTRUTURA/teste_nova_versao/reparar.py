"""
04_MASTER/reparar.py — Recalibrador de Totais e Subtotais da Master
DMF Automação

Executa após qualquer integração para garantir que:
  - Coluna R = =O+P+Q em todas as linhas com dados
  - Subtotais da linha 7 (O, P, Q, R) cobrem até ws.max_row
  - Formato [h]:mm:ss em todas as células de tempo

Também escaneia e corrige células com valores fora do limite de data
do Excel (prevenção contra "fórmulas radioativas").

Uso:
    python 04_MASTER/reparar.py --mes 03 --ano 2026
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
logger = logging.getLogger("dmf.master.reparar")

# Limite máximo de valor serial de data no Excel (~9999-12-31)
EXCEL_DATE_MAX = 2958465.0


def reparar_totais(mes: int, ano: int, *, dry_run: bool = False) -> dict:
    """
    Recalcula fórmulas R e subtotais da linha 7 para todas as colunas de tempo.
    Também sanitiza células com valores absurdos.
    """
    if not cfg.master:
        raise FileNotFoundError("Planilha Master não encontrada.")

    wb  = xl.abrir_planilha(cfg.master)
    aba = cfg.aba_excel(mes, ano)

    if aba not in wb.sheetnames:
        raise ValueError(f"Aba '{aba}' não encontrada na Master.")

    ws = wb[aba]

    stats = {
        "formulas_r_atualizadas": 0,
        "celulas_sanitizadas": 0,
        "subtotais_atualizados": 0,
    }

    COLUNAS_TEMPO = [xl.COL_MES_ANT_FISC, xl.COL_FISCAL, xl.COL_CONTABIL, xl.COL_DP]

    for row in ws.iter_rows(min_row=xl.LINHA_INICIO_DADOS):
        n_linha = row[0].row

        # ── Sanitizar células com valores absurdos (problema C do Troubleshooting) ──
        for col in COLUNAS_TEMPO:
            cell = ws.cell(row=n_linha, column=col)
            if isinstance(cell.value, (int, float)):
                if cell.value > EXCEL_DATE_MAX or cell.value < 0:
                    logger.warning(
                        "⚠️  Valor absurdo na linha %d col %d: %s → zerado.",
                        n_linha, col, cell.value
                    )
                    if not dry_run:
                        cell.value = 0
                        cell.number_format = "[h]:mm:ss"
                    stats["celulas_sanitizadas"] += 1

            # Garantir formato correto se o valor é numérico de tempo
            if isinstance(cell.value, (int, float)) and 0 <= cell.value <= EXCEL_DATE_MAX:
                if not dry_run:
                    cell.number_format = "[h]:mm:ss"

        # ── Reescrever fórmula =O+P+Q na coluna R ──
        if not dry_run:
            xl.escrever_formula_total(ws, n_linha)
        stats["formulas_r_atualizadas"] += 1

    # ── Atualizar SUBTOTAIs da linha 7 (dinâmico — ws.max_row) ──
    for col in COLUNAS_TEMPO + [xl.COL_TOTAL]:
        if not dry_run:
            xl.atualizar_subtotal(ws, col)
        stats["subtotais_atualizados"] += 1

    if not dry_run:
        xl.salvar_planilha(wb, cfg.master)

    logger.info(
        "✅ Reparação | Fórmulas R: %d | Sanitizações: %d | Subtotais: %d",
        stats["formulas_r_atualizadas"],
        stats["celulas_sanitizadas"],
        stats["subtotais_atualizados"],
    )
    return stats


def gerar_relatorio(mes: int, ano: int, stats: dict) -> Path:
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    aba = cfg.aba_excel(mes, ano)
    nome = cfg.rel_master / f"relatorio_reparacao_{aba.replace('.', '_')}.md"

    conteudo = f"""# Relatório — Reparação de Totais e Subtotais
**Mês:** {aba} | **Executado em:** {ts}

## Ações Executadas

| Ação | Qtd |
|---|---|
| Fórmulas R (=O+P+Q) reescritas | {stats['formulas_r_atualizadas']} |
| Células com valor absurdo sanitizadas | {stats['celulas_sanitizadas']} |
| Subtotais linha 7 atualizados | {stats['subtotais_atualizados']} |

## Regras Aplicadas

- Fórmula `=O{{linha}}+P{{linha}}+Q{{linha}}` injetada em cada linha
- SUBTOTAL calculado dinamicamente até `max_row` da planilha
- Valores seriais fora do range `[0, 2958465]` zeraram (proteção contra overflow)
- Formato `[h]:mm:ss` garantido em todas as células de tempo

---
*Gerado automaticamente por 04_MASTER/reparar.py*
"""
    nome.write_text(conteudo, encoding="utf-8")
    return nome


if __name__ == "__main__":
    args = cfg.parse_args("DMF — Reparação de Totais")
    stats = reparar_totais(args.mes, args.ano, dry_run=args.dry_run)
    gerar_relatorio(args.mes, args.ano, stats)
