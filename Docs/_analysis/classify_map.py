"""Mapa de clasificacion por categoria para validar las mascaras.
  magenta = recoloreable (gris uniforme+casco)
  verde   = oliva (chaleco)  -> DEBE preservarse
  azul    = negro (guantes/botas)
  amarillo= piel
  rojo    = naranja (cuello)
  gris    = sin clasificar
"""
import numpy as np
from PIL import Image

SRC = r"J:\Code\GreatSpadesTextures\Docs\blocky_humanoid_3d_model_basecolor.jpg"
OUT = r"J:\Code\GreatSpadesTextures\Docs\_analysis\classify_map.png"

im = Image.open(SRC).convert("RGB").resize((2048, 2048), Image.LANCZOS)
arr = np.asarray(im, dtype=np.float32)/255.0
R,G,B = arr[...,0],arr[...,1],arr[...,2]
mx=arr.max(-1); mn=arr.min(-1); V=mx; chroma=mx-mn
delta=np.where(chroma<1e-6,1.0,chroma)
rc=(mx-R)/delta; gc=(mx-G)/delta; bc=(mx-B)/delta
h=np.zeros_like(V); is_r=mx==R; is_g=(mx==G)&~is_r; is_b=(mx==B)&~is_r&~is_g
h[is_r]=(bc-gc)[is_r]; h[is_g]=(2+rc-bc)[is_g]; h[is_b]=(4+gc-rc)[is_b]
hue=(h/6.0)%1.0*360.0
S=np.where(mx>0,chroma/np.maximum(mx,1e-6),0)

black  = V < 0.14
gray   = (chroma < 0.07) & (V>=0.14) & (V<=0.80)
olive_like = (hue>=35)&(hue<=100)&(chroma>=0.045)
gray   = gray & ~olive_like
orange = (~black)&(hue>=5)&(hue<=33)&(S>0.5)&(V>0.4)
skin   = (~black)&(hue>=8)&(hue<=45)&(S>=0.18)&(S<=0.5)&(V>0.5)&~orange
olive  = (~black)&~gray&(hue>=33)&(hue<=105)&(chroma>=0.045)
assigned = black|gray|olive|skin|orange
other = ~assigned

out = np.stack([0.2126*R+0.7152*G+0.0722*B]*3,-1)  # luminancia base
def paint(m,c): out[m]=np.array(c,dtype=np.float32)
paint(gray,  [1.0,0.0,0.8])
paint(olive, [0.1,0.9,0.1])
paint(black, [0.1,0.2,1.0])
paint(skin,  [1.0,0.9,0.1])
paint(orange,[1.0,0.2,0.0])
# 'other' queda en luminancia

Image.fromarray((out*255).astype(np.uint8)).resize((1024,1024)).save(OUT)
tot=arr.shape[0]*arr.shape[1]
for n,m in [("gris",gray),("oliva",olive),("negro",black),("piel",skin),("naranja",orange),("otro",other)]:
    print(f"  {n:8s}: {100*m.sum()/tot:5.1f}%")
print("Guardado", OUT)
