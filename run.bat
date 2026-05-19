@echo off
REM ============================================================
REM  DMF Engine - launcher
REM
REM  O driver ODBC do Sybase (SQL Anywhere) usado pelo Dominio
REM  e 32-bit. Por isso o aplicativo PRECISA rodar com Python
REM  32-bit, caso contrario a conexao ODBC falha com IM014
REM  ("incompatibilidade de arquiteturas entre o Driver e o
REM  Aplicativo").
REM
REM  Esse .bat usa o Python launcher do Windows ("py") para
REM  forcar a variante 32-bit (-3-32).
REM ============================================================

cd /d %~dp0

py -3-32 --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERRO: Python 32-bit nao encontrado no launcher 'py'.
    echo  Instale o Python 32-bit em:
    echo    https://www.python.org/downloads/windows/
    echo  e marque a opcao "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)

py -3-32 dmf_engine\main.py
if errorlevel 1 pause
7