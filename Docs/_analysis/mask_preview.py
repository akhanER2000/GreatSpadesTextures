"""Genera una previsualizacion de la mascara de recoloreado superpuesta
sobre la textura, para verificar que captura SOLO uniforme + casco (gris)."""
import numpy as np
from PIL import Image

SRC = r"J:\Code\GreatSpadesTextures\Docs\blocky_humanoid_3d_model_basecolor.jpg"
OUT = r"J:\Code\GreatSpadesTextures\Docs\_analysis"

im = Image.open(SRC).convert("RGB")
im2k = im.resize((2048, 2048), Image.LANCZOS)
arr = np.asarray(im2k, dtype=np.float32) / 255.0
R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
mx = arr.max(-1); mn = arr.min(-1)
V = mx
chroma = mx - mn                      # croma absoluto 0..1
L = 0.2126*R + 0.7152*G + 0.0722*B

# Hue (0..360), -1 si gris puro
delta = np.where(chroma < 1e-6, 1.0, chroma)
rc = (mx - R)/delta; gc = (mx - G)/delta; bc = (mx - B)/delta
h = np.zeros_like(V)
is_r = mx == R; is_g = (mx == G) & ~is_r; is_b = (mx == B) & ~is_r & ~is_g
h[is_r] = (bc - gc)[is_r]; h[is_g] = (2+rc-bc)[is_g]; h[is_b] = (4+gc-rc)[is_b]
hue = (h/6.0) % 1.0 * 360.0

def recolor_mask(chroma, V, hue,
                 chroma_gray=0.07, v_floor=0.14, v_ceil=0.80,
                 olive_lo=35, olive_hi=100, chroma_olive_protect=0.045):
    """Pixel recoloreable = gris (croma baja) y no negro/blanco.
    Protege oliva: si tiene tono verde-amarillo con algo de croma, se excluye."""
    gray = (chroma < chroma_gray) & (V >= v_floor) & (V <= v_ceil)
    olive_like = (hue >= olive_lo) & (hue <= olive_hi) & (chroma >= chroma_olive_protect)
    return gray & ~olive_like

mask = recolor_mask(chroma, V, hue)
print(f"Mascara recoloreable: {100*mask.mean():.1f}% de la textura")

# Overlay magenta sobre version desaturada
gray_img = (np.stack([L, L, L], -1))
overlay = gray_img.copy()
overlay[mask] = overlay[mask]*0.25 + np.array([1.0, 0.0, 0.8])*0.75
Image.fromarray((overlay*255).astype(np.uint8)).resize((1024,1024)).save(OUT+r"\mask_overlay.png")

# Mascara binaria sola
Image.fromarray((mask*255).astype(np.uint8)).resize((1024,1024)).save(OUT+r"\mask_binary.png")
print("Guardado mask_overlay.png y mask_binary.png")
