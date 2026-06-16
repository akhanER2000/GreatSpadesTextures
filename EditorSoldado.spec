# -*- mode: python ; coding: utf-8 -*-
# Empaqueta el Editor del Soldado en un único .exe (doble clic, sin consola).
from PyInstaller.utils.hooks import collect_all

datas = [
    ('app/index.html', '.'),
    ('app/app.js', '.'),
    ('app/styles.css', '.'),
    ('app/vendor', 'vendor'),
    ('app/assets', 'assets'),
]
binaries = []
hiddenimports = ['engine', 'numpy', 'PIL', 'PIL.Image']

# pywebview y su backend (EdgeChromium / pythonnet)
for pkg in ['webview', 'clr_loader']:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ['app/main.py'],
    pathex=['app'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EditorSoldado',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon='app/app.ico',
)
