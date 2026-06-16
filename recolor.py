#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
=============================================================================
 GreatSpades - Recoloreador de uniforme/casco del soldado voxel
=============================================================================

Cambia el color de la ZONA GRIS (uniforme + casco) de la textura del soldado
a CUALQUIER color que indiques, SIN perder los detalles de la tela
(trama, costuras, dibujos, bolsillos, sombras de los pliegues).

Como funciona (resumen tecnico):
  1. Segmenta la textura por color en el espacio HSV/croma y aisla los
     pixeles "gris recoloreable" (uniforme + casco), protegiendo el chaleco
     oliva, los guantes/botas negros, la piel y el cuello naranja.
  2. Convierte a espacio Lab y RECOLOREA preservando el detalle:
        - Mantiene la VARIACION de luminancia L* (= toda la textura/tela).
        - Recentra el brillo medio hacia el del color objetivo.
        - Sustituye la cromaticidad (a*, b*) por la del color objetivo.
     Resultado: misma tela, mismas costuras y dibujos, color nuevo.
  3. Mezcla con una mascara suavizada (feather) para bordes limpios.

Uso:
  python recolor.py --color "#1b2f5e" --name azul_marino
  python recolor.py --color forest
  python recolor.py --color "#7a1f1f" --helmet-color "#202020" --name rojo_casco_negro
  python recolor.py --color navy --size 2048        # vista rapida (preview)
  python recolor.py --all-palette                   # genera toda la paleta

Salida: Variaciones/<name>/blocky_humanoid_3d_model_basecolor.jpg  (8192x8192)
        + preview_<name>.png (comparativa) en la misma carpeta.
=============================================================================
"""
import argparse
import json
import os
import sys
import numpy as np
from PIL import Image

# ----------------------------------------------------------------------------
# Rutas
# ----------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_TEXTURE = os.path.join(ROOT, "Docs", "blocky_humanoid_3d_model_basecolor.jpg")
OUT_ROOT = os.path.join(ROOT, "Variaciones")
PALETTE_FILE = os.path.join(ROOT, "palette.json")

# ----------------------------------------------------------------------------
# Paleta de colores con nombre (se puede ampliar en palette.json)
# ----------------------------------------------------------------------------
DEFAULT_PALETTE = {
    "navy":        "#1b2f5e",   # azul marino
    "azul_marino": "#1b2f5e",
    "forest":      "#2f4a22",   # verde bosque
    "verde":       "#3a5a2a",
    "oliva":       "#4f4a28",
    "rojo":        "#7a1f1f",   # rojo oscuro
    "maroon":      "#5a1d1d",
    "burdeos":     "#4a1530",
    "negro":       "#1a1a1c",
    "urbano":      "#3a4048",   # gris urbano azulado
    "arena":       "#9c8862",   # tan / desierto
    "coyote":      "#7d684a",
    "tierra":      "#5a4632",
    "morado":      "#3d2a55",
    "teal":        "#1f4a4a",
    "blanco_inv":  "#cfd3d6",   # gris claro invierno
}

# ----------------------------------------------------------------------------
# Conversion de color
# ----------------------------------------------------------------------------
def hex_to_rgb01(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"Color hex invalido: {h}")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0


def resolve_color(token, palette):
    """Acepta '#rrggbb', 'rrggbb' o un nombre de la paleta."""
    t = token.strip().lower()
    if t in palette:
        return hex_to_rgb01(palette[t])
    return hex_to_rgb01(t)


# ----------------------------------------------------------------------------
# sRGB <-> Lab (D65), vectorizado en numpy
# ----------------------------------------------------------------------------
_WHITE = np.array([0.95047, 1.0, 1.08883], dtype=np.float32)
_M_RGB2XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
], dtype=np.float32)
_M_XYZ2RGB = np.linalg.inv(_M_RGB2XYZ).astype(np.float32)


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * (c ** (1 / 2.4)) - 0.055)


def _f(t):
    d = 6.0 / 29.0
    return np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4.0 / 29.0)


def _f_inv(t):
    d = 6.0 / 29.0
    return np.where(t > d, t ** 3, 3 * d * d * (t - 4.0 / 29.0))


def rgb_to_lab(rgb):
    """rgb: (...,3) en [0,1] sRGB -> Lab."""
    lin = srgb_to_linear(rgb)
    xyz = lin @ _M_RGB2XYZ.T
    xyz = xyz / _WHITE
    fx, fy, fz = _f(xyz[..., 0]), _f(xyz[..., 1]), _f(xyz[..., 2])
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return np.stack([L, a, b], axis=-1)


def lab_to_rgb(lab):
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0
    xyz = np.stack([_f_inv(fx), _f_inv(fy), _f_inv(fz)], axis=-1) * _WHITE
    lin = xyz @ _M_XYZ2RGB.T
    return linear_to_srgb(lin)


# ----------------------------------------------------------------------------
# Mascara de la zona recoloreable (gris uniforme + casco)
# Umbrales validados con el analisis de la textura.
# ----------------------------------------------------------------------------
def compute_channels(arr):
    R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = arr.max(-1)
    mn = arr.min(-1)
    V = mx
    chroma = mx - mn
    S = np.where(mx > 1e-6, chroma / np.maximum(mx, 1e-6), 0.0)
    delta = np.where(chroma < 1e-6, 1.0, chroma)
    rc = (mx - R) / delta
    gc = (mx - G) / delta
    bc = (mx - B) / delta
    h = np.zeros_like(V)
    is_r = mx == R
    is_g = (mx == G) & ~is_r
    is_b = (mx == B) & ~is_r & ~is_g
    h[is_r] = (bc - gc)[is_r]
    h[is_g] = (2 + rc - bc)[is_g]
    h[is_b] = (4 + gc - rc)[is_b]
    hue = (h / 6.0) % 1.0 * 360.0
    return V, S, chroma, hue


def recolor_mask(arr,
                 chroma_gray=0.07, v_floor=0.14, v_ceil=0.82,
                 olive_lo=33, olive_hi=105, chroma_olive_protect=0.045):
    """Devuelve mascara booleana de la zona 'gris recoloreable'."""
    V, S, chroma, hue = compute_channels(arr)
    gray = (chroma < chroma_gray) & (V >= v_floor) & (V <= v_ceil)
    olive_like = (hue >= olive_lo) & (hue <= olive_hi) & (chroma >= chroma_olive_protect)
    return gray & ~olive_like


def feather_mask(mask_bool, radius=1.5):
    """Suaviza los bordes de la mascara (gaussian, via PIL) -> alpha [0,1]."""
    from PIL import ImageFilter
    if radius <= 0:
        return mask_bool.astype(np.float32)
    m = Image.fromarray((mask_bool.astype(np.uint8) * 255), mode="L")
    m = m.filter(ImageFilter.GaussianBlur(radius=radius))
    return np.asarray(m, dtype=np.float32) / 255.0


# ----------------------------------------------------------------------------
# Recoloreado preservando detalle (Lab)
# ----------------------------------------------------------------------------
def recolor_region(rgb, alpha, target_rgb01, contrast=1.0, chroma_scale=1.0,
                   ref_L_mean=None):
    """Recolorea pixeles segun alpha hacia target_rgb01, preservando el
    detalle de luminancia.
        L_new = L_target + (L_src - L_src_mean)*contrast
        a_new, b_new = (a_target, b_target)*chroma_scale
    """
    lab = rgb_to_lab(rgb)
    L = lab[..., 0]
    tlab = rgb_to_lab(target_rgb01.reshape(1, 1, 3))[0, 0]
    Lt, at, bt = float(tlab[0]), float(tlab[1]), float(tlab[2])

    if ref_L_mean is None:
        w = alpha
        ref_L_mean = float((L * w).sum() / max(w.sum(), 1e-6))

    L_new = Lt + (L - ref_L_mean) * contrast
    L_new = np.clip(L_new, 0.0, 100.0)
    a_new = np.full_like(L, at * chroma_scale)
    b_new = np.full_like(L, bt * chroma_scale)
    new_lab = np.stack([L_new, a_new, b_new], axis=-1)
    new_rgb = lab_to_rgb(new_lab)

    a3 = alpha[..., None]
    out = rgb * (1.0 - a3) + new_rgb * a3
    return np.clip(out, 0.0, 1.0)


# ----------------------------------------------------------------------------
# Pipeline principal
# ----------------------------------------------------------------------------
def load_palette():
    pal = dict(DEFAULT_PALETTE)
    if os.path.exists(PALETTE_FILE):
        try:
            with open(PALETTE_FILE, "r", encoding="utf-8") as f:
                pal.update(json.load(f))
        except Exception as e:
            print(f"[aviso] no se pudo leer palette.json: {e}")
    return pal


def process(color_token, name=None, helmet_token=None, helmet_mask_path=None,
            size=None, contrast=1.0, chroma_scale=1.0, feather=1.5,
            src=SRC_TEXTURE):
    palette = load_palette()
    target = resolve_color(color_token, palette)
    name = name or color_token.lstrip("#").lower()
    out_dir = os.path.join(OUT_ROOT, name)
    os.makedirs(out_dir, exist_ok=True)

    print(f"[1/5] Cargando textura: {os.path.basename(src)}")
    im = Image.open(src).convert("RGB")
    full_size = im.size
    if size:
        im = im.resize((size, size), Image.LANCZOS)
    arr = np.asarray(im, dtype=np.float32) / 255.0
    H, W = arr.shape[:2]

    print(f"[2/5] Segmentando zona recoloreable ({W}x{H})...")
    mask = recolor_mask(arr)
    pct = 100.0 * mask.mean()
    print(f"       zona gris (uniforme+casco) = {pct:.1f}%")

    # Separacion opcional casco/uniforme via mascara externa
    helmet_alpha = None
    helmet_rgb = None
    if helmet_token and helmet_mask_path and os.path.exists(helmet_mask_path):
        hm = Image.open(helmet_mask_path).convert("L").resize((W, H), Image.NEAREST)
        hm = np.asarray(hm, dtype=np.float32) / 255.0 > 0.5
        helmet_alpha = feather_mask(mask & hm, feather)
        uniform_alpha = feather_mask(mask & ~hm, feather)
        helmet_rgb = resolve_color(helmet_token, palette)
        print(f"       casco={100*(mask&hm).mean():.1f}%  uniforme={100*(mask&~hm).mean():.1f}%")
    else:
        uniform_alpha = feather_mask(mask, feather)

    # Brillo medio de la zona gris (para recentrar la luminancia). Se estima en
    # baja resolucion: es estadisticamente identico y evita una pasada Lab cara.
    small = np.asarray(Image.fromarray((arr * 255).astype(np.uint8))
                       .resize((512, 512), Image.LANCZOS), dtype=np.float32) / 255.0
    sm_mask = recolor_mask(small)
    ref_L_mean = float(rgb_to_lab(small)[..., 0][sm_mask].mean()) if sm_mask.any() else 40.0

    print(f"[3/5] Recoloreando (Lab, preservando detalle) brillo_ref={ref_L_mean:.1f}...")
    # Procesamiento por bandas horizontales para acotar memoria en 8192x8192
    out = np.empty_like(arr)
    band = 1024
    for y0 in range(0, H, band):
        sl = slice(y0, min(y0 + band, H))
        o = recolor_region(arr[sl], uniform_alpha[sl], target,
                           contrast=contrast, chroma_scale=chroma_scale,
                           ref_L_mean=ref_L_mean)
        if helmet_alpha is not None:
            o = recolor_region(o, helmet_alpha[sl], helmet_rgb,
                               contrast=contrast, chroma_scale=chroma_scale,
                               ref_L_mean=ref_L_mean)
        out[sl] = o

    out_im = Image.fromarray((out * 255.0 + 0.5).astype(np.uint8))

    print(f"[4/5] Guardando textura final ({W}x{H})...")
    out_path = os.path.join(out_dir, "blocky_humanoid_3d_model_basecolor.jpg")
    out_im.save(out_path, quality=95, subsampling=0)

    print(f"[5/5] Generando comparativa de verificacion...")
    make_preview(arr, out, mask, target, helmet_token, palette, out_dir, name)

    print(f"\nOK -> {out_path}")
    return out_path


def make_preview(src_arr, out_arr, mask, target, helmet_token, palette,
                 out_dir, name, thumb=720):
    """Comparativa: original | recoloreada | mascara, a baja resolucion."""
    def to_thumb(a):
        im = Image.fromarray((a * 255 + 0.5).astype(np.uint8))
        im.thumbnail((thumb, thumb))
        return im
    a = to_thumb(src_arr)
    b = to_thumb(out_arr)
    mk = Image.fromarray((mask * 255).astype(np.uint8)).convert("RGB")
    mk.thumbnail((thumb, thumb))
    w, h = a.size
    sw = mk.size[0]
    canvas = Image.new("RGB", (w + b.size[0] + sw + 24, max(h, b.size[1], mk.size[1])), (30, 30, 34))
    canvas.paste(a, (0, 0))
    canvas.paste(b, (w + 12, 0))
    canvas.paste(mk, (w + b.size[0] + 24, 0))
    canvas.save(os.path.join(out_dir, f"preview_{name}.png"))


def main():
    ap = argparse.ArgumentParser(description="Recoloreador de uniforme/casco del soldado voxel")
    ap.add_argument("--color", help="Color objetivo: #rrggbb o nombre de la paleta")
    ap.add_argument("--name", help="Nombre de la variacion (carpeta de salida)")
    ap.add_argument("--helmet-color", help="(Opcional) color distinto para el casco")
    ap.add_argument("--helmet-mask", help="(Opcional) PNG mascara del casco (blanco=casco)")
    ap.add_argument("--size", type=int, help="Resolucion de trabajo (preview rapido, p.ej. 2048)")
    ap.add_argument("--contrast", type=float, default=1.0, help="Contraste de la tela (1.0=original)")
    ap.add_argument("--chroma-scale", type=float, default=1.0, help="Intensidad del color (1.0=objetivo)")
    ap.add_argument("--feather", type=float, default=1.5, help="Suavizado de bordes de mascara")
    ap.add_argument("--all-palette", action="store_true", help="Genera todas las variaciones de la paleta")
    ap.add_argument("--src", default=SRC_TEXTURE, help="Textura origen")
    args = ap.parse_args()

    if args.all_palette:
        palette = load_palette()
        seen = {}
        for nm, hx in palette.items():
            if hx in seen:
                continue
            seen[hx] = nm
            print(f"\n=== {nm} ({hx}) ===")
            process(hx, name=nm, size=args.size, contrast=args.contrast,
                    chroma_scale=args.chroma_scale, feather=args.feather, src=args.src)
        return

    if not args.color:
        ap.error("indica --color, o usa --all-palette")
    process(args.color, name=args.name, helmet_token=args.helmet_color,
            helmet_mask_path=args.helmet_mask, size=args.size,
            contrast=args.contrast, chroma_scale=args.chroma_scale,
            feather=args.feather, src=args.src)


if __name__ == "__main__":
    main()
