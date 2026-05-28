@echo off
REM ============================================================
REM  Automacao de Horas - launcher standalone (debug / direto)
REM  REQUER Python 32-bit: driver ODBC Sybase e 32-bit.
REM  A Central DMF lanca este servico automaticamente com SSO.
REM ============================================================

cd /d %~dp0
py -3-32 services\automacao_horas\main.py
if errorlevel 1 pause
