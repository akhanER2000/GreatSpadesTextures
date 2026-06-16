# -*- coding: utf-8 -*-
import sys; sys.path.insert(0, r'J:\Code\GreatSpadesTextures')
from bake_regions import load_geom
import numpy as np
from PIL import Image

TEX = r'J:\Code\GreatSpadesTextures\app\assets\texture_2048.jpg'
img = np.asarray(Image.open(TEX).convert('RGB'), np.float32) / 255.0
H, W = img.shape[:2]
meshes, gmin, gmax = load_geom()

def hsv(rgb):
    r,g,b=rgb[...,0],rgb[...,1],rgb[...,2]
    mx=rgb.max(-1);mn=rgb.min(-1);V=mx;ch=mx-mn
    S=np.where(mx>1e-6,ch/np.maximum(mx,1e-6),0.)
    d=np.where(ch<1e-6,1.,ch);rc=(mx-r)/d;gc=(mx-g)/d;bc=(mx-b)/d
    h=np.zeros_like(V);ir=mx==r;ig=(mx==g)&~ir;ib=(mx==b)&~ir&~ig
    h[ir]=(bc-gc)[ir];h[ig]=(2+rc-bc)[ig];h[ib]=(4+gc-rc)[ib]
    return (h/6)%1*360,S,V,ch

def sample(uv):
    x=np.clip(uv[:,0]*(W-1),0,W-1).astype(np.int32)
    y=np.clip((1-uv[:,1])*(H-1),0,H-1).astype(np.int32)
    return img[y,x]

def tri_pts(uv,idx):
    a=uv[idx[:,0]];b=uv[idx[:,1]];c=uv[idx[:,2]]
    cen=(a+b+c)/3;mab=(a+b)/2;mbc=(b+c)/2;mca=(c+a)/2
    # 13 puntos: centroide + 3 vert + 3 medios + 6 puntos a 1/3,2/3 hacia centroide
    extra=[(cen+a)/2,(cen+b)/2,(cen+c)/2,(cen+mab)/2,(cen+mbc)/2,(cen+mca)/2]
    return np.stack([cen,a,b,c,mab,mbc,mca]+extra,axis=1)

def tri_pos(pos,idx):
    return (pos[idx[:,0]]+pos[idx[:,1]]+pos[idx[:,2]])/3

# === Funcion candidata de clasificacion ===
def classify(rgb, OL_HUE=(30,115), OL_CH=0.05, V_BLACK=0.14):
    hue,S,V,ch=hsv(rgb)
    black=V<V_BLACK
    olive=(~black)&(hue>=OL_HUE[0])&(hue<=OL_HUE[1])&(ch>=OL_CH)
    skin=(~black)&(hue>=8)&(hue<=45)&(S>=0.18)&(S<=0.55)&(V>0.5)&(ch<OL_CH if False else ~olive)
    orange=(~black)&(hue>=5)&(hue<=33)&(S>0.5)&(V>0.4)
    code=np.ones(rgb.shape[:-1],np.int8)
    code[olive]=2; code[skin]=0; code[orange]=4; code[black]=3
    return code

def dominant(code):
    # voto; empate -> prioridad oliva>negro>naranja>piel>gris para no perder chaleco
    out=np.zeros(code.shape[0],np.int8)
    prio={2:0,3:1,4:2,0:3,1:4}
    for i in range(code.shape[0]):
        vals,cnts=np.unique(code[i],return_counts=True)
        mx=cnts.max()
        cand=[v for v,c in zip(vals,cnts) if c==mx]
        out[i]=min(cand,key=lambda v:prio[v])
    return out

m=meshes[5]; uv=m['uv']; idx=m['idx']; pos=m['pos']
pts=tri_pts(uv,idx); nT=pts.shape[0]
rgb=sample(pts.reshape(-1,2)).reshape(nT,pts.shape[1],3)
tp=tri_pos(pos,idx)  # (nT,3) centroide 3D

# Barrido de OL_CH para ver cobertura del chaleco
hC,sC,vC,chC=hsv(rgb[:,0,:])
print('=== TORSO barrido umbral OL_CH (hue 30..115) ===')
print(' OL_CH   oliva%  gris%  negro%  naranja%')
for olch in [0.03,0.035,0.04,0.045,0.05,0.06,0.07]:
    code=classify(rgb,OL_CH=olch); dom=dominant(code)
    print(f' {olch:.3f}  {100*(dom==2).mean():6.1f} {100*(dom==1).mean():6.1f} {100*(dom==3).mean():6.1f} {100*(dom==4).mean():7.1f}')

# Elegir OL_CH=0.045 y analizar los triangulos GRIS: cuantos tienen ALGUN pt oliva (chaleco fugado)
code=classify(rgb,OL_CH=0.045); dom=dominant(code)
gray=dom==1
# de los grises, fraccion de puntos que son oliva
ol_pts=(code==2)
frac_ol=ol_pts.mean(1)
sus=gray & (frac_ol>0.15)
print(f'\nGrises totales: {gray.sum()}; de ellos con >15% puntos oliva (posible chaleco fugado): {sus.sum()}')

# Posicion 3D: el chaleco/mochila esta en z extremos (frente/espalda) y parte central. gris jacket en hombros/mangas-torso
# Analizamos rango z normalizado de oliva vs gris
zc=tp[:,2]
print(f'\nz centroide: oliva p10={np.percentile(zc[dom==2],10):+.3f} p50={np.percentile(zc[dom==2],50):+.3f} p90={np.percentile(zc[dom==2],90):+.3f}')
print(f'z centroide: gris  p10={np.percentile(zc[gray],10):+.3f} p50={np.percentile(zc[gray],50):+.3f} p90={np.percentile(zc[gray],90):+.3f}')

np.save(r'Docs\_analysis\_torso_dom.npy', dom)
np.save(r'Docs\_analysis\_torso_tp.npy', tp)
