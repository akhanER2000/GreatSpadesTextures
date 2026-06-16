# -*- coding: utf-8 -*-
"""Abre _meshviz.html (mallas coloreadas) en WebView2. Uso: viz_launch.py [angulo]."""
import sys, threading, time
import webview

angle = sys.argv[1] if len(sys.argv) > 1 else "0"
secs = int(sys.argv[2]) if len(sys.argv) > 2 else 30


def autoclose(w):
    time.sleep(secs)
    try: w.destroy()
    except Exception: pass


if __name__ == "__main__":
    w = webview.create_window("Mallas", url=f"http://127.0.0.1:8971/_meshviz.html?a={angle}",
                              width=900, height=820, background_color="#23272f")
    threading.Thread(target=autoclose, args=(w,), daemon=True).start()
    webview.start()
