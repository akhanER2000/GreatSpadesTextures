# -*- coding: utf-8 -*-
"""Servidor de apoyo para hornear regiones:
  - GET  : sirve la carpeta app/ (igual que http.server)
  - POST /save?name=<archivo> : guarda el cuerpo (binario) en app/assets/geom/<archivo>

Se usa una sola vez para extraer la geometría del modelo desde el navegador
(three.js carga el FBX correctamente, con sus transformaciones de mundo).
"""
import os
import http.server
import socketserver
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(ROOT, "..", "app")
GEOM = os.path.join(APP, "assets", "geom")
os.makedirs(GEOM, exist_ok=True)
PORT = 8971


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=APP, **k)

    def log_message(self, *a):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)
        qs = urllib.parse.urlparse(self.path).query
        name = urllib.parse.parse_qs(qs).get("name", ["out.bin"])[0]
        name = os.path.basename(name)  # evitar rutas
        with open(os.path.join(GEOM, name), "wb") as f:
            f.write(data)
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"ok " + str(len(data)).encode())


if __name__ == "__main__":
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"geom_server en http://127.0.0.1:{PORT}  (guarda en {GEOM})")
        httpd.serve_forever()
