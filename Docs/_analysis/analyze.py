"""Analisis exhaustivo del espacio de color de la textura del soldado voxel.

Objetivo: cuantificar los clusters de color para construir mascaras precisas
que separen la zona recoloreable (gris uniforme + gris casco) del resto
(oliva del chaleco, negro de guantes/botas, piel, naranja del cuello).
"""
import numpy as np
from PIL import Image
import colorsys

SRC = r"J:\Code\GreatSpadesTextures\Docs\blocky_humanoid_3d_model_basecolor.jpg"

im = Image.open(SRC).convert("RGB")
W, H = im.size
# Muestreo: cada 8 px en cada eje -> ~1M px, suficiente y rapido
arr = np.asarray(im, dtype=np.uint8)[::8, ::8, :]
flat = arr.reshape(-1, 3).astype(np.float32) / 255.0
N = flat.shape[0]
print(f"Imagen {W}x{H}, muestreada a {arr.shape[1]}x{arr.shape[0]} = {N} px")

R, G, B = flat[:, 0], flat[:, 1], flat[:, 2]
mx = flat.max(axis=1)
mn = flat.min(axis=1)
V = mx                      # value (HSV)
S = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)  # saturation
# Luminancia perceptual (Rec.709)
L = 0.2126 * R + 0.7152 * G + 0.0722 * B
# Croma simple
chroma = mx - mn

# Hue en grados
maxc = mx; minc = mn; delta = chroma
hue = np.zeros(N)
mask_d = delta > 1e-6
rc = (maxc - R) / np.where(delta == 0, 1, delta)
gc = (maxc - G) / np.where(delta == 0, 1, delta)
bc = (maxc - B) / np.where(delta == 0, 1, delta)
h = np.zeros(N)
is_r = (maxc == R)
is_g = (maxc == G) & ~is_r
is_b = (maxc == B) & ~is_r & ~is_g
h[is_r] = (bc - gc)[is_r]
h[is_g] = (2.0 + rc - bc)[is_g]
h[is_b] = (4.0 + gc - rc)[is_b]
hue = (h / 6.0) % 1.0 * 360.0
hue[~mask_d] = -1  # gris puro: sin hue

def pct(m):
    return 100.0 * m.sum() / N

print("\n=== Distribucion de saturacion ===")
for lo, hi in [(0,0.08),(0.08,0.15),(0.15,0.25),(0.25,0.4),(0.4,1.01)]:
    m = (S>=lo)&(S<hi)
    print(f"  S [{lo:.2f},{hi:.2f}): {pct(m):5.1f}%   V_medio={V[m].mean() if m.any() else 0:.2f}")

# --- Clasificacion heuristica por categorias ---
# Negro: muy oscuro
black = (V < 0.16)
# Gris recoloreable: baja saturacion, no negro, no blanco puro
gray = (S < 0.12) & (V >= 0.16) & ~black
# Piel: hue naranja-rosa, saturacion media, valor alto
skin = (~black) & (hue >= 10) & (hue <= 45) & (S >= 0.18) & (S <= 0.55) & (V > 0.45)
# Naranja cuello: hue naranja, saturacion alta
orange = (~black) & (hue >= 5) & (hue <= 35) & (S > 0.55) & (V > 0.4)
# Oliva/khaki chaleco: hue verde-amarillo, saturacion media
olive = (~black) & (hue >= 35) & (hue <= 90) & (S >= 0.15)
# Resto
classified = black | gray | skin | orange | olive
other = ~classified

print("\n=== Categorias (heuristica) ===")
for name, m in [("negro",black),("gris(recolor)",gray),("oliva",olive),
                ("piel",skin),("naranja",orange),("otro",other)]:
    if m.any():
        rgb = (flat[m].mean(axis=0)*255).astype(int)
        print(f"  {name:14s}: {pct(m):5.1f}%  RGB medio={tuple(rgb)}  V[{V[m].min():.2f}-{V[m].max():.2f}]")
    else:
        print(f"  {name:14s}: 0%")

# --- Sub-analisis del GRIS: casco vs uniforme separables por valor? ---
gv = V[gray]
print(f"\n=== Sub-distribucion del GRIS (n={gray.sum()}) ===")
print(f"  V: min={gv.min():.3f} max={gv.max():.3f} media={gv.mean():.3f} std={gv.std():.3f}")
qs = np.percentile(gv, [5,10,25,50,75,90,95])
print(f"  percentiles V [5,10,25,50,75,90,95] = {np.round(qs,3)}")
# histograma de valor del gris
hist, edges = np.histogram(gv, bins=20, range=(0.16,1.0))
print("  histograma V del gris:")
for i in range(20):
    bar = "#" * int(60*hist[i]/hist.max())
    print(f"    {edges[i]:.2f}-{edges[i+1]:.2f} {bar} {hist[i]}")

# k-means 1D sobre el valor del gris (2 clusters) para ver si hay bimodalidad
def kmeans1d(x, k=2, iters=50):
    c = np.percentile(x, np.linspace(10,90,k))
    for _ in range(iters):
        d = np.abs(x[:,None]-c[None,:])
        lab = d.argmin(1)
        newc = np.array([x[lab==j].mean() if (lab==j).any() else c[j] for j in range(k)])
        if np.allclose(newc,c): break
        c = newc
    return c, lab
c2, lab2 = kmeans1d(gv,2)
print(f"\n  k-means(2) centros de valor del gris: {np.round(np.sort(c2),3)}")
print(f"  separacion entre centros: {abs(c2[0]-c2[1]):.3f}")
print(f"  tamano clusters: {[int((lab2==j).sum()) for j in range(2)]}")
