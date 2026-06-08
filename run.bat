@echo off
REM ============================================================
REM  Central DMF - launcher
REM  64-bit: o banco Dominio conecta via DSN-less (SQL Anywhere 17),
REM  sem dependencia 32-bit. Ver docs/migracao-64bit.md.
REM ============================================================

cd /d %~dp0
py -3-64 dmf_engine\main.py
if errorlevel 1 pause
