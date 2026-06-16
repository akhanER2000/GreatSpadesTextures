"""Previsualiza el soldado recoloreado aplicando la tecnica de recoloreo a los
renders, excluyendo el fondo (flood fill desde los bordes)."""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from recolor import recolor_mask, recolor_region, feather_mask, resolve_color, load_palette

def background_mask(im, thresh=44):
    """Fondo via flood fill (PIL) desde el borde. El fondo es un degradado gris
    oscuro; el uniforme iluminado (mas claro) hace de muro. Deja un halo tenue
    en la zona central del degradado tras el soldado (aceptable en un preview)."""
    rgb = im.convert("RGB")
    flood = rgb.copy()
    W, H = rgb.size
    SENT = (255, 0, 255)
    seeds = [(0,0),(W-1,0),(0,H-1),(W-1,H-1),(W//2,0),(W//2,H-1),
             (0,H//2),(W-1,H//2),(W//4,0),(3*W//4,0)]
    for s in seeds:
        ImageDraw.floodfill(flood, s, SENT, thresh=thresh)
    fa = np.asarray(flood)
    return np.all(fa == np.array(SENT), axis=-1)

def recolor_render(im, color_token, thresh=44):
    pal = load_palette()
    target = resolve_color(color_token, pal)
    arr = np.asarray(im.convert("RGB"), dtype=np.float32)/255.0
    gray = recolor_mask(arr)                 # gris (incluye fondo gris)
    bg = background_mask(im, thresh=thresh)   # fondo
    region = gray & ~bg
    alpha = feather_mask(region, 1.0)
    out = recolor_region(arr, alpha, target, contrast=1.0)
    return Image.fromarray((out*255+0.5).astype(np.uint8))

def montage(render_path, specs, out_path, thresh=44, cell=300, pad=10, label_h=26):
    """specs = [(etiqueta, color), ...]; incluye el original al principio."""
    from PIL import ImageFont
    base = Image.open(render_path).convert("RGB")
    tiles = [("original", None)] + specs
    imgs = []
    for label, color in tiles:
        im = base if color is None else recolor_render(base, color, thresh)
        t = im.copy(); t.thumbnail((cell, cell))
        imgs.append((label, t))
    cols = min(4, len(imgs))
    rows = (len(imgs)+cols-1)//cols
    cw = cell+pad; ch = cell+label_h+pad
    canvas = Image.new("RGB", (cols*cw+pad, rows*ch+pad), (28,28,32))
    d = ImageDraw.Draw(canvas)
    for i,(label,t) in enumerate(imgs):
        r,c = divmod(i, cols)
        x = pad + c*cw + (cell-t.size[0])//2
        y = pad + r*ch + (cell-t.size[1])//2
        canvas.paste(t, (x, y))
        d.text((pad + c*cw + 4, pad + r*ch + cell + 4), label, fill=(220,220,225))
    canvas.save(out_path)
    print("montaje ->", out_path)

if __name__ == "__main__":
    render = sys.argv[1] if len(sys.argv)>1 else r"Docs\Captura de pantalla 2026-06-16 013109.png"
    specs = [("azul_marino","#1b2f5e"), ("verde_bosque","#2f4a22"),
             ("rojo_sangre","#7a1f1f"), ("arena","#9c8862"),
             ("morado","#3d2a55"), ("gris_urbano","#3a4048"),
             ("negro_tactico","#1a1a1c")]
    montage(render, specs, r"Docs\_analysis\soldado_variaciones.png")
