# -*- coding: utf-8 -*-
"""Compone la galería final (_galeria.png) a partir del render en rejilla."""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "app", "assets", "geom", "galeria_render.png")
OUT = os.path.join(ROOT, "Variaciones", "_galeria.png")

render = Image.open(SRC).convert("RGB")
W, H = render.size  # 1600 x 820
TITLE_H = 64
canvas = Image.new("RGB", (W, H + TITLE_H), (28, 30, 36))
canvas.paste(render, (0, TITLE_H))
d = ImageDraw.Draw(canvas)


def font(sz):
    for f in [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"]:
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


# título
d.text((24, 18), "Editor del Soldado — Variaciones de color (uniforme + casco)",
       fill=(235, 237, 242), font=font(28))

# etiquetas por soldado (orden en pantalla: columnas espejadas)
ROW0 = ["Arena", "Rojo sangre", "Verde bosque", "Azul marino"]
ROW1 = ["Invierno", "Negro táctico", "Morado", "Gris urbano"]
fl = font(22)
colx = [W * (k + 0.5) / 4 for k in range(4)]
for k, name in enumerate(ROW0):
    bb = d.textbbox((0, 0), name, font=fl)
    d.text((colx[k] - (bb[2]-bb[0]) / 2, TITLE_H + H*0.46), name, fill=(225, 227, 233), font=fl)
for k, name in enumerate(ROW1):
    bb = d.textbbox((0, 0), name, font=fl)
    d.text((colx[k] - (bb[2]-bb[0]) / 2, TITLE_H + H*0.965), name, fill=(225, 227, 233), font=fl)

canvas.save(OUT)
print("OK ->", OUT, canvas.size)
