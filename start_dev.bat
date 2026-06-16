@echo off
REM ============================================================
REM  Editor del Soldado — modo desarrollo (sin empaquetar)
REM  Ejecuta la app directamente desde el codigo fuente.
REM ============================================================
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo No existe el entorno .venv. Ejecuta construir_exe.bat una vez.
    pause
    exit /b
)
start "" ".venv\Scripts\pythonw.exe" "app\main.py"
