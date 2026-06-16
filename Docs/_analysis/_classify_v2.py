# -*- coding: utf-8 -*-
"""Clasificador FINAL por triangulo, mesh-scoped. Solo lectura."""
import sys; sys.path.insert(0, r'J:\Code\GreatSpadesTextures')
from bake_regions import load_geom
import numpy as np
from PIL import Image
TEX=r'J:\Code\GreatSpadesTextures\app\assets\texture_2048.jpg'
img=np.asarray(Image.open(TEX).convert('RGB'),np.float32)/255.;H,W=img.shape[:2]
meshes,gmin,gmax=load_geom()

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
def tri_pos(pos,idx): return (pos[idx[:,0]]+pos[idx[:,1]]+pos[idx[:,2]])/3

# IDs FINALES: 0 piel,1 uniforme,2 chaleco,3 botas,4 cuello,6 guantes,7 correa-bloq
def classify_region(k, m):
    uv,idx,pos=m['uv'],m['idx'],m['pos']
    pts=tri_pts(uv,idx);nT=pts.shape[0]
    rgb=sample(pts.reshape(-1,2)).reshape(nT,pts.shape[1],3)
    hue,S,V,ch=hsv(rgb); nb=V>=0.14
    def med(a): return np.array([np.median(a[i][nb[i]]) if nb[i].any() else 0. for i in range(nT)])
    mh=med(hue);mc=med(ch);ms=med(S);mv=np.median(V,1)
    cen=rgb[:,0,:]; warm=cen[:,1]>=cen[:,2]-0.005
    fb=(V<0.14).mean(1)               # fraccion oscura
    tp=tri_pos(pos,idx); yc=tp[:,1]
    is_torso=(k==5); is_head=(k==6); is_limb=(k in(1,2,4))
    reg=np.full(nT,1,np.int8)         # default uniforme(1)

    # NEGRO: mayoria oscura Y (neutro/frio  o  no-torso)  -> botas/guantes/correa
    dark=fb>=0.5
    if is_torso:
        dark_black = dark & (~warm)    # solo oscuro-neutro = correa/strap
    else:
        dark_black = dark              # en miembros/cabeza, oscuro = negro real

    # OLIVA (solo TORSO): hue 30-118 & (ch>=0.06  o  ch>=0.025&warm) ; o dark&warm (sombra oliva)
    olive=np.zeros(nT,bool)
    if is_torso:
        olive=((mh>=30)&(mh<=118)&((mc>=0.06)|((mc>=0.025)&warm))) | (dark&warm)
    # CUELLO/naranja (solo TORSO o CABEZA, parte alta): hue 5-33 S>0.45 V>0.4 y>0.78
    orange=np.zeros(nT,bool)
    if is_torso or is_head:
        orange=(mh>=5)&(mh<=33)&(ms>0.45)&(mv>0.4)&(yc>0.78)
    # PIEL (cabeza/detalles): hue 8-45 S 0.18-0.55 V>0.5, sin olive
    skin=(mh>=8)&(mh<=45)&(ms>=0.18)&(ms<=0.55)&(mv>0.5)&~olive

    # Asignacion por prioridad: oliva>naranja>piel>negro>uniforme
    reg[dark_black]=7 if is_torso else (3 if is_limb and k==1 else (6 if is_limb else 7))
    # corregir: piernas->botas(3), brazos->guantes(6), torso->correa(7), cabeza/det->correa(7)
    if is_limb:
        reg[dark_black & (k==1)]=3   # botas
        reg[dark_black & (k!=1)]=6   # guantes
    elif is_torso:
        reg[dark_black]=7            # correa barbilla/strap (bloq)
    else:
        reg[dark_black]=7
    reg[skin]=0
    reg[orange]=4
    reg[olive]=2
    return reg

NAMES={0:'piel',1:'uniforme',2:'chaleco',3:'botas',4:'cuello',6:'guantes',7:'correa'}
PAL={0:(255,255,0),1:(255,0,255),2:(0,200,0),3:(0,128,255),4:(255,0,0),6:(0,0,255),7:(255,128,0)}
def raster(uv,idx,reg,res,canvas):
    px=uv[:,0]*(res-1);py=(1-uv[:,1])*(res-1);P=np.stack([px,py],-1)
    for t in range(idx.shape[0]):
        a,b,c=idx[t];pa,pb,pc=P[a],P[b],P[c]
        mnx=int(max(0,np.floor(min(pa[0],pb[0],pc[0]))));mxx=int(min(res-1,np.ceil(max(pa[0],pb[0],pc[0]))))
        mny=int(max(0,np.floor(min(pa[1],pb[1],pc[1]))));mxy=int(min(res-1,np.ceil(max(pa[1],pb[1],pc[1]))))
        if mxx<mnx or mxy<mny:continue
        gx,gy=np.meshgrid(np.arange(mnx,mxx+1),np.arange(mny,mxy+1))
        d=((pb[1]-pc[1])*(pa[0]-pc[0])+(pc[0]-pb[0])*(pa[1]-pc[1]))
        if abs(d)<1e-9:continue
        w1=((pb[1]-pc[1])*(gx-pc[0])+(pc[0]-pb[0])*(gy-pc[1]))/d
        w2=((pc[1]-pa[1])*(gx-pc[0])+(pa[0]-pc[0])*(gy-pc[1]))/d
        w3=1-w1-w2;ins=(w1>=-0.01)&(w2>=-0.01)&(w3>=-0.01)
        canvas[gy[ins],gx[ins]]=PAL[int(np.bincount(reg).argmax()) if False else 0]  # placeholder
    return canvas

# raster correcto por triangulo
def raster2(uv,idx,reg,res,canvas):
    px=uv[:,0]*(res-1);py=(1-uv[:,1])*(res-1);P=np.stack([px,py],-1)
    for t in range(idx.shape[0]):
        a,b,c=idx[t];pa,pb,pc=P[a],P[b],P[c]
        mnx=int(max(0,np.floor(min(pa[0],pb[0],pc[0]))));mxx=int(min(res-1,np.ceil(max(pa[0],pb[0],pc[0]))))
        mny=int(max(0,np.floor(min(pa[1],pb[1],pc[1]))));mxy=int(min(res-1,np.ceil(max(pa[1],pb[1],pc[1]))))
        if mxx<mnx or mxy<mny:continue
        gx,gy=np.meshgrid(np.arange(mnx,mxx+1),np.arange(mny,mxy+1))
        d=((pb[1]-pc[1])*(pa[0]-pc[0])+(pc[0]-pb[0])*(pa[1]-pc[1]))
        if abs(d)<1e-9:continue
        w1=((pb[1]-pc[1])*(gx-pc[0])+(pc[0]-pb[0])*(gy-pc[1]))/d
        w2=((pc[1]-pa[1])*(gx-pc[0])+(pa[0]-pc[0])*(gy-pc[1]))/d
        w3=1-w1-w2;ins=(w1>=-0.01)&(w2>=-0.01)&(w3>=-0.01)
        canvas[gy[ins],gx[ins]]=PAL[int(reg[t])]
    return canvas

mesh_part={0:'detalle',1:'PIERNAS',2:'BRAZO-tras',3:'detalle',4:'BRAZO-del',5:'TORSO',6:'CABEZA'}
res=1024; canvas=np.zeros((res,res,3),np.uint8)
print('=== RECUENTOS POR MALLA -> REGION FINAL (clasificador v2 mesh-scoped) ===')
allreg={}
for k,m in enumerate(meshes):
    reg=classify_region(k,m);allreg[k]=reg;nT=len(reg)
    canvas=raster2(m['uv'],m['idx'],reg,res,canvas)
    line=f'k={k} {mesh_part[k]:10s} nTri={nT:5d} |'
    for rid in [1,2,3,4,6,7,0]:
        c=int((reg==rid).sum())
        if c: line+=f' {NAMES[rid]}={c}({100*c/nT:.0f}%)'
    print(line)
Image.fromarray(canvas).save(r'Docs\_analysis\regionmap_v2.png')
cvt=np.zeros((res,res,3),np.uint8);cvt=raster2(meshes[5]['uv'],meshes[5]['idx'],allreg[5],res,cvt)
Image.fromarray(cvt).save(r'Docs\_analysis\regionmap_v2_torso.png')
print('\nguardado regionmap_v2.png y regionmap_v2_torso.png')
