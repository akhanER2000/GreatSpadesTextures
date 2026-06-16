@echo off
REM ============================================================
REM  Editor del Soldado — lanzador (doble clic)
REM  Abre la aplicacion empaquetada (dist\EditorSoldado.exe).
REM ============================================================
cd /d "%~dp0"
if exist "dist\EditorSoldado.exe" (
    start "" "dist\EditorSoldado.exe"
) else (
    echo No se encontro dist\EditorSoldado.exe
    echo Ejecuta primero el empaquetado:  construir_exe.bat
    pause
)
