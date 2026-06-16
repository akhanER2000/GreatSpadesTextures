# -*- coding: utf-8 -*-
"""
Editor del Soldado — app de escritorio (GreatSpades)

Abre una ventana nativa con el visor 3D (three.js) y el panel de recoloreado.
Sirve los archivos por HTTP local (para que funcionen los módulos ES y WebGL)
y expone a JavaScript la función de EXPORTAR la textura a 8192² (motor Python).
"""
import os
import sys
import threading
import http.server
import socketserver

# 'engine' en el mismo directorio; import a nivel de módulo para que PyInstaller
# recoja también numpy y Pillow al empaquetar.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine


def base_dir():
    """Carpeta con index.html / assets / vendor (soporta PyInstaller)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def output_dir():
    """Carpeta 'Variaciones' junto al ejecutable (o en la raíz del proyecto)."""
    if getattr(sys, "frozen", False):
        root = os.path.dirname(sys.executable)
    else:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(root, "Variaciones")
    os.makedirs(d, exist_ok=True)
    return d


BASE = base_dir()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=BASE, **k)

    def log_message(self, *a):
        pass  # silencioso


def start_server():
    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return port


class Api:
    """Funciones invocables desde JavaScript (window.pywebview.api.*)."""

    def export_texture(self, colors):
        try:
            path = engine.recolor_multi(colors, output_dir())
            return path
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise RuntimeError(str(e))

    def output_folder(self):
        return output_dir()


def main():
    # asegurar que 'engine' sea importable al ejecutar desde fuente
    sys.path.insert(0, BASE)
    port = start_server()
    import webview
    api = Api()
    webview.create_window(
        "Editor del Soldado — GreatSpades",
        url=f"http://127.0.0.1:{port}/index.html",
        js_api=api,
        width=1240, height=840, min_size=(960, 640),
        background_color="#1c1f25",
    )
    webview.start()


if __name__ == "__main__":
    main()
