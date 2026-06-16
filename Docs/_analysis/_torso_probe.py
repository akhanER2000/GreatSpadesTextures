# -*- coding: utf-8 -*-
import sys; sys.path.insert(0, r'J:\Code\GreatSpadesTextures')
from bake_regions import load_geom
import numpy as np
from PIL import Image

TEX = r'J:\Code\GreatSpadesTextures\app\assets\texture_2048.jpg'
img = np.asarray(Image.open(TEX).convert('RGB'), np.float32) / 255.0
H, W = img.shape[:2]
meshes, gmin, gmax = load_geom()

def rgb2hsv_chroma(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(-1); mn = rgb.min(-1); V = mx; chroma = mx - mn
    S = np.where(mx > 1e-6, chroma / np.maximum(mx, 1e-6), 0.0)
    d = np.where(chroma < 1e-6, 1.0, chroma)
    rc = (mx - r) / d; gc = (mx - g) / d; bc = (mx - b) / d
    h = np.zeros_like(V)
    ir = mx == r; ig = (mx == g) & ~ir; ib = (mx == b) & ~ir & ~ig
    h[ir] = (bc - gc)[ir]; h[ig] = (2 + rc - bc)[ig]; h[ib] = (4 + gc - rc)[ib]
    hue = (h / 6.0) % 1.0 * 360.0
    return hue, S, V, chroma

def sample_tex(uv):
    # uv: (N,2). V invertida
    x = np.clip(uv[:, 0] * (W - 1), 0, W - 1).astype(np.int32)
    y = np.clip((1.0 - uv[:, 1]) * (H - 1), 0, H - 1).astype(np.int32)
    return img[y, x]

def tri_sample_points(uv, idx):
    # devuelve por triangulo: 7 puntos (centroide,3 vertices,3 medios arista)
    a = uv[idx[:, 0]]; b = uv[idx[:, 1]]; c = uv[idx[:, 2]]
    cen = (a + b + c) / 3.0
    mab = (a + b) / 2.0; mbc = (b + c) / 2.0; mca = (c + a) / 2.0
    # 7 puntos
    pts = np.stack([cen, a, b, c, mab, mbc, mca], axis=1)  # (nTri,7,2)
    return pts

def classify_pts(rgb):
    # rgb (...,3) -> codigo: 0 piel,1 gris/uniforme,2 oliva,3 negro,4 naranja
    hue, S, V, chroma = rgb2hsv_chroma(rgb)
    black = V < 0.14
    skin = (~black) & (hue >= 8) & (hue <= 45) & (S >= 0.18) & (S <= 0.55) & (V > 0.5)
    orange = (~black) & (hue >= 5) & (hue <= 33) & (S > 0.5) & (V > 0.4)
    olive = (~black) & (hue >= 33) & (hue <= 110) & (chroma >= 0.045)
    code = np.ones(rgb.shape[:-1], np.int8)  # default gris
    code[olive] = 2
    code[skin] = 0
    code[orange] = 4
    code[black] = 3
    return code, hue, S, V, chroma

# Probar sobre TORSO (k=5)
m = meshes[5]
uv = m['uv']; idx = m['idx']
pts = tri_sample_points(uv, idx)  # (nTri,7,2)
nTri = pts.shape[0]
flat = pts.reshape(-1, 2)
rgb = sample_tex(flat).reshape(nTri, 7, 3)
code, hue, S, V, chroma = classify_pts(rgb)

# voto dominante por triangulo
def dominant(code):
    out = np.zeros(code.shape[0], np.int8)
    for i in range(code.shape[0]):
        vals, cnts = np.unique(code[i], return_counts=True)
        out[i] = vals[np.argmax(cnts)]
    return out
dom = dominant(code)
names = {0:'piel',1:'gris',2:'oliva',3:'negro',4:'naranja'}
print('=== TORSO (k=5) clasificacion actual por triangulo (dominante de 7 pts) ===')
for v in range(5):
    print(f'  {names[v]:8s}: {(dom==v).sum():5d}  ({100*(dom==v).mean():5.1f}%)')

# Mediana de hue/chroma/V por triangulo (usando centroide para tono)
cen_rgb = rgb[:, 0, :]
hC, sC, vC, chC = rgb2hsv_chroma(cen_rgb)
# Distribucion de chroma/hue para triangulos en rango verde-amarillo
greenish = (hC >= 33) & (hC <= 130)
print('\n=== Triangulos torso con hue centroide en 33..130 (candidatos oliva) ===')
print(f'  n={greenish.sum()}  chroma: min={chC[greenish].min():.3f} p10={np.percentile(chC[greenish],10):.3f} p50={np.percentile(chC[greenish],50):.3f} p90={np.percentile(chC[greenish],90):.3f} max={chC[greenish].max():.3f}')
print(f'  hue: p5={np.percentile(hC[greenish],5):.1f} p50={np.percentile(hC[greenish],50):.1f} p95={np.percentile(hC[greenish],95):.1f}')

# Histograma de chroma sobre TODO el torso (centroide)
print('\n=== Histograma chroma centroide TORSO (todos) ===')
hist, edges = np.histogram(chC, bins=20, range=(0, 0.4))
for i in range(20):
    print(f'  {edges[i]:.3f}-{edges[i+1]:.3f}: {hist[i]:5d}  {"#"*int(hist[i]/30)}')
print('\n=== Histograma hue centroide TORSO (chroma>=0.03) ===')
sel = chC >= 0.03
hist, edges = np.histogram(hC[sel], bins=24, range=(0, 360))
for i in range(24):
    if hist[i] > 0:
        print(f'  hue {edges[i]:5.0f}-{edges[i+1]:5.0f}: {hist[i]:5d}  {"#"*int(hist[i]/20)}')

# ---- render mapa de clasificacion por triangulo en UV (TORSO) ----
def raster_tris(uv, idx, codes, res, palette):
    cv = np.zeros((res, res, 3), np.uint8)
    px = uv[:, 0] * (res - 1)
    py = (1.0 - uv[:, 1]) * (res - 1)
    P = np.stack([px, py], -1)
    for t in range(idx.shape[0]):
        a, b, c = idx[t]
        pa, pb, pc = P[a], P[b], P[c]
        minx = int(max(0, np.floor(min(pa[0], pb[0], pc[0]))))
        maxx = int(min(res - 1, np.ceil(max(pa[0], pb[0], pc[0]))))
        miny = int(max(0, np.floor(min(pa[1], pb[1], pc[1]))))
        maxy = int(min(res - 1, np.ceil(max(pa[1], pb[1], pc[1]))))
        if maxx < minx or maxy < miny: continue
        xs = np.arange(minx, maxx + 1); ys = np.arange(miny, maxy + 1)
        gx, gy = np.meshgrid(xs, ys)
        d = ((pb[1]-pc[1])*(pa[0]-pc[0])+(pc[0]-pb[0])*(pa[1]-pc[1]))
        if abs(d) < 1e-9: continue
        w1 = ((pb[1]-pc[1])*(gx-pc[0])+(pc[0]-pb[0])*(gy-pc[1]))/d
        w2 = ((pc[1]-pa[1])*(gx-pc[0])+(pa[0]-pc[0])*(gy-pc[1]))/d
        w3 = 1 - w1 - w2
        ins = (w1 >= -0.01) & (w2 >= -0.01) & (w3 >= -0.01)
        cv[gy[ins], gx[ins]] = palette[codes[t]]
    return cv

palette = {0:(255,255,0),1:(255,0,255),2:(0,200,0),3:(0,0,255),4:(255,0,0)}
res = 1024
# clasif blue extra: marcar triangulos con hue centroide 190-250 ch>=0.04 como 'AZUL' (codigo 5 -> cyan)
blue_tri = (hC>=190)&(hC<=250)&(chC>=0.04)
dom2 = dom.copy()
pal2 = dict(palette); pal2[5]=(0,255,255)
dom2[blue_tri & (dom!=2) & (dom!=3)] = 5  # solo si no es ya oliva/negro
cv = raster_tris(uv, idx, dom2, res, pal2)
Image.fromarray(cv).save(r'Docs\_analysis\torso_classmap.png')
print('\nguardado Docs/_analysis/torso_classmap.png  (magenta=gris verde=oliva azul=negro amarillo=piel rojo=naranja cyan=AZULleak)')
print('triangulos AZUL-leak (hue190-250):', int((blue_tri & (dom!=2)&(dom!=3)).sum()))
