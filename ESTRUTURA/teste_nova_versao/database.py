"""
database.py — Conexão ODBC e Execução de SQL
DMF Automação | _ENGINE

Uso:
    from _ENGINE.database import executar_query, testar_conexao

Nota sobre arquitetura:
    O driver SQL Anywhere (Sybase) geralmente é 32-bit.
    Se houver erro IM014 (32/64-bit mismatch), use um wrapper de processo
    separado ou a variável ODBC_FORCE_32BIT=1 no .env.
"""

import os
import logging
from typing import Any

logger = logging.getLogger("dmf.database")

# ─────────────────────────────────────────────
# Importação condicional do driver ODBC
# ─────────────────────────────────────────────
try:
    import pyodbc
    _DRIVER = "pyodbc"
except ImportError:
    try:
        import pypyodbc as pyodbc   # type: ignore
        _DRIVER = "pypyodbc"
    except ImportError:
        pyodbc = None               # type: ignore
        _DRIVER = None
        logger.warning("Nenhum driver ODBC encontrado (pyodbc / pypyodbc). "
                       "Instale com: pip install pyodbc")


def _get_conn_string() -> str:
    from _ENGINE.config import ODBC_CONN_STRING
    return ODBC_CONN_STRING


def testar_conexao() -> bool:
    """Testa a conexão ODBC e retorna True se bem-sucedida."""
    if pyodbc is None:
        logger.error("pyodbc não instalado.")
        return False
    try:
        conn = pyodbc.connect(_get_conn_string(), timeout=10)
        conn.close()
        logger.info("✅ Conexão ODBC OK (%s).", _DRIVER)
        return True
    except Exception as exc:
        logger.error("❌ Falha na conexão ODBC: %s", exc)
        return False


def executar_query(
    sql: str,
    params: tuple = (),
    *,
    como_dict: bool = True,
) -> list[dict[str, Any]] | list[tuple]:
    """
    Executa uma query SELECT no Domínio e retorna os resultados.

    Args:
        sql:       Query SQL parametrizada.
        params:    Tupla de parâmetros para substituição segura.
        como_dict: Se True (padrão), retorna lista de dicts {col: valor}.
                   Se False, retorna lista de tuplas.

    Returns:
        Lista de registros. Lista vazia se não houver resultados.

    Raises:
        RuntimeError: Se pyodbc não estiver instalado ou a conexão falhar.
    """
    if pyodbc is None:
        raise RuntimeError("pyodbc não está instalado.")

    conn = None
    try:
        conn = pyodbc.connect(_get_conn_string(), timeout=30)
        cursor = conn.cursor()

        # Log da query (mascara senhas em caso de debug)
        logger.debug("Executando SQL:\n%s\nParâmetros: %s", sql, params)

        cursor.execute(sql, params)

        if como_dict:
            colunas = [col[0] for col in cursor.description]
            rows = [dict(zip(colunas, row)) for row in cursor.fetchall()]
        else:
            rows = cursor.fetchall()

        logger.debug("Retornou %d linhas.", len(rows))
        return rows

    except pyodbc.Error as exc:
        logger.error("Erro ODBC ao executar query: %s\nSQL: %s", exc, sql[:200])
        raise
    finally:
        if conn:
            conn.close()


def executar_queries_em_lote(
    queries: list[tuple[str, tuple]],
) -> list[list[dict]]:
    """
    Executa múltiplas queries em uma única conexão (mais eficiente).

    Args:
        queries: Lista de tuplas (sql, params).

    Returns:
        Lista de resultados (uma lista de dicts por query).
    """
    if pyodbc is None:
        raise RuntimeError("pyodbc não está instalado.")

    resultados = []
    conn = None
    try:
        conn = pyodbc.connect(_get_conn_string(), timeout=30)
        cursor = conn.cursor()

        for sql, params in queries:
            cursor.execute(sql, params)
            colunas = [col[0] for col in cursor.description]
            rows = [dict(zip(colunas, row)) for row in cursor.fetchall()]
            resultados.append(rows)
            logger.debug("Query retornou %d linhas.", len(rows))

        return resultados
    except pyodbc.Error as exc:
        logger.error("Erro ODBC em lote: %s", exc)
        raise
    finally:
        if conn:
            conn.close()
