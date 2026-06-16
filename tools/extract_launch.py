# -*- coding: utf-8 -*-
"""Abre _extract.html en una ventana WebView2 (pywebview) para extraer la
geometría del modelo y POSTearla al geom_server (mismo origen, puerto 8971).
Se cierra solo a los ~12 s."""
import threading, time
import webview


def autoclose(window):
    time.sleep(12)
    try:
        window.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    w = webview.create_window("Extrayendo geometría…",
                              url="http://127.0.0.1:8971/_extract.html",
                              width=640, height=520)
    threading.Thread(target=autoclose, args=(w,), daemon=True).start()
    webview.start()
