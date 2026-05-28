@echo off
REM ============================================================
REM  Central DMF - launcher
REM  Roda em Python 64-bit (padrao do sistema).
REM  Para Automacao de Horas standalone, use run_automacao_horas.bat
REM ============================================================

cd /d %~dp0
py dmf_engine\main.py
if errorlevel 1 pause
