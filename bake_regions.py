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


# ---------- clasificación por color (téxel) ----------
def color_classes(arr):
    R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = arr.max(-1); mn = arr.min(-1); V = mx; chroma = mx - mn
    S = np.where(mx > 1e-6, chroma / np.maximum(mx, 1e-6), 0.0)
    d = np.where(chroma < 1e-6, 1.0, chroma)
    rc = (mx - R) / d; gc = (mx - G) / d; bc = (mx - B) / d
    h = np.zeros_like(V)
    ir = mx == R; ig = (mx == G) & ~ir; ib = (mx == B) & ~ir & ~ig
    h[ir] = (bc - gc)[ir]; h[ig] = (2 + rc - bc)[ig]; h[ib] = (4 + gc - rc)[ib]
    hue = (h / 6.0) % 1.0 * 360.0
    black = V < 0.14
    skin = (~black) & (hue >= 8) & (hue <= 45) & (S >= 0.18) & (S <= 0.5) & (V > 0.5)
    orange = (~black) & (hue >= 5) & (hue <= 33) & (S > 0.5) & (V > 0.4)
    return dict(V=V, S=S, chroma=chroma, hue=hue, black=black, skin=skin, orange=orange)


# ---------- rasterización de triángulos en UV -> mapa de pieza ----------
def rasterize_parts(meshes, part_of_tri, res, flipv=True):
    """part_of_tri: lista por malla de arrays (nTris,) con el id de pieza geométrica."""
    part = np.zeros((res, res), np.int16)  # 0 = sin pieza
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


# Mapeo malla(i del manifest) -> PIEZA geométrica (confirmado visualmente):
#  head=1 torso=2 arm=3 legs=4 detail(correa/oreja)=5
PART_BY_MESH = {0: 5, 1: 4, 2: 3, 3: 5, 4: 3, 5: 2, 6: 1}
SIZE = 2048


def bake():
    sys.path.insert(0, os.path.join(ROOT, "app"))
    import engine

    meshes, gmin, gmax = load_geom()
    print("GLOBAL size", (gmax-gmin).round(3))
    part_of_tri = []
    for m in meshes:
        pid = PART_BY_MESH.get(m["i"], 0)
        part_of_tri.append(np.full(m["idx"].shape[0], pid, np.int16))
        print(f"  #{m['i']} {m['name']:16s} -> pieza {pid}  (tris={m['idx'].shape[0]})")

    print("Rasterizando partmap (UV)...")
    gp = rasterize_parts(meshes, part_of_tri, SIZE, flipv=True)
    print("  cobertura partmap (cruda):", f"{100*(gp>0).mean():.1f}%")

    # Dilatar para cerrar costuras finas (gp=0 entre triángulos/islas):
    # rellena solo los píxeles vacíos con el id del vecino, sin mover bordes existentes.
    from PIL import ImageFilter
    for _ in range(3):
        zero = gp == 0
        if not zero.any():
            break
        grown = np.asarray(Image.fromarray(gp.astype(np.uint8)).filter(ImageFilter.MaxFilter(3)))
        gp = np.where(zero, grown.astype(np.int16), gp)
    print("  cobertura partmap (dilatada):", f"{100*(gp>0).mean():.1f}%")

    # guardar partmap (R = id de pieza)
    pm = np.zeros((SIZE, SIZE, 3), np.uint8); pm[..., 0] = gp.astype(np.uint8)
    pm[..., 1] = (gp * 40).astype(np.uint8)
    Image.fromarray(pm).save(os.path.join(ASSETS, "partmap_2048.png"))

    # textura base 2048 y combinación geometría+color -> regiones finales
    tex = np.asarray(Image.open(os.path.join(ASSETS, "texture_2048.jpg")).convert("RGB"),
                     np.float32) / 255.0
    ids = engine.combine_regions(gp, tex)
    reg = np.zeros((SIZE, SIZE, 3), np.uint8); reg[..., 0] = ids; reg[..., 1] = (ids * 30).astype(np.uint8)
    Image.fromarray(reg).save(os.path.join(ASSETS, "regions_2048.png"))

    # meta: brillo medio L* por región (para recentrar al recolorear)
    L = engine.rgb_to_lab(tex)[..., 0]
    meta = {"size": SIZE, "flipY": True, "regions": {}}
    for rid in range(1, 8):
        m = ids == rid
        meta["regions"][str(rid)] = {"name": NAMES.get(rid, str(rid)),
            "meanL": float(L[m].mean()) if m.any() else 50.0,
            "pct": float(100 * m.mean())}
    json.dump(meta, open(os.path.join(ASSETS, "regions_meta.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    print("Regiones finales (% del atlas):")
    for rid in range(0, 8):
        print(f"  {rid} {NAMES.get(rid,'-'):9s}: {100*(ids==rid).mean():5.1f}%")

    # visualización de auditoría (color por región sobre luminancia)
    PAL = {0:(40,40,46),1:(60,120,255),2:(90,200,90),3:(20,20,20),
           4:(255,120,40),5:(200,80,220),6:(60,60,70),7:(240,210,90)}
    lum = (0.2126*tex[...,0]+0.7152*tex[...,1]+0.0722*tex[...,2])
    viz = np.stack([lum]*3, -1)
    for rid, col in PAL.items():
        if rid == 0: continue
        m = ids == rid
        viz[m] = viz[m]*0.25 + np.array(col, np.float32)/255.0*0.75
    Image.fromarray((viz*255).astype(np.uint8)).resize((1024,1024)).save(
        os.path.join(ROOT, "Docs", "_analysis", "regions_debug.png"))
    print("OK -> partmap_2048.png, regions_2048.png, regions_meta.json, Docs/_analysis/regions_debug.png")


if __name__ == "__main__":
    if "--inspect" in sys.argv:
        meshes, gmin, gmax = load_geom()
        print("GLOBAL min", gmin.round(3), "max", gmax.round(3), "size", (gmax-gmin).round(3))
        for m in meshes:
            cn = (m["center"] - gmin) / np.maximum(gmax - gmin, 1e-6)
            print(f"  #{m['i']:2d} {m['name']:20s} verts={m['pos'].shape[0]:6d} "
                  f"tris={m['idx'].shape[0]:6d} centroY_norm={cn[1]:.2f} cx_norm={cn[0]:.2f}")
    else:
        bake()
