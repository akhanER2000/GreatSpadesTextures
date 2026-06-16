# -*- coding: utf-8 -*-
import sys; sys.path.insert(0, r'J:\Code\GreatSpadesTextures')
from bake_regions import load_geom
import numpy as np
from PIL import Image
TEX=r'J:\Code\GreatSpadesTextures\app\assets\texture_2048.jpg'
img=np.asarray(Image.open(TEX).convert('RGB'),np.float32)/255.;H,W=img.shape[:2]
meshes,_,_=load_geom()
def hsv(rgb):
    r,g,b=rgb[...,0],rgb[...,1],rgb[...,2];mx=rgb.max(-1);mn=rgb.min(-1);V=mx;ch=mx-mn
    S=np.where(mx>1e-6,ch/np.maximum(mx,1e-6),0.);d=np.where(ch<1e-6,1.,ch)
    rc=(mx-r)/d;gc=(mx-g)/d;bc=(mx-b)/d;h=np.zeros_like(V)
    ir=mx==r;ig=(mx==g)&~ir;ib=(mx==b)&~ir&~ig
    h[ir]=(bc-gc)[ir];h[ig]=(2+rc-bc)[ig];h[ib]=(4+gc-rc)[ib]
    return (h/6)%1*360,S,V,ch
def sample(uv):
    x=np.clip(uv[:,0]*(W-1),0,W-1).astype(np.int32);y=np.clip((1-uv[:,1])*(H-1),0,H-1).astype(np.int32)
    return img[y,x]
def tri_pts(uv,idx):
    a=uv[idx[:,0]];b=uv[idx[:,1]];c=uv[idx[:,2]];cen=(a+b+c)/3
    mab=(a+b)/2;mbc=(b+c)/2;mca=(c+a)/2
    extra=[(cen+a)/2,(cen+b)/2,(cen+c)/2,(cen+mab)/2,(cen+mbc)/2,(cen+mca)/2]
    return np.stack([cen,a,b,c,mab,mbc,mca]+extra,axis=1)
m=meshes[5];uv=m['uv'];idx=m['idx']
pts=tri_pts(uv,idx);nT=pts.shape[0]
rgb=sample(pts.reshape(-1,2)).reshape(nT,pts.shape[1],3)
hue,S,V,ch=hsv(rgb)  # (nT,13)
# Mediana por triangulo (robusta) de hue/chroma sobre los puntos no-negros
mask_nb=V>=0.14
med_ch=np.array([np.median(ch[i][mask_nb[i]]) if mask_nb[i].any() else 0 for i in range(nT)])
med_hue=np.array([np.median(hue[i][mask_nb[i]]) if mask_nb[i].any() else 0 for i in range(nT)])
med_V=np.median(V,1)
# triangulos cuya MEDIANA cae en oliva debil: hue 30-115, chroma 0.03-0.06
weak=(med_hue>=30)&(med_hue<=115)&(med_ch>=0.025)&(med_ch<0.06)
strong=(med_hue>=30)&(med_hue<=115)&(med_ch>=0.06)
graygenuine=(med_ch<0.025)
print(f'TORSO nTri={nT}')
print(f'  oliva fuerte (med_ch>=0.06, hue30-115): {strong.sum()} ({100*strong.mean():.1f}%)')
print(f'  oliva debil  (med_ch 0.025-0.06):       {weak.sum()} ({100*weak.mean():.1f}%)')
print(f'  gris genuino (med_ch<0.025):            {graygenuine.sum()} ({100*graygenuine.mean():.1f}%)')
# de la zona debil, ¿el color es verdoso (g>b y g>=r aprox)? -> tela oliva oscura
cen=rgb[:,0,:]
g_gt_b=(cen[:,1]>=cen[:,2])  # verde >= azul
g_ge_r=(cen[:,1]>=cen[:,0]-0.01)
oliveish_weak=weak & g_gt_b
print(f'  de la oliva debil, con G>=B (tono oliva real): {oliveish_weak.sum()}')
# Caracteriza color medio de cada grupo
for nm,sel in [('fuerte',strong),('debil',weak),('gris',graygenuine)]:
    if sel.sum():
        c=cen[sel].mean(0)
        print(f'  color medio {nm}: RGB=({c[0]:.2f},{c[1]:.2f},{c[2]:.2f}) hue_med={np.median(med_hue[sel]):.0f} ch_med={np.median(med_ch[sel]):.3f}')
