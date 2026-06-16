# -*- coding: utf-8 -*-
"""Regenera las Variaciones con el motor nuevo (geometría+color, 8192²).
Cada variación recolorea uniforme+casco al mismo color (look coherente),
manteniendo chaleco, botas, guantes, cuello y piel originales."""
import os, sys, shutil, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))
import engine

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "Variaciones")
os.makedirs(OUT, exist_ok=True)

# limpiar variaciones/artefactos antiguos
for d in os.listdir(OUT):
    p = os.path.join(OUT, d)
    if os.path.isdir(p) and (d.startswith("custom_") or d.startswith("_")):
        shutil.rmtree(p, ignore_errors=True)

PALETTE = {
    "azul_marino": "#1b2f5e", "verde_bosque": "#2f4a22", "rojo_sangre": "#7a1f1f",
    "arena": "#9c8862", "gris_urbano": "#3a4048", "morado": "#3d2a55",
    "negro_tactico": "#1a1a1c", "invierno": "#cfd3d6",
}

for name, hexc in PALETTE.items():
    t = time.time()
    p = engine.recolor_multi({1: hexc, 5: hexc}, OUT, name=name)
    print(f"OK {name:14s} {hexc}  ({time.time()-t:.0f}s)")
print("Listo ->", OUT)
