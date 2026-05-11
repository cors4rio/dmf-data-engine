"""
03_DP/processar.py — Departamento Pessoal (Folha de Pagamento)
DMF Automação

Preenche a coluna Q (Horário Pessoal) na Planilha Master.
Fonte primária: bethadba.foempregados + forescisoes
Fallback:       Planilha Carol (Controle de Empregados MM.xls)
Exceções:       nao_faz_setor/DP NAO.txt

Fórmula de horas:
    total > 0  → (total × 0.33) + 1.5  (em horas)
    total = 0  → 00:05:00  (mínimo obrigatório)
    consultoria → 1:30 exato

Uso:
    python 03_DP/processar.py --mes 03 --ano 2026
    python 03_DP/processar.py --mes 03 --ano 2026 --dry-run
"""

import sys
import re
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
logger = logging.getLogger("dmf.dp")

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
HORAS_MINIMO_FRAC   = 5 / 60 / 24       # 00:05:00 em fração de dia
HORAS_OVERHEAD      = 1.5 / 24.0        # 1:30h em fração de dia
FATOR_POR_EMPREGADO = 0.33 / 24.0       # 0.33h por empregado em fração de dia
HORAS_CONSULTORIA   = 1.5 / 24.0        # 1:30h exato para consultoria

# ─────────────────────────────────────────────
# SQL
# ─────────────────────────────────────────────
SQL_EMPREGADOS = """
SELECT
    e.codi_emp                                                AS Codigo_Cliente,
    SUM(CASE WHEN e.vinculo = 1  THEN 1 ELSE 0 END)          AS Qtd_Funcionarios,
    SUM(CASE WHEN e.vinculo = 6  THEN 1 ELSE 0 END)          AS Qtd_Estagiarios,
    SUM(CASE WHEN e.vinculo = 11 THEN 1 ELSE 0 END)          AS Qtd_Contribuintes,
    SUM(CASE WHEN e.vinculo IN (1,6,11) THEN 1 ELSE 0 END)   AS Total_Para_Formula
FROM bethadba.foempregados e
LEFT JOIN bethadba.forescisoes r
    ON r.codi_emp     = e.codi_emp
   AND r.i_empregados = e.i_empregados
   AND r.demissao     < ?
WHERE e.admissao <= ?
  AND r.i_empregados IS NULL
GROUP BY e.codi_emp
ORDER BY e.codi_emp
"""


# ─────────────────────────────────────────────
# FÓRMULA DE HORAS
# ─────────────────────────────────────────────

def calcular_horas_dp(total: int) -> float:
    """
    Retorna fração de dia do Excel para as horas de DP.
    total > 0 → (total × 0.33) + 1.5 horas
    total = 0 → 5 minutos (mínimo obrigatório)
    """
    if total > 0:
        horas = (total * 0.33) + 1.5
        return horas / 24.0
    return HORAS_MINIMO_FRAC


def calcular_horas_contribuinte_unico() -> float:
    """1 contribuinte, 0 funcionários, 0 estagiários → 1:10:00"""
    return (1 + 10/60) / 24.0


# ─────────────────────────────────────────────
# EXCEÇÕES — DP NÃO
# ─────────────────────────────────────────────

def carregar_excecoes_dp() -> tuple[set[str], dict[str, float], set[str]]:
    """
    Lê o arquivo DP NAO.txt e retorna:
    - dp_nao_codes: set de códigos que recebem "DP NÃO"
    - consultoria:  dict {codigo → horas_frac_dia} para consultorias
    - dp_nao_names: set de nomes (upper) sem código
    """
    dp_nao_codes: set[str] = set()
    consultoria:  dict[str, float] = {}
    dp_nao_names: set[str] = set()

    path = cfg.dp_nao
    if not path or not Path(path).exists():
        logger.warning("Arquivo DP NAO.txt não encontrado: %s", path)
        return dp_nao_codes, consultoria, dp_nao_names

    for linha in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue

        # Extrair código (pode ser separado por tab, ; ou espaço)
        match_cod = re.match(r"^(\d+)[\t;]?\s*(.*)", linha)
        nome_raw  = ""

        if match_cod:
            cod_str  = match_cod.group(1)
            nome_raw = match_cod.group(2)
        else:
            cod_str  = None
            nome_raw = linha

        # Verificar se é consultoria (padrão: "FAZ CONSULTORIA, LANCAR APENAS 1:30")
        match_consult = re.search(r"LANCAR APENAS\s+(\d+):(\d+)", nome_raw.upper())
        if match_consult:
            h = int(match_consult.group(1))
            m = int(match_consult.group(2))
            horas_frac = (h + m / 60) / 24.0
            if cod_str:
                consultoria[cod_str] = horas_frac
        else:
            if cod_str:
                dp_nao_codes.add(cod_str)
            elif nome_raw and "SISTEMA PRÓPRIO" not in nome_raw.upper():
                dp_nao_names.add(nome_raw.strip().upper())

    logger.info("DP NAO carregado | Códigos: %d | Consultorias: %d | Nomes: %d",
                len(dp_nao_codes), len(consultoria), len(dp_nao_names))
    return dp_nao_codes, consultoria, dp_nao_names


# ─────────────────────────────────────────────
# FALLBACK — PLANILHA CAROL
# ─────────────────────────────────────────────

def carregar_carol(mes: int, ano: int) -> dict[str, int]:
    """
    Lê a planilha Carol como fallback.
    Retorna {codi_emp_str → total_ativos}.
    Colunas relevantes (0-indexed): 0=código, 7,9,11,13,15,17,19,21,23=categorias
    """
    try:
        import xlrd
    except ImportError:
        logger.warning("xlrd não instalado. Fallback Carol indisponível.")
        return {}

    path = cfg.carol_path(mes, ano)
    if not path:
        logger.warning("Planilha Carol não encontrada para %02d/%d.", mes, ano)
        return {}

    try:
        wb   = xlrd.open_workbook(str(path))
        ws   = wb.sheet_by_index(0)
        resultado: dict[str, int] = {}
        COLS_ATIVOS = [7, 9, 11, 13, 15, 17, 19, 21, 23]

        for i in range(2, ws.nrows):  # Pula 2 linhas de header
            cod_raw = ws.cell_value(i, 0)
            cod     = xl.normalizar_codigo(cod_raw)
            if not cod:
                continue
            total = sum(
                int(ws.cell_value(i, c) or 0)
                for c in COLS_ATIVOS
                if c < ws.ncols
            )
            resultado[cod] = total

        logger.info("Carol (fallback): %d empresas carregadas.", len(resultado))
        return resultado
    except Exception as exc:
        logger.error("Erro ao ler planilha Carol: %s", exc)
        return {}


# ─────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────

def processar_dp(mes: int, ano: int, *, dry_run: bool = False) -> dict:
    """
    Pipeline completo do setor de DP.
    1. Extrai empregados do Domínio
    2. Fallback Carol se necessário
    3. Aplica fórmula + exceções
    4. Preenche coluna Q da Master
    """
    if not cfg.master:
        raise FileNotFoundError("Planilha Master não encontrada.")

    inicio, fim = cfg.datas_mes(mes, ano)

    # ── 1. Dados do Domínio ──
    logger.info("Extraindo empregados do Domínio: %s → %s", inicio, fim)
    rows = executar_query(SQL_EMPREGADOS, params=(inicio, fim))
    dict_dominio: dict[str, int] = {
        xl.normalizar_codigo(r["Codigo_Cliente"]): int(r["Total_Para_Formula"] or 0)
        for r in rows
        if xl.normalizar_codigo(r["Codigo_Cliente"])
    }
    logger.info("Empregados Domínio: %d empresas com dados.", len(dict_dominio))

    # ── 2. Fallback Carol (complemento, não substituição) ──
    dict_carol = carregar_carol(mes, ano)

    # ── 3. Exceções ──
    dp_nao_codes, consultoria, dp_nao_names = carregar_excecoes_dp()

    # ── 4. Abrir planilha ──
    wb  = xl.abrir_planilha(cfg.master)
    aba = cfg.aba_excel(mes, ano)

    if aba not in wb.sheetnames:
        raise ValueError(f"Aba '{aba}' não encontrada na Master.")

    ws = wb[aba]
    por_codigo, por_cnpj = xl.mapear_linhas_master(ws)

    stats = {
        "preenchidos": 0,
        "dp_nao": 0,
        "consultoria": 0,
        "minimo": 0,
        "zerados": 0,
        "nao_encontrados": 0,
    }

    # ── 5. Percorrer TODAS as linhas ──
    for row in ws.iter_rows(min_row=xl.LINHA_INICIO_DADOS):
        n_linha = row[0].row

        cod_raw  = row[xl.COL_COD_DOMINIO - 1].value
        nome_raw = row[xl.COL_NOME_FANTASIA - 1].value

        cod = xl.normalizar_codigo(cod_raw)

        # Verificar exceção DP NÃO (por código)
        if cod and cod in dp_nao_codes:
            if not dry_run:
                ws.cell(row=n_linha, column=xl.COL_DP).value = "DP NÃO"
                xl.escrever_formula_total(ws, n_linha)
            stats["dp_nao"] += 1
            continue

        # Verificar consultoria (por código)
        if cod and cod in consultoria:
            valor_frac = consultoria[cod]
            if not dry_run:
                xl.escrever_tempo(ws, n_linha, xl.COL_DP, valor_frac)
                xl.escrever_formula_total(ws, n_linha)
            stats["consultoria"] += 1
            continue

        # Verificar DP NÃO por nome
        nome_upper = str(nome_raw or "").upper().strip()
        if nome_upper in dp_nao_names:
            if not dry_run:
                ws.cell(row=n_linha, column=xl.COL_DP).value = "DP NÃO"
                xl.escrever_formula_total(ws, n_linha)
            stats["dp_nao"] += 1
            continue

        if not cod:
            stats["nao_encontrados"] += 1
            continue

        # Buscar total de empregados (Domínio primeiro, Carol como fallback)
        total = dict_dominio.get(cod)
        if total is None and cod in dict_carol:
            total = dict_carol[cod]
            logger.debug("Fallback Carol usado para cod=%s", cod)

        if total is None:
            # Empresa não tem folha no Domínio → zerar ghost
            if not dry_run:
                xl.escrever_zero(ws, n_linha, xl.COL_DP)
                xl.escrever_formula_total(ws, n_linha)
            stats["zerados"] += 1
            continue

        horas_frac = calcular_horas_dp(total)

        if not dry_run:
            xl.escrever_tempo(ws, n_linha, xl.COL_DP, horas_frac)
            xl.escrever_formula_total(ws, n_linha)

        if total == 0:
            stats["minimo"] += 1
        else:
            stats["preenchidos"] += 1

        if dry_run:
            logger.info("  [DRY-RUN] Linha %d | cod=%s | total=%d | horas=%.4f",
                        n_linha, cod, total, horas_frac)

    if not dry_run:
        xl.atualizar_subtotal(ws, xl.COL_DP)
        xl.salvar_planilha(wb, cfg.master)

    logger.info(
        "✅ DP | Preenchidos: %d | Mínimos: %d | DP NÃO: %d | "
        "Consultoria: %d | Zerados: %d | Não encontrados: %d",
        stats["preenchidos"], stats["minimo"], stats["dp_nao"],
        stats["consultoria"], stats["zerados"], stats["nao_encontrados"]
    )
    return stats


# ─────────────────────────────────────────────
# RELATÓRIO
# ─────────────────────────────────────────────

def gerar_relatorio(mes: int, ano: int, stats: dict) -> Path:
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    aba = cfg.aba_excel(mes, ano)
    nome = cfg.rel_dp / f"relatorio_dp_{aba.replace('.', '_')}.md"

    conteudo = f"""# Relatório de Execução — Departamento Pessoal (DP)
**Mês de Apuração:** {aba}
**Executado em:** {ts}

## Resumo

| Métrica | Valor |
|---|---|
| Empresas com horas calculadas | {stats['preenchidos']} |
| Empresas com mínimo (5 min) | {stats['minimo']} |
| Empresas "DP NÃO" | {stats['dp_nao']} |
| Empresas consultoria (1:30) | {stats['consultoria']} |
| Linhas zeradas (ghost eliminado) | {stats['zerados']} |
| Sem código Domínio | {stats['nao_encontrados']} |

## Fórmula Aplicada

```
total > 0 → horas = (total × 0,33) + 1,5h
total = 0 → horas = 00:05:00 (mínimo obrigatório)
consultoria → horas = 01:30:00 (fixo)
```

## Fontes

- **Primária:** `bethadba.foempregados` + `bethadba.forescisoes`
  - `vinculo IN (1=Funcionário, 6=Estagiário, 11=Contribuinte)`
- **Fallback:** Planilha Carol `Controle de Empregados {str(mes).zfill(2)}(CAROL).xls`
- **Exceções:** `nao_faz_setor/DP NAO.txt`

---
*Gerado automaticamente por 03_DP/processar.py*
"""
    nome.write_text(conteudo, encoding="utf-8")
    logger.info("📄 Relatório: %s", nome)
    return nome


# ─────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    args = cfg.parse_args("DMF — Departamento Pessoal")

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not testar_conexao():
        logger.error("Conexão ODBC falhou. Abortando.")
        sys.exit(1)

    stats = processar_dp(args.mes, args.ano, dry_run=args.dry_run)
    gerar_relatorio(args.mes, args.ano, stats)
