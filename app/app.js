// =============================================================================
//  Editor del Soldado — visor 3D + recoloreado por región (GreatSpades)
//  - three.js carga el FBX y aplica la textura base.
//  - Un shader (inyectado en MeshStandardMaterial) recolorea cada región
//    preservando la LUMINANCIA (detalle de tela): mismo método Lab que el
//    motor Python -> L_new = L_target + (L_base - meanL_region); (a,b)=target.
//  - La PIEL (región 0) nunca se toca.
// =============================================================================
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';

// ---- Definición de piezas (id de región en el mapa) -------------------------
// ids: 1=uniforme 2=chaleco 3=botas 4=cuello 5=casco 6=guantes
// (0=piel y 7=correa de barbilla quedan BLOQUEADOS: nunca se recolorean)
const PARTS = [
  { id:5, name:'Casco',    sub:'tela / acero', color:'#5a5f66', on:false },
  { id:1, name:'Uniforme', sub:'tela',         color:'#2f4f86', on:false },
  { id:2, name:'Chaleco',  sub:'táctico',      color:'#3c4a23', on:false },
  { id:6, name:'Guantes',  sub:'',             color:'#1d1d22', on:false },
  { id:3, name:'Botas',    sub:'',             color:'#202026', on:false },
  { id:4, name:'Cuello',   sub:'detalle',      color:'#8a3b1f', on:false },
];
const partById = Object.fromEntries(PARTS.map(p=>[p.id,p]));
const NREG = 8;  // ids 0..7

// ---- Lab en JS (sRGB -> linear -> XYZ -> Lab) para el color objetivo --------
const srgb2lin = c => c<=0.04045 ? c/12.92 : Math.pow((c+0.055)/1.055,2.4);
function hexToLinRGB(hex){
  const h=hex.replace('#',''); const n=parseInt(h.length===3?h.split('').map(c=>c+c).join(''):h,16);
  return [ srgb2lin(((n>>16)&255)/255), srgb2lin(((n>>8)&255)/255), srgb2lin((n&255)/255) ];
}
function linRGBtoXYZ([r,g,b]){
  return [ 0.4124564*r+0.3575761*g+0.1804375*b,
           0.2126729*r+0.7151522*g+0.0721750*b,
           0.0193339*r+0.1191920*g+0.9503041*b ];
}
function xyzToLab([X,Y,Z]){
  const w=[0.95047,1.0,1.08883]; const f=t=> t>0.008856 ? Math.cbrt(t) : (7.787*t+16/116);
  const fx=f(X/w[0]), fy=f(Y/w[1]), fz=f(Z/w[2]);
  return [116*fy-16, 500*(fx-fy), 200*(fy-fz)];
}
const hexToLab = hex => xyzToLab(linRGBtoXYZ(hexToLinRGB(hex)));

// ---- Uniforms compartidos por el material -----------------------------------
const U = {
  uActive:    { value: new Array(NREG).fill(0) },
  uMeanL:     { value: new Array(NREG).fill(0) },
  uTargetLab: { value: Array.from({length:NREG}, ()=>new THREE.Vector3()) },
};
let regionTex = null;

// ---- Escena -----------------------------------------------------------------
const viewer = document.getElementById('viewer');
const renderer = new THREE.WebGLRenderer({ antialias:true, alpha:true, preserveDrawingBuffer:true });
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.setClearColor(0x000000, 0);   // transparente -> se ve el degradado CSS
viewer.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const pivot = new THREE.Group(); scene.add(pivot);   // gira el pivote, no el modelo
const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 100);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.12;

scene.add(new THREE.AmbientLight(0xffffff, 1.05));
const key = new THREE.DirectionalLight(0xffffff, 1.7); key.position.set(3,5,4); scene.add(key);
const fill = new THREE.DirectionalLight(0xbcd2ff, 0.5); fill.position.set(-4,1,-3); scene.add(fill);
const back = new THREE.DirectionalLight(0xffffff, 0.5); back.position.set(0,3,-5); scene.add(back);

let scheduled=false;
function requestRender(){ if(scheduled)return; scheduled=true;
  requestAnimationFrame(()=>{ scheduled=false; controls.update(); renderer.render(scene,camera); }); }
controls.addEventListener('change', requestRender);

function resize(){ const w=viewer.clientWidth, h=viewer.clientHeight;
  if(w===0||h===0) return;
  renderer.setSize(w,h); camera.aspect=w/h; camera.updateProjectionMatrix(); requestRender(); }
addEventListener('resize', resize);

// ---- Material con recoloreado inyectado -------------------------------------
function makeMaterial(baseTex){
  const mat = new THREE.MeshStandardMaterial({ map:baseTex, roughness:0.92, metalness:0.0 });
  mat.onBeforeCompile = (shader)=>{
    shader.uniforms.uRegion    = { value: regionTex };
    shader.uniforms.uActive    = U.uActive;
    shader.uniforms.uMeanL     = U.uMeanL;
    shader.uniforms.uTargetLab = U.uTargetLab;
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform sampler2D uRegion;
        uniform float uActive[8];
        uniform float uMeanL[8];
        uniform vec3  uTargetLab[8];
        vec3 _lin2xyz(vec3 c){ return vec3(
          dot(c,vec3(0.4124564,0.3575761,0.1804375)),
          dot(c,vec3(0.2126729,0.7151522,0.0721750)),
          dot(c,vec3(0.0193339,0.1191920,0.9503041))); }
        float _f(float t){ return t>0.008856 ? pow(t,1.0/3.0) : (7.787*t+16.0/116.0); }
        vec3 _xyz2lab(vec3 x){ vec3 w=vec3(0.95047,1.0,1.08883);
          vec3 f=vec3(_f(x.x/w.x),_f(x.y/w.y),_f(x.z/w.z));
          return vec3(116.0*f.y-16.0, 500.0*(f.x-f.y), 200.0*(f.y-f.z)); }
        float _fi(float t){ float d=6.0/29.0; return t>d ? t*t*t : 3.0*d*d*(t-4.0/29.0); }
        vec3 _lab2xyz(vec3 l){ float fy=(l.x+16.0)/116.0, fx=fy+l.y/500.0, fz=fy-l.z/200.0;
          vec3 w=vec3(0.95047,1.0,1.08883); return vec3(_fi(fx)*w.x,_fi(fy)*w.y,_fi(fz)*w.z); }
        vec3 _xyz2lin(vec3 x){ return vec3(
          dot(x,vec3( 3.2404542,-1.5371385,-0.4985314)),
          dot(x,vec3(-0.9692660, 1.8760108, 0.0415560)),
          dot(x,vec3( 0.0556434,-0.2040259, 1.0572252))); }
        vec3 recolor(vec3 linRGB, int id){
          vec3 lab=_xyz2lab(_lin2xyz(linRGB));
          vec3 t=uTargetLab[id];
          float Ln=clamp(t.x+(lab.x-uMeanL[id]),0.0,100.0);
          return clamp(_xyz2lin(_lab2xyz(vec3(Ln,t.y,t.z))),0.0,1.0);
        }`)
      .replace('#include <map_fragment>', `#include <map_fragment>
        #ifdef USE_MAP
          int _rid = int(floor(texture2D(uRegion, vMapUv).r*255.0 + 0.5));
          if(_rid>=1 && _rid<=6 && uActive[_rid]>0.5){
            diffuseColor.rgb = recolor(diffuseColor.rgb, _rid);
          }
        #endif`);
    mat.userData.shader = shader;
  };
  return mat;
}

// ---- Encadre del modelo -----------------------------------------------------
let model=null, modelHome={maxDim:1};
function frame(obj){
  obj.updateMatrixWorld(true);
  const box=new THREE.Box3().setFromObject(obj);
  const size=box.getSize(new THREE.Vector3());
  const center=box.getCenter(new THREE.Vector3());
  obj.position.sub(center);                       // centra el modelo en el origen del pivote
  const maxDim=Math.max(size.x,size.y,size.z)||1;
  modelHome.maxDim=maxDim;
  camera.near=maxDim/100; camera.far=maxDim*100; camera.updateProjectionMatrix();
  resetView();
}
function resetView(){
  const d=modelHome.maxDim;
  pivot.rotation.set(0,0,0);                       // resetea el pivote (NO la orientación del modelo)
  camera.position.set(0, d*0.10, d*1.6);           // cámara recta en +Z, ligeramente arriba
  controls.target.set(0,0,0); controls.update(); requestRender();
}

// ---- Carga de activos -------------------------------------------------------
const statusEl=document.getElementById('status');
const setStatus=(m,c='')=>{ statusEl.textContent=m; statusEl.className=c; };

async function init(){
  const meta = await fetch('assets/regions_meta.json').then(r=>r.json());
  for(const [id,info] of Object.entries(meta.regions)) U.uMeanL.value[+id]=info.meanL;

  const texLoader=new THREE.TextureLoader();
  const baseTex = await texLoader.loadAsync('assets/texture_2048.jpg');
  baseTex.colorSpace=THREE.SRGBColorSpace; baseTex.flipY=true;
  baseTex.anisotropy = renderer.capabilities.getMaxAnisotropy();

  regionTex = await texLoader.loadAsync('assets/regions_2048.png');
  regionTex.colorSpace=THREE.NoColorSpace; regionTex.flipY=true;
  regionTex.magFilter=THREE.NearestFilter; regionTex.minFilter=THREE.NearestFilter;
  regionTex.generateMipmaps=false;

  const mat = makeMaterial(baseTex);

  const loader=new FBXLoader();
  loader.load('assets/model.fbx', (obj)=>{
    obj.traverse(c=>{ if(c.isMesh){ c.material=mat; c.castShadow=false; } });
    model=obj; pivot.add(obj);
    resize();          // primero fija el aspecto correcto del canvas
    frame(obj);        // luego encuadra con ese aspecto
    document.getElementById('loading').style.display='none';
    setStatus(`Modelo cargado · ${PARTS.length} piezas recoloreables`, 'ok');
  }, undefined, (err)=>{ document.getElementById('loading').textContent='Error al cargar el modelo'; console.error(err); });

  buildPanel();
}

// ---- Aplicar colores a los uniforms -----------------------------------------
function applyPart(p){
  U.uActive.value[p.id] = p.on ? 1 : 0;
  const [L,a,b]=hexToLab(p.color);
  U.uTargetLab.value[p.id].set(L,a,b);
  if(model){ model.traverse(c=>{ if(c.isMesh) c.material.needsUpdate=false; }); }
  requestRender();
}

// ---- Panel ------------------------------------------------------------------
function buildPanel(){
  const wrap=document.getElementById('parts');
  for(const p of PARTS){
    const card=document.createElement('div');
    card.className='part'+(p.on?' on':'');
    card.innerHTML=`
      <div class="part-top">
        <input type="checkbox" class="toggle" ${p.on?'checked':''} data-id="${p.id}">
        <div class="name">${p.name} <span class="sub">· ${p.sub}</span></div>
        <input type="color" class="swatch" value="${p.color}" data-id="${p.id}">
      </div>
      <div class="row2">
        <span class="hexlabel" id="hex-${p.id}">${p.color}</span>
        <button class="mini" data-reset="${p.id}">Quitar</button>
      </div>`;
    wrap.appendChild(card);

    const toggle=card.querySelector('.toggle');
    const swatch=card.querySelector('.swatch');
    const hex=card.querySelector('.hexlabel');
    toggle.addEventListener('change',()=>{ p.on=toggle.checked; card.classList.toggle('on',p.on); applyPart(p); });
    swatch.addEventListener('input',()=>{ p.color=swatch.value; hex.textContent=swatch.value;
      if(!p.on){ p.on=true; toggle.checked=true; card.classList.add('on'); } applyPart(p); });
    card.querySelector('[data-reset]').addEventListener('click',()=>{ p.on=false; toggle.checked=false;
      card.classList.remove('on'); applyPart(p); });
  }
  // tarjeta de piel bloqueada
  const lock=document.createElement('div');
  lock.className='part locked';
  lock.innerHTML=`<div class="part-top"><div class="name">Piel, cara y correa <span class="sub">· protegidas</span></div>🔒</div>
    <div class="lockbadge">🔒 La piel/cara y la correa metálica de la barbilla nunca se recolorean</div>`;
  wrap.appendChild(lock);
}

// ---- Toolbar y acciones -----------------------------------------------------
let autoRotate=false, rafLoop=null;
document.getElementById('btnReset').onclick=resetView;
document.getElementById('btnAuto').onclick=(e)=>{
  autoRotate=!autoRotate; e.target.style.color=autoRotate?'#5b9dff':'';
  if(autoRotate && !rafLoop){
    const tick=()=>{ if(!autoRotate){rafLoop=null;return;} pivot.rotation.y+=0.012;
      controls.update(); renderer.render(scene,camera); rafLoop=requestAnimationFrame(tick); };
    rafLoop=requestAnimationFrame(tick);
  }
};
document.getElementById('btnResetAll').onclick=()=>{
  for(const p of PARTS){ p.on=false; }
  document.querySelectorAll('.toggle').forEach(t=>t.checked=false);
  document.querySelectorAll('.part').forEach(c=>c.classList.remove('on'));
  for(const p of PARTS) applyPart(p);
  setStatus('Restablecido','');
};
document.getElementById('btnExport').onclick=exportTexture;

async function exportTexture(){
  const colors={};
  for(const p of PARTS) if(p.on) colors[p.id]=p.color;
  if(Object.keys(colors).length===0){ setStatus('Activa al menos una pieza para exportar','err'); return; }
  const hasApi = window.pywebview && window.pywebview.api && window.pywebview.api.export_texture;
  if(!hasApi){ setStatus('La exportación 8192² requiere la app de escritorio (.exe)','err'); return; }
  setStatus('Exportando a 8192²… puede tardar ~25 s','');
  document.getElementById('btnExport').disabled=true;
  try{
    const res = await window.pywebview.api.export_texture(colors);
    setStatus('Guardado: '+res, 'ok');
  }catch(err){ setStatus('Error al exportar: '+err, 'err'); }
  finally{ document.getElementById('btnExport').disabled=false; }
}

init();
