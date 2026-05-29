@echo off
REM ============================================================
REM  Central DMF - launcher
REM  Usa py -3-32 enquanto houver dependencias residuais de engine/
REM  (ODBC Sybase, lock_master, excel_parser).
REM  Migrar para py -3-64 apos limpeza das dependencias (ver ROADMAP sec 3).
REM ============================================================

cd /d %~dp0
py -3-32 dmf_engine\main.py
if errorlevel 1 pause
