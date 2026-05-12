"""
automacao.py — Orquestrador Principal
DMF Automação

Executa o pipeline completo na ordem correta:
  1. Fiscal    → col O da Master
  2. Contábil  → cols F, O, I da planilha HORAS CONTABEIS
  3. DP        → col Q da Master
  4. Integrar  → col P da Master (Contábil → Master)
  5. Reparar   → subtotais e fórmulas R

Pode-se executar módulos individuais com --setor.

Uso:
    python automacao.py --mes 03 --ano 2026
    python automacao.py --mes 03 --ano 2026 --setor fiscal
    python automacao.py --mes 03 --ano 2026 --dry-run
    python automacao.py --mes 03 --ano 2026 --setor dp --verbose
"""

import sys
import logging
import argparse
from datetime import date, datetime
from pathlib import Path

# Garante que _ENGINE e demais módulos sejam encontrados
sys.path.insert(0, str(Path(__file__).parent))

from _ENGINE.config import cfg
from _ENGINE.database import testar_conexao

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("dmf.automacao")

SETORES_DISPONIVEIS = ["fiscal", "contabil", "dp", "integrar", "reparar", "todos"]


def parse_args() -> argparse.Namespace:
    hoje = date.today()
    p = argparse.ArgumentParser(
        description="DMF Automação — Orquestrador Principal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python automacao.py --mes 03 --ano 2026
  python automacao.py --mes 03 --ano 2026 --setor fiscal --dry-run
  python automacao.py --mes 03 --ano 2026 --setor dp --verbose
        """
    )
    p.add_argument("-m", "--mes",   type=int, default=hoje.month)
    p.add_argument("-y", "--ano",   type=int, default=hoje.year)
    p.add_argument(
        "-s", "--setor",
        choices=SETORES_DISPONIVEIS,
        default="todos",
        help="Módulo a executar (padrão: todos).",
    )
    p.add_argument("--dry-run",  action="store_true")
    p.add_argument("--verbose",  action="store_true")
    p.add_argument("--skip-conn-check", action="store_true",
                   help="Pular verificação de conexão ODBC.")
    return p.parse_args()


def _separator(titulo: str) -> None:
    logger.info("─" * 60)
    logger.info("▶  %s", titulo)
    logger.info("─" * 60)


def executar(args: argparse.Namespace) -> None:
    inicio = datetime.now()
    aba    = cfg.aba_excel(args.mes, args.ano)

    logger.info("=" * 60)
    logger.info("DMF AUTOMAÇÃO — Mês: %s | Setor: %s | Dry-run: %s",
                aba, args.setor, args.dry_run)
    logger.info("=" * 60)

    if not args.skip_conn_check:
        if not testar_conexao():
            logger.error("Conexão ODBC falhou. Use --skip-conn-check para ignorar.")
            sys.exit(1)

    setor = args.setor
    kw    = dict(dry_run=args.dry_run)

    # ── FISCAL ──────────────────────────────────────────
    if setor in ("fiscal", "todos"):
        _separator("1/5 — FISCAL (col O)")
        from _FISCAL.processar import preencher_fiscal, gerar_relatorio as rel_fiscal
        stats = preencher_fiscal(args.mes, args.ano, **kw)
        rel_fiscal(args.mes, args.ano, stats)

    # ── CONTÁBIL ─────────────────────────────────────────
    if setor in ("contabil", "todos"):
        _separator("2/5 — CONTÁBIL (cols F, O, I)")
        from _02_CONTABIL.processar import processar_contabil, gerar_relatorio as rel_cont
        resultado = processar_contabil(args.mes, args.ano, **kw)
        rel_cont(args.mes, args.ano, resultado)

    # ── DP ───────────────────────────────────────────────
    if setor in ("dp", "todos"):
        _separator("3/5 — DP (col Q)")
        from _03_DP.processar import processar_dp, gerar_relatorio as rel_dp
        stats = processar_dp(args.mes, args.ano, **kw)
        rel_dp(args.mes, args.ano, stats)

    # ── INTEGRAR Contábil → Master ────────────────────────
    if setor in ("integrar", "todos"):
        _separator("4/5 — INTEGRAR Contábil → Master (col P)")
        from _04_MASTER.integrar import integrar_contabil, gerar_relatorio as rel_int
        stats = integrar_contabil(args.mes, args.ano, **kw)
        rel_int(args.mes, args.ano, stats)

    # ── REPARAR Totais ────────────────────────────────────
    if setor in ("reparar", "todos"):
        _separator("5/5 — REPARAR Totais e Subtotais")
        from _04_MASTER.reparar import reparar_totais, gerar_relatorio as rel_rep
        stats = reparar_totais(args.mes, args.ano, **kw)
        rel_rep(args.mes, args.ano, stats)

    # ── RESUMO ────────────────────────────────────────────
    elapsed = (datetime.now() - inicio).total_seconds()
    logger.info("=" * 60)
    logger.info("✅ CONCLUÍDO em %.1fs | Aba: %s | Dry-run: %s",
                elapsed, aba, args.dry_run)
    logger.info("=" * 60)


if __name__ == "__main__":
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    executar(args)
