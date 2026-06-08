@echo off
REM ============================================================
REM  Build do DMF Engine para distribuicao na rede com barra de progresso.
REM
REM  Uso:
REM     build.bat
REM
REM  Requer Python 3.x 64-bit com PyInstaller instalado.
REM ============================================================

setlocal enableextensions

REM Executa o script python que cuida de todo o processo de build
REM e mostra a barra de progresso em porcentagem no CMD.
py -3-64 build_runner.py

if errorlevel 1 (
    echo.
    echo  [ERRO] O build falhou. Verifique as mensagens acima.
    pause
    exit /b 1
)

endlocal
pause
exit /b 0
