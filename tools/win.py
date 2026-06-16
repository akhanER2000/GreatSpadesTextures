# -*- coding: utf-8 -*-
"""Abre una URL en WebView2 N segundos. Uso: win.py <url> [segundos]."""
import sys, threading, time
import webview
url = sys.argv[1]
secs = int(sys.argv[2]) if len(sys.argv) > 2 else 25
w = webview.create_window("ventana", url=url, width=900, height=820, background_color="#202229")
threading.Thread(target=lambda: (time.sleep(secs), _close(w)), daemon=True).start()
def _close(win):
    try: win.destroy()
    except Exception: pass
webview.start()
