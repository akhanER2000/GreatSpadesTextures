# -*- coding: utf-8 -*-
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

# === CLASIFICADOR FINAL POR TRIANGULO ===
# Devuelve color dominante: 0 piel,1 gris/uniforme,2 oliva,3 negro,4 naranja
def classify_tri(uv, idx, mesh_is_torso, pos=None):
    pts=tri_pts(uv,idx); nT=pts.shape[0]
    rgb=sample(pts.reshape(-1,2)).reshape(nT,pts.shape[1],3)
    hue,S,V,ch=hsv(rgb)
    nb=V>=0.14
    def med(a):
        return np.array([np.median(a[i][nb[i]]) if nb[i].any() else 0. for i in range(nT)])
    mh=med(hue); mc=med(ch); mv=np.median(V,1); ms=med(S)
    cen=rgb[:,0,:]; warm=cen[:,1]>=cen[:,2]-0.005  # G>=B (oliva calido)
    frac_black=(V<0.14).mean(1)
    code=np.ones(nT,np.int8)
    # OLIVA: hue 30-118 & ( ch>=0.06  OR  (ch>=0.025 & warm) )
    olive=(mh>=30)&(mh<=118)&((mc>=0.06)|((mc>=0.025)&warm))
    # NEGRO: mayoria de puntos oscuros
    black=frac_black>=0.5
    # NARANJA/CUELLO: solo si torso & hue 5-33 & S alto & V alto & parte ALTA (y>0.78)
    orange=np.zeros(nT,bool)
    if mesh_is_torso and pos is not None:
        tp=tri_pos(pos,idx); yc=tp[:,1]
        orange=(mh>=5)&(mh<=33)&(ms>0.45)&(mv>0.4)&(yc>0.78)
    skin=(mh>=8)&(mh<=45)&(ms>=0.18)&(ms<=0.55)&(mv>0.5)&~olive
    code[olive]=2; code[skin]=0; code[orange]=4; code[black]=3
    return code, dict(mh=mh,mc=mc,mv=mv,ms=ms)

pal={0:(255,255,0),1:(255,0,255),2:(0,200,0),3:(0,0,255),4:(255,0,0)}
def raster(uv,idx,codes,res):
    cv=np.zeros((res,res,3),np.uint8)
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
        cv[gy[ins],gx[ins]]=pal[codes[t]]
    return cv

names={0:'piel',1:'uniforme',2:'oliva/chaleco',3:'negro',4:'naranja/cuello'}
res=1024
canvas=np.zeros((res,res,3),np.uint8)
report={}
for k,m in enumerate(meshes):
    is_torso=(k==5)
    code,_=classify_tri(m['uv'],m['idx'],is_torso,m['pos'])
    report[k]=code
    cv=raster(m['uv'],m['idx'],code,res)
    canvas=np.maximum(canvas,cv)
Image.fromarray(canvas).save(r'Docs\_analysis\classmap_all.png')
# torso solo
cvt=raster(meshes[5]['uv'],meshes[5]['idx'],report[5],res)
Image.fromarray(cvt).save(r'Docs\_analysis\classmap_torso.png')

print('=== RECUENTOS POR MALLA (clasificador final) ===')
mesh_part={0:'detalle',1:'PIERNAS',2:'BRAZO-tras',3:'detalle',4:'BRAZO-del',5:'TORSO',6:'CABEZA'}
for k,m in enumerate(meshes):
    code=report[k];nT=len(code)
    cnt={v:int((code==v).sum()) for v in range(5)}
    pct={v:100*cnt[v]/nT for v in range(5)}
    print(f'k={k} {mesh_part[k]:10s} nTri={nT:5d} | gris {pct[1]:5.1f}% oliva {pct[2]:5.1f}% negro {pct[3]:5.1f}% naranja {pct[4]:5.1f}% piel {pct[0]:5.1f}%')
print('\nguardado classmap_all.png y classmap_torso.png')
