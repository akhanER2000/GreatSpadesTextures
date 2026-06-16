# -*- coding: utf-8 -*-
"""Motor de exportación a resolución completa (8192²).

Aplica el MISMO recoloreado que el visor 3D (Lab: preserva L*, recentra el
brillo hacia el color objetivo, sustituye a*/b*) pero por región y a máxima
resolución, usando el mapa de regiones por color. La PIEL (región 0) jamás
se toca. Autocontenido para empaquetar con PyInstaller.
"""
import os, sys, json
import numpy as np
from PIL import Image


def _base():
    """Carpeta base (soporta ejecución empaquetada con PyInstaller)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


HERE = _base()


def asset(*p):
    return os.path.join(_base(), "assets", *p)


# ---------- sRGB <-> Lab (idéntico a recolor.py) ----------
_WHITE = np.array([0.95047, 1.0, 1.08883], np.float32)
_M = np.array([[0.4124564, 0.3575761, 0.1804375],
               [0.2126729, 0.7151522, 0.0721750],
               [0.0193339, 0.1191920, 0.9503041]], np.float32)
_Mi = np.linalg.inv(_M).astype(np.float32)


def _s2l(c): return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)
def _l2s(c): c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c*12.92, 1.055*c**(1/2.4)-0.055)
def _f(t): d = 6/29; return np.where(t > d**3, np.cbrt(t), t/(3*d*d)+4/29)
def _fi(t): d = 6/29; return np.where(t > d, t**3, 3*d*d*(t-4/29))


def rgb_to_lab(rgb):
    xyz = (_s2l(rgb) @ _M.T) / _WHITE
    fx, fy, fz = _f(xyz[..., 0]), _f(xyz[..., 1]), _f(xyz[..., 2])
    return np.stack([116*fy-16, 500*(fx-fy), 200*(fy-fz)], -1)


def lab_to_rgb(lab):
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L+16)/116; fx = fy+a/500; fz = fy-b/200
    xyz = np.stack([_fi(fx), _fi(fy), _fi(fz)], -1) * _WHITE
    return _l2s(xyz @ _Mi.T)


def hex_to_rgb01(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c*2 for c in h)
    return np.array([int(h[i:i+2], 16) for i in (0, 2, 4)], np.float32)/255.0


# ---------- Segmentación por región (idéntica a build_assets.py) ----------
def _channels(arr):
    R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = arr.max(-1); mn = arr.min(-1); V = mx; chroma = mx-mn
    S = np.where(mx > 1e-6, chroma/np.maximum(mx, 1e-6), 0.0)
    d = np.where(chroma < 1e-6, 1.0, chroma)
    rc = (mx-R)/d; gc = (mx-G)/d; bc = (mx-B)/d
    h = np.zeros_like(V)
    ir = mx == R; ig = (mx == G) & ~ir; ib = (mx == B) & ~ir & ~ig
    h[ir] = (bc-gc)[ir]; h[ig] = (2+rc-bc)[ig]; h[ib] = (4+gc-rc)[ib]
    return V, S, chroma, (h/6.0) % 1.0*360.0


def region_ids(arr):
    V, S, chroma, hue = _channels(arr)
    black = V < 0.14
    gray = (chroma < 0.07) & (V >= 0.14) & (V <= 0.82)
    olive_like = (hue >= 33) & (hue <= 105) & (chroma >= 0.045)
    gray = gray & ~olive_like
    orange = (~black) & (hue >= 5) & (hue <= 33) & (S > 0.5) & (V > 0.4)
    skin = (~black) & (hue >= 8) & (hue <= 45) & (S >= 0.18) & (S <= 0.5) & (V > 0.5) & ~orange
    olive = (~black) & ~gray & (hue >= 33) & (hue <= 105) & (chroma >= 0.045)
    ids = np.zeros(arr.shape[:2], np.uint8)
    ids[olive] = 2; ids[black] = 3; ids[orange] = 4; ids[gray] = 1; ids[skin] = 0
    return ids


def _source_texture():
    """Textura origen a máxima resolución para exportar."""
    for cand in [asset("texture_8192.jpg"),
                 os.path.join(_base(), "..", "Docs", "blocky_humanoid_3d_model_basecolor.jpg")]:
        if os.path.exists(cand):
            return cand
    return asset("texture_2048.jpg")  # último recurso


def recolor_multi(colors, out_dir, name=None, band=1024):
    """colors = {region_id(int|str): '#rrggbb'}; region 0 (piel) ignorada."""
    meta = json.load(open(asset("regions_meta.json"), encoding="utf-8"))
    meanL = {int(k): v["meanL"] for k, v in meta["regions"].items()}
    targets = {int(k): hex_to_rgb01(v) for k, v in colors.items() if int(k) in (1, 2, 3, 4)}
    tlab = {k: rgb_to_lab(c.reshape(1, 1, 3))[0, 0] for k, c in targets.items()}

    im = Image.open(_source_texture()).convert("RGB")
    W, H = im.size
    arr = np.asarray(im, np.float32)/255.0
    out = np.empty_like(arr)
    for y0 in range(0, H, band):
        sl = slice(y0, min(y0+band, H))
        a = arr[sl]
        ids = region_ids(a)
        L = rgb_to_lab(a)[..., 0]
        res = a.copy()
        for rid, t in tlab.items():
            m = ids == rid
            if not m.any():
                continue
            Ln = np.clip(float(t[0]) + (L[m] - meanL.get(rid, 40.0)), 0, 100)
            nl = np.stack([Ln, np.full_like(Ln, float(t[1])), np.full_like(Ln, float(t[2]))], -1)
            res[m] = lab_to_rgb(nl)
        out[sl] = np.clip(res, 0, 1)

    if not name:
        name = "custom_" + "_".join(f"{k}{colors[str(k)] if str(k) in colors else colors[k]}".lstrip("#")
                                    for k in sorted(int(x) for x in colors))
        name = name.replace("#", "")
    d = os.path.join(out_dir, name)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "blocky_humanoid_3d_model_basecolor.jpg")
    Image.fromarray((out*255+0.5).astype(np.uint8)).save(path, quality=95, subsampling=0)
    return path
