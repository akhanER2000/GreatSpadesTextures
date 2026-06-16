@echo off
REM ============================================================
REM  Editor del Soldado — construir el ejecutable (.exe)
REM  Crea el entorno, genera los activos y empaqueta con PyInstaller.
REM ============================================================
cd /d "%~dp0"
echo === Editor del Soldado: construccion del .exe ===

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno Python 3.12...
    py -3.12 -m venv .venv
)

echo Instalando dependencias...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
call ".venv\Scripts\python.exe" -m pip install pywebview pyinstaller pillow numpy

echo Generando activos (textura + copia del modelo)...
call ".venv\Scripts\python.exe" build_assets.py

echo Horneando regiones por geometria (casco/uniforme/chaleco/botas/guantes)...
call ".venv\Scripts\python.exe" bake_regions.py

echo Empaquetando...
call ".venv\Scripts\pyinstaller.exe" --noconfirm --clean EditorSoldado.spec

echo.
echo ============================================================
echo  Listo:  dist\EditorSoldado.exe
echo  Doble clic en ese .exe (o en start.vbs) para abrir la app.
echo ============================================================
pause
