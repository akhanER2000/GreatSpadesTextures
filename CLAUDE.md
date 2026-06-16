# GreatSpadesTextures — Recoloreado de uniforme/casco del soldado voxel

## Qué es este proyecto
Pipeline para generar **variaciones de color** del soldado voxel (modelo
generado con Tripo AI) cambiando **únicamente el color del uniforme y del
casco** (la zona gris), **preservando todos los detalles de la tela**
(trama, costuras, dibujos, bolsillos/MOLLE, sombras de pliegues) y **sin
tocar** el chaleco oliva, los guantes/botas negros, la piel ni el cuello
naranja.

## Estructura
```
GreatSpadesTextures/
├── recolor.py                 # Herramienta principal (CLI)
├── palette.json               # Paleta de colores con nombre (editable)
├── README.md                  # Guía de uso rápida
├── CLAUDE.md                  # Este archivo (contexto para agentes)
├── Docs/
│   ├── blocky_humanoid_3d_model_basecolor.jpg   # TEXTURA ORIGEN (8192²)
│   ├── ...Clone1...basecolor.jpg                 # variante verde previa (ref.)
│   ├── VoxelSoldierSegmentationTextureBlender/   # modelo FBX + textura
│   ├── PLAN.md                # Metodología / plan de trabajo (ultracode)
│   ├── ANALISIS_TEXTURA.md    # Análisis exhaustivo del espacio de color
│   ├── PROCESO.md             # Bitácora de decisiones
│   └── _analysis/             # Scripts y artefactos del análisis
├── Variaciones/               # SALIDA: una carpeta por color
│   └── <nombre>/
│       ├── blocky_humanoid_3d_model_basecolor.jpg   # textura lista (8192²)
│       └── preview_<nombre>.png                     # comparativa de control
└── .claude/agents/            # Agentes de IA especializados
```

## Cómo funciona el recoloreado (resumen técnico)
1. **Segmentación por color** (HSV/croma): se aísla la "zona gris
   recoloreable" (uniforme + casco). Se protegen oliva, negro, piel y naranja
   con umbrales validados (ver `Docs/ANALISIS_TEXTURA.md`).
2. **Recoloreado en espacio Lab preservando detalle**:
   - Se **conserva la variación de luminancia `L*`** → toda la tela/costuras/dibujos.
   - Se **recentra el brillo medio** hacia el del color objetivo.
   - Se **sustituye la cromaticidad `(a*, b*)`** por la del color objetivo.
3. **Mezcla con máscara suavizada** (feather gaussiano) → bordes limpios.
4. Procesamiento **por bandas** para soportar 8192² sin agotar memoria.

## Comandos frecuentes
```powershell
# Una variación a resolución completa (8192²)
python recolor.py --color "#1b2f5e" --name azul_marino

# Usar un color con nombre de la paleta
python recolor.py --color forest

# Vista previa rápida (2048², ~3 s) para tantear un color
python recolor.py --color "#7a1f1f" --name rojo --size 2048

# Generar TODA la paleta de golpe
python recolor.py --all-palette

# (Avanzado) casco con color distinto al uniforme, usando máscara pintada
python recolor.py --color "#7a1f1f" --helmet-color "#202020" \
                  --helmet-mask Docs/_analysis/helmet_mask.png --name rojo_casco_negro
```

## Decisiones clave (no re-litigar)
- **Casco y uniforme comparten el mismo material gris** y la misma textura
  (el FBX tiene un único material Phong). No son auto-separables por color.
  → Por defecto, **un color cambia ambos** (esto cumple "cambiar casco y
  uniforme, nada más"). Para colores distintos hace falta una máscara del casco.
- La salida **mantiene 8192²** para ser reemplazo directo de la textura del modelo.
- No se usa `cv2`/`sklearn`/`scipy` (entorno incompleto): solo `numpy` + `Pillow`.

## Convenciones de código
- Español en comentarios y mensajes (idioma del proyecto).
- Sin dependencias nuevas sin justificar; preferir `numpy`+`Pillow`.
- Toda lógica de color en `recolor.py` (funciones puras y testeables).
- Verificación **siempre visual** (preview comparativo) antes de dar por bueno.
