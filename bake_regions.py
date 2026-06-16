# -*- coding: utf-8 -*-
"""Hornea el MAPA DE REGIONES por GEOMETRÍA (+ color), robusto al desgaste/camo.

Lee la geometría extraída (app/assets/geom/) con three.js y:
  1. Clasifica cada triángulo en una PIEZA por su posición 3D (y/o malla).
  2. Rasteriza los triángulos en espacio UV -> mapa de PIEZA por téxel.
  3. Sub-clasifica por COLOR (piel/gris/oliva/negro/naranja) dentro de cada pieza.
  4. Produce el mapa de regiones final (ids) a la resolución pedida.

IDs finales:
  0 = piel/cara            (BLOQUEADO)
  1 = uniforme             (recolor)
  2 = chaleco              (recolor)
  3 = botas                (recolor)
  4 = cuello/naranja       (recolor)
  5 = casco                (recolor)
  6 = guantes              (recolor)
  7 = correa barbilla/metal(BLOQUEADO, gris)
"""
import os, json, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
GEOM = os.path.join(ROOT, "app", "assets", "geom")
ASSETS = os.path.join(ROOT, "app", "assets")
SRC8192 = os.path.join(ROOT, "Docs", "blocky_humanoid_3d_model_basecolor.jpg")

LOCKED = {0, 7}
RECOLOR = {1, 2, 3, 4, 5, 6}
NAMES = {0: "piel", 1: "uniforme", 2: "chaleco", 3: "botas", 4: "cuello",
         5: "casco", 6: "guantes", 7: "correa"}


# ---------- carga de geometría ----------
def load_geom():
    man = json.load(open(os.path.join(GEOM, "manifest.json"), encoding="utf-8"))
    meshes = []
    for m in man["meshes"]:
        i = m["i"]
        pos = np.fromfile(os.path.join(GEOM, f"pos_{i}.bin"), np.float32).reshape(-1, 3)
        uv = np.fromfile(os.path.join(GEOM, f"uv_{i}.bin"), np.float32).reshape(-1, 2)
        idx = np.fromfile(os.path.join(GEOM, f"idx_{i}.bin"), np.uint32).reshape(-1, 3)
        meshes.append(dict(i=i, name=m["name"], pos=pos, uv=uv, idx=idx,
                           center=np.array(m["center"]), size=np.array(m["size"])))
    gb = man["globalBox"]
    return meshes, np.array(gb["min"]), np.array(gb["max"])


# =====================  PARÁMETROS (afinados con subagentes)  ===============
PART_BY_MESH = {0: "detail", 1: "legs", 2: "arm", 3: "detail",
                4: "arm", 5: "torso", 6: "head"}
# Color
BLACK_V      = 0.14          # negro (botas/guantes/correas)
OLIVE_HUE    = (33, 115)     # oliva (chaleco/mochila)
OLIVE_CHROMA = 0.05          # oliva incluso oscuro/desgastado
# Cara (geometría): triángulos frontales de la cabeza -> bloqueados.
# La normal.x NO es fiable (winding inconsistente del FBX): se usa la PROFUNDIDAD
# frontal cxn (la cara está adelante, cxn alto; el casco gris detrás, cxn bajo).
FACE_CXN = 0.79              # profundidad frontal mínima (centroide X normalizado)
FACE_Y   = (0.77, 0.875)    # banda de altura de la cara (yhi=0.875 = corte cara/ala)
FACE_ZW  = 0.11             # |czn-0.5| máximo (central)
CUELLO_CYN = 0.78            # naranja -> cuello solo en parte alta del torso (cuello)
BOOT_Y = 0.17               # botas: negro solo en los PIES (cyn bajo); el negro
                            # de ingle/rodilla queda bloqueado (cremalleras/broches)
# clases de color (enteros)
C_GRAY, C_SKIN, C_OLIVE, C_BLACK, C_ORANGE = 0, 1, 2, 3, 4


# ---------- clasificación de color de MUESTRAS RGB (vectorizada) ----------
def classify_rgb(rgb):
    """rgb (...,3) en [0,1] -> etiqueta entera por píxel/muestra."""
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(-1); mn = rgb.min(-1); V = mx; chroma = mx - mn
    S = np.where(mx > 1e-6, chroma / np.maximum(mx, 1e-6), 0.0)
    d = np.where(chroma < 1e-6, 1.0, chroma)
    rc = (mx - R) / d; gc = (mx - G) / d; bc = (mx - B) / d
    h = np.zeros_like(V)
    ir = mx == R; ig = (mx == G) & ~ir; ib = (mx == B) & ~ir & ~ig
    h[ir] = (bc - gc)[ir]; h[ig] = (2 + rc - bc)[ig]; h[ib] = (4 + gc - rc)[ib]
    hue = (h / 6.0) % 1.0 * 360.0
    warm = (G - B) > 0.012          # oliva = cálido (G>B); gris neutro y negro no
    lab = np.zeros(V.shape, np.int8)  # gris por defecto
    # oliva (chaleco/mochila): nítido O desgastado cálido (lo que antes se fugaba)
    olive = (hue >= 30) & (hue <= 118) & ((chroma >= 0.06) | ((chroma >= 0.025) & warm))
    orange = (hue >= 5) & (hue <= 33) & (S > 0.45) & (V > 0.4)
    skin = (hue >= 8) & (hue <= 45) & (S >= 0.18) & (S <= 0.55) & (V > 0.5) & ~orange
    lab[olive] = C_OLIVE
    lab[skin] = C_SKIN
    lab[orange] = C_ORANGE
    lab[V < BLACK_V] = C_BLACK     # negro tiene prioridad...
    # ...salvo oliva OSCURO cálido (sombra del chaleco): se rescata como oliva
    dark_olive = (V < BLACK_V) & warm & (hue >= 30) & (hue <= 118) & (chroma >= 0.02)
    lab[dark_olive] = C_OLIVE
    return lab


# ---------- color DOMINANTE por triángulo (muestreo de varios puntos) ----------
def triangle_dominant(mesh, texarr):
    H, W = texarr.shape[:2]
    uv = mesh["uv"]; idx = mesh["idx"]
    if uv.shape[0] == 0 or idx.shape[0] == 0:
        return np.zeros(idx.shape[0], np.int8)
    v0, v1, v2 = uv[idx[:, 0]], uv[idx[:, 1]], uv[idx[:, 2]]
    cen = (v0 + v1 + v2) / 3.0
    pts = [cen, (v0+v1)/2, (v1+v2)/2, (v2+v0)/2,
           0.6*v0+0.4*cen, 0.6*v1+0.4*cen, 0.6*v2+0.4*cen]
    M = idx.shape[0]
    counts = np.zeros((5, M), np.int32)
    for p in pts:
        px = np.clip((p[:, 0] * (W - 1)).astype(int), 0, W - 1)
        py = np.clip(((1.0 - p[:, 1]) * (H - 1)).astype(int), 0, H - 1)
        lab = classify_rgb(texarr[py, px])
        for c in range(5):
            counts[c] += (lab == c)
    return counts.argmax(0).astype(np.int8)


# ---------- geometría por triángulo (normal + centroide normalizado) ----------
def triangle_geo(mesh, gmin, gmax):
    pos = mesh["pos"]; idx = mesh["idx"]
    p0, p1, p2 = pos[idx[:, 0]], pos[idx[:, 1]], pos[idx[:, 2]]
    n = np.cross(p1 - p0, p2 - p0)
    n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    cen = (p0 + p1 + p2) / 3.0
    cn = (cen - gmin) / np.maximum(gmax - gmin, 1e-6)
    return n, cn


# ---------- región final por triángulo (malla + color + geometría) ----------
FACE_LOCK = 8   # id interno para 'bloqueado por cara/piel/accesorio' (se mapea a 0 al final)


def classify_mesh(part, n, cn, dom, face_y):
    M = dom.shape[0]
    cxn = cn[:, 0]; cyn = cn[:, 1]; czn = cn[:, 2]
    reg = np.zeros(M, np.uint8)
    if part == "detail":
        reg[:] = FACE_LOCK               # correa/oreja: siempre original (bloqueado)
        return reg
    if part == "head":
        is_face = (cxn > FACE_CXN) & (cyn >= face_y[0]) & (cyn <= face_y[1]) & (np.abs(czn-0.5) < FACE_ZW)
        reg[:] = 5                       # casco
        reg[is_face] = FACE_LOCK         # CARA bloqueada (incluye cejas/ojos)
        reg[dom == C_SKIN] = FACE_LOCK   # piel siempre bloqueada
        return reg
    if part == "torso":
        reg[:] = 1                       # uniforme (chaqueta)
        reg[dom == C_OLIVE] = 2          # chaleco/mochila
        reg[dom == C_BLACK] = 7          # correas (bloqueado)
        reg[(dom == C_ORANGE) & (cyn > CUELLO_CYN)] = 4  # cuello
        reg[dom == C_SKIN] = FACE_LOCK
        return reg
    if part == "arm":
        reg[:] = 1                       # brazo = uniforme (no hay piel real aquí)
        reg[dom == C_BLACK] = 6          # guantes
        return reg
    if part == "legs":
        reg[:] = 1                       # pierna = uniforme (no hay piel real aquí)
        black = dom == C_BLACK
        reg[black & (cyn < BOOT_Y)] = 3          # botas (solo los pies)
        reg[black & (cyn >= BOOT_Y)] = 7         # herraje negro (ingle/rodilla) bloqueado
        return reg
    return reg


# ---------- rasterización de triángulos en UV -> mapa de pieza ----------
def rasterize_parts(meshes, part_of_tri, res, flipv=True, init=0):
    """part_of_tri: lista por malla de arrays (nTris,) con el id de región por triángulo."""
    part = np.full((res, res), init, np.int16)  # init = sin asignar (gutter)
    for mi, m in enumerate(meshes):
        uv = m["uv"]; idx = m["idx"]; parts = part_of_tri[mi]
        if uv.shape[0] == 0:
            continue
        px = uv[:, 0] * (res - 1)
        py = (1.0 - uv[:, 1]) * (res - 1) if flipv else uv[:, 1] * (res - 1)
        P = np.stack([px, py], -1)
        for t in range(idx.shape[0]):
            a, b, c = idx[t]
            pa, pb, pc = P[a], P[b], P[c]
            minx = int(max(0, np.floor(min(pa[0], pb[0], pc[0]))))
            maxx = int(min(res - 1, np.ceil(max(pa[0], pb[0], pc[0]))))
            miny = int(max(0, np.floor(min(pa[1], pb[1], pc[1]))))
            maxy = int(min(res - 1, np.ceil(max(pa[1], pb[1], pc[1]))))
            if maxx < minx or maxy < miny:
                continue
            xs = np.arange(minx, maxx + 1)
            ys = np.arange(miny, maxy + 1)
            gx, gy = np.meshgrid(xs, ys)
            # baricéntricas
            d = ((pb[1]-pc[1])*(pa[0]-pc[0])+(pc[0]-pb[0])*(pa[1]-pc[1]))
            if abs(d) < 1e-9:
                continue
            w1 = ((pb[1]-pc[1])*(gx-pc[0])+(pc[0]-pb[0])*(gy-pc[1]))/d
            w2 = ((pc[1]-pa[1])*(gx-pc[0])+(pa[0]-pc[0])*(gy-pc[1]))/d
            w3 = 1 - w1 - w2
            inside = (w1 >= -0.001) & (w2 >= -0.001) & (w3 >= -0.001)
            if inside.any():
                part[gy[inside], gx[inside]] = parts[t]
    return part


def tri_centroids_norm(m, gmin, gmax):
    """Centroides de triángulo normalizados [0,1] en cada eje (Y-up)."""
    p = m["pos"]; idx = m["idx"]
    cen = (p[idx[:, 0]] + p[idx[:, 1]] + p[idx[:, 2]]) / 3.0
    size = np.maximum(gmax - gmin, 1e-6)
    return (cen - gmin) / size, cen


SIZE = 2048


def _rgb_to_L(tex):
    """L* (perceptual) para meta; misma fórmula que engine."""
    def s2l(c): return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)
    lin = s2l(tex)
    Y = lin[..., 0]*0.2126729 + lin[..., 1]*0.7151522 + lin[..., 2]*0.0721750
    return np.where(Y > 0.008856, 116*np.cbrt(Y)-16, 903.3*Y)


def bake():
    meshes, gmin, gmax = load_geom()
    print("GLOBAL size", (gmax-gmin).round(3))
    tex = np.asarray(Image.open(os.path.join(ASSETS, "texture_2048.jpg")).convert("RGB"),
                     np.float32) / 255.0

    # Banda de altura de la cara: fija (calibrada por el análisis de la malla #6).
    # yhi=0.875 es el corte limpio cara/ala del casco (subirlo dispara el gris).
    face_y = FACE_Y

    # Región final POR TRIÁNGULO (malla + color dominante + geometría)
    region_of_tri = []
    for m in meshes:
        part = PART_BY_MESH.get(m["i"], "detail")
        n, cn = triangle_geo(m, gmin, gmax)
        dom = triangle_dominant(m, tex)
        reg = classify_mesh(part, n, cn, dom, face_y)
        region_of_tri.append(reg.astype(np.int16))
        cnt = {NAMES.get(int(r) if r != FACE_LOCK else 0, "bloq"): int((reg == r).sum())
               for r in np.unique(reg)}
        print(f"  #{m['i']} {m['name']:14s} {part:7s} tris={len(reg):5d}  {cnt}")

    print("Rasterizando regiones por triángulo...")
    raw = rasterize_parts(meshes, region_of_tri, SIZE, flipv=True, init=0)  # 0 = gutter

    # Dilatar SOLO el gutter (0); la cara va con id 8, así no se la come la dilatación.
    from PIL import ImageFilter
    for _ in range(3):
        gut = raw == 0
        if not gut.any():
            break
        grown = np.asarray(Image.fromarray(raw.astype(np.uint8)).filter(ImageFilter.MaxFilter(3)))
        raw = np.where(gut, grown.astype(np.int16), raw)
    ids = raw.astype(np.uint8)
    ids[ids == FACE_LOCK] = 0          # cara/piel/accesorios -> 0 (bloqueado)

    reg = np.zeros((SIZE, SIZE, 3), np.uint8)
    reg[..., 0] = ids; reg[..., 1] = (ids * 30).astype(np.uint8)
    Image.fromarray(reg).save(os.path.join(ASSETS, "regions_2048.png"))

    # meta: brillo medio L* por región
    L = _rgb_to_L(tex)
    meta = {"size": SIZE, "flipY": True, "regions": {}}
    for rid in range(1, 8):
        mm = ids == rid
        meta["regions"][str(rid)] = {"name": NAMES.get(rid, str(rid)),
            "meanL": float(L[mm].mean()) if mm.any() else 50.0,
            "pct": float(100 * mm.mean())}
    json.dump(meta, open(os.path.join(ASSETS, "regions_meta.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    print("Regiones finales (% del atlas):")
    for rid in range(0, 8):
        print(f"  {rid} {NAMES.get(rid, '-'):9s}: {100*(ids == rid).mean():5.1f}%")

    # visualización de auditoría (color por región sobre luminancia)
    PAL = {1:(60,120,255), 2:(90,200,90), 3:(200,40,40), 4:(255,150,30),
           5:(200,80,220), 6:(40,210,230), 7:(240,210,90)}
    lum = (0.2126*tex[..., 0]+0.7152*tex[..., 1]+0.0722*tex[..., 2])
    viz = np.stack([lum]*3, -1)
    for rid, col in PAL.items():
        mm = ids == rid
        viz[mm] = viz[mm]*0.25 + np.array(col, np.float32)/255.0*0.75
    Image.fromarray((viz*255).astype(np.uint8)).resize((1024, 1024)).save(
        os.path.join(ROOT, "Docs", "_analysis", "regions_debug.png"))
    print("OK -> regions_2048.png, regions_meta.json, Docs/_analysis/regions_debug.png")


if __name__ == "__main__":
    bake()
