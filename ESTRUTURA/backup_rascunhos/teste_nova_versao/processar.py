"""
01_FISCAL/processar.py — Produtividade do Setor Fiscal
DMF Automação

Preenche a coluna O (Horário Fiscal) na Planilha Master.
Fonte: bethadba.geloguser  WHERE sist_log = 5  (Módulo Escrita Fiscal)
Adicional: +80% sobre o tempo bruto (fator 1.80 — v1.2 de 2026-04-12)

Uso:
    python 01_FISCAL/processar.py --mes 03 --ano 2026
    python 01_FISCAL/processar.py --mes 03 --ano 2026 --dry-run
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from _ENGINE.config import cfg
from _ENGINE.database import executar_query, testar_conexao
from _ENGINE import excel_utils as xl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("dmf.fiscal")

# ─────────────────────────────────────────────
# SQL — validada em Jan/2026 com precisão de segundos
# ─────────────────────────────────────────────
SQL_FISCAL = """
SELECT
    l.usua_log              AS Colaborador,
    e.codi_emp              AS Codigo_Cliente,
    e.nome_emp              AS Nome_Cliente,
    SUM(
        DATEDIFF(second,
            YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tini_log,
            COALESCE(
                YMD(YEAR(l.dfim_log), MONTH(l.dfim_log), DAY(l.dfim_log)) + l.tfim_log,
                YMD(YEAR(l.data_log), MONTH(l.data_log), DAY(l.data_log)) + l.tfim_log
            )
        )
    ) AS Segundos_Brutos
FROM bethadba.geloguser l
INNER JOIN bethadba.geempre e
    ON e.codi_emp = l.codi_emp
WHERE l.sist_log = ?
  AND l.data_log >= ?
  AND l.data_log <= ?
  AND l.tfim_log IS NOT NULL
GROUP BY l.usua_log, e.codi_emp, e.nome_emp
ORDER BY e.codi_emp
"""


def extrair_fiscal(mes: int, ano: int) -> dict[str, float]:
    """
    Extrai segundos brutos de log fiscal por empresa e retorna
    dict {codi_emp_str → segundos_com_adicional}.
    """
    inicio, fim = cfg.datas_mes(mes, ano)
    logger.info("Extraindo fiscal: %s → %s", inicio, fim)

    rows = executar_query(SQL_FISCAL, params=(cfg.sist_fiscal, inicio, fim))
    logger.info("Linhas retornadas do banco: %d", len(rows))

    # Agregar por empresa (soma de todos os colaboradores)
    por_empresa: dict[str, float] = {}
    for row in rows:
        cod  = xl.normalizar_codigo(row["Codigo_Cliente"])
        secs = float(row["Segundos_Brutos"] or 0)
        if cod:
            por_empresa[cod] = por_empresa.get(cod, 0.0) + secs

    # Aplicar adicional de 80%
    resultado: dict[str, float] = {
        cod: secs * cfg.adicional_fiscal
        for cod, secs in por_empresa.items()
    }

    logger.info(
        "Empresas com tempo fiscal após adicional (×%.2f): %d",
        cfg.adicional_fiscal, len(resultado)
    )
    return resultado


def preencher_fiscal(mes: int, ano: int, *, dry_run: bool = False) -> dict:
    """
    Pipeline completo: extrai do Domínio → grava na coluna O da Master.

    Returns:
        Dicionário com estatísticas da execução para o relatório.
    """
    stats = {
        "preenchidos": 0,
        "zerados":     0,     # linhas sem tempo no banco (ghosts eliminados)
        "nao_encontrados": 0,
        "linhas_total": 0,
    }

    if not cfg.master:
        raise FileNotFoundError("Planilha Master não encontrada. Verifique config.py.")

    # 1. Extrair dados do banco
    dict_fiscal = extrair_fiscal(mes, ano)

    # 2. Abrir planilha
    wb = xl.abrir_planilha(cfg.master)
    aba = cfg.aba_excel(mes, ano)

    if aba not in wb.sheetnames:
        raise ValueError(f"Aba '{aba}' não encontrada na planilha Master.")

    ws = wb[aba]
    por_codigo, por_cnpj = xl.mapear_linhas_master(ws)

    # Detectar duplicados (alerta, não bloqueia)
    dups = xl.detectar_cnpj_duplicados(por_cnpj)
    if dups:
        logger.warning(
            "⚠️  CNPJs duplicados detectados (%d). Não serão preenchidos automaticamente.",
            len(dups)
        )

    cnpjs_dup = set()
    for linhas in dups.values():
        for l in linhas:
            cnpjs_dup.add(l)

    # 3. Percorrer TODAS as linhas da Master (não só as que têm dados)
    # [F] Isso garante zerar ghosts de meses anteriores
    for row in ws.iter_rows(min_row=xl.LINHA_INICIO_DADOS):
        n_linha = row[0].row
        stats["linhas_total"] += 1

        cod_raw  = row[xl.COL_COD_DOMINIO - 1].value
        cnpj_raw = row[xl.COL_CNPJ - 1].value

        if n_linha in cnpjs_dup:
            logger.debug("Linha %d ignorada (CNPJ duplicado).", n_linha)
            continue

        cod = xl.normalizar_codigo(cod_raw)
        if not cod:
            stats["nao_encontrados"] += 1
            continue

        segundos = dict_fiscal.get(cod)

        if dry_run:
            acao = "PREENCHER" if segundos else "ZERAR"
            logger.info("  [DRY-RUN] Linha %d | codi_emp=%s | %s (%.0f s)",
                        n_linha, cod, acao, segundos or 0)
        else:
            if segundos:
                xl.escrever_tempo(ws, n_linha, xl.COL_FISCAL, segundos)
                stats["preenchidos"] += 1
            else:
                # [F] Zerar explicitamente para matar ghosts
                xl.escrever_zero(ws, n_linha, xl.COL_FISCAL)
                stats["zerados"] += 1

            xl.escrever_formula_total(ws, n_linha)

    if not dry_run:
        # [G] Atualizar SUBTOTAL dinamicamente
        xl.atualizar_subtotal(ws, xl.COL_FISCAL)
        xl.salvar_planilha(wb, cfg.master)

    logger.info(
        "✅ Fiscal | Preenchidos: %d | Zerados: %d | Não encontrados: %d | Total linhas: %d",
        stats["preenchidos"], stats["zerados"],
        stats["nao_encontrados"], stats["linhas_total"]
    )
    return stats


# ─────────────────────────────────────────────
# RELATÓRIO
# ─────────────────────────────────────────────

def gerar_relatorio(mes: int, ano: int, stats: dict) -> Path:
    """Gera relatório .md de auditoria na pasta 01_FISCAL/relatorios/."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    aba = cfg.aba_excel(mes, ano)
    nome_arquivo = cfg.rel_fiscal / f"relatorio_fiscal_{aba.replace('.', '_')}.md"

    conteudo = f"""# Relatório de Execução — Produtividade Fiscal
**Mês de Apuração:** {aba}
**Executado em:** {ts}
**Adicional aplicado:** ×{cfg.adicional_fiscal:.2f} (+{(cfg.adicional_fiscal-1)*100:.0f}%)

## Resumo

| Métrica | Valor |
|---|---|
| Linhas totais na Master | {stats['linhas_total']} |
| Empresas preenchidas (col O) | {stats['preenchidos']} |
| Empresas zeradas (ghost eliminado) | {stats['zerados']} |
| Linhas sem código Domínio | {stats['nao_encontrados']} |

## Observações

- Fonte: `bethadba.geloguser` WHERE `sist_log = {cfg.sist_fiscal}`
- Precisão: SEGUNDOS (`DATEDIFF(second)`)
- Adicional de {(cfg.adicional_fiscal-1)*100:.0f}% aplicado sobre tempo bruto antes de gravar

---
*Gerado automaticamente por 01_FISCAL/processar.py*
"""
    nome_arquivo.write_text(conteudo, encoding="utf-8")
    logger.info("📄 Relatório: %s", nome_arquivo)
    return nome_arquivo


# ─────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    args = cfg.parse_args("DMF — Produtividade Fiscal")

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not testar_conexao():
        logger.error("Conexão ODBC falhou. Abortando.")
        sys.exit(1)

    stats = preencher_fiscal(args.mes, args.ano, dry_run=args.dry_run)
    gerar_relatorio(args.mes, args.ano, stats)
