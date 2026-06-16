#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Genera los activos que consume la app de escritorio:
  - app/assets/texture_2048.jpg : textura base reducida (visor fluido)
  - app/assets/regions_2048.png : MAPA DE REGIONES (R = id de pieza)
        id 0 = piel / otros  -> BLOQUEADO (nunca se recolorea)
        id 1 = uniforme + casco (gris)
        id 2 = chaleco (oliva)
        id 3 = botas + guantes (negro)
        id 4 = cuello (naranja)
  - app/assets/model.fbx       : copia del modelo

El mapa de regiones alinea 1:1 con la textura (mismas UV), así el shader del
visor sabe qué pieza es cada texel y aplica el color preservando la luminancia.
"""
import os, shutil, json
import numpy as np
from PIL import Image
from recolor import rgb_to_lab

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "Docs", "blocky_humanoid_3d_model_basecolor.jpg")
FBX = os.path.join(ROOT, "Docs", "VoxelSoldierSegmentationTextureBlender",
                   "tripo_convert_22d9f727-6901-4fb9-9862-efec8d03a64b.fbx")
OUT = os.path.join(ROOT, "app", "assets")
os.makedirs(OUT, exist_ok=True)

SIZE = 2048

def channels(arr):
    R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = arr.max(-1); mn = arr.min(-1); V = mx; chroma = mx - mn
    S = np.where(mx > 1e-6, chroma / np.maximum(mx, 1e-6), 0.0)
    delta = np.where(chroma < 1e-6, 1.0, chroma)
    rc = (mx - R)/delta; gc = (mx - G)/delta; bc = (mx - B)/delta
    h = np.zeros_like(V)
    is_r = mx == R; is_g = (mx == G) & ~is_r; is_b = (mx == B) & ~is_r & ~is_g
    h[is_r] = (bc - gc)[is_r]; h[is_g] = (2+rc-bc)[is_g]; h[is_b] = (4+gc-rc)[is_b]
    hue = (h/6.0) % 1.0 * 360.0
    return V, S, chroma, hue

def build_regions(arr):
    V, S, chroma, hue = channels(arr)
    black  = V < 0.14
    gray   = (chroma < 0.07) & (V >= 0.14) & (V <= 0.82)
    olive_like = (hue >= 33) & (hue <= 105) & (chroma >= 0.045)
    gray   = gray & ~olive_like
    orange = (~black) & (hue >= 5) & (hue <= 33) & (S > 0.5) & (V > 0.4)
    skin   = (~black) & (hue >= 8) & (hue <= 45) & (S >= 0.18) & (S <= 0.5) & (V > 0.5) & ~orange
    olive  = (~black) & ~gray & (hue >= 33) & (hue <= 105) & (chroma >= 0.045)

    ids = np.zeros(arr.shape[:2], dtype=np.uint8)  # 0 = piel/otros (bloqueado)
    ids[olive]  = 2
    ids[black]  = 3
    ids[orange] = 4
    ids[gray]   = 1   # el gris manda sobre solapes (uniforme/casco)
    # la piel queda como 0 explícitamente (no se toca)
    ids[skin]   = 0
    return ids

def main():
    print("Cargando textura origen...")
    im = Image.open(SRC).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
    im.save(os.path.join(OUT, "texture_2048.jpg"), quality=92)
    arr = np.asarray(im, dtype=np.float32) / 255.0

    print("Construyendo mapa de regiones...")
    ids = build_regions(arr)
    reg = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
    reg[..., 0] = ids                      # R = id de región
    reg[..., 1] = (ids * 60).astype(np.uint8)  # G = ayuda visual (debug)
    Image.fromarray(reg).save(os.path.join(OUT, "regions_2048.png"))

    tot = ids.size
    for i, n in [(0,"piel/otros"),(1,"uniforme+casco"),(2,"chaleco"),(3,"botas+guantes"),(4,"cuello")]:
        print(f"  region {i} {n:16s}: {100*(ids==i).mean():5.1f}%")

    print("Calculando brillo medio (L*) por región...")
    lab = rgb_to_lab(arr)
    L = lab[..., 0]
    meta = {"size": SIZE, "flipY": True, "regions": {}}
    names = {1: "uniforme_casco", 2: "chaleco", 3: "botas_guantes", 4: "cuello"}
    for i, key in names.items():
        m = ids == i
        meta["regions"][str(i)] = {
            "name": key,
            "meanL": float(L[m].mean()) if m.any() else 50.0,
            "pct": float(100 * m.mean()),
        }
    with open(os.path.join(OUT, "regions_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("Copiando modelo FBX...")
    shutil.copy2(FBX, os.path.join(OUT, "model.fbx"))

    print("Copiando textura 8192² (para exportación)...")
    shutil.copy2(SRC, os.path.join(OUT, "texture_8192.jpg"))

    print("OK -> activos en", OUT)

if __name__ == "__main__":
    main()
