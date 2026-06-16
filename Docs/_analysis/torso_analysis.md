# Análisis de clasificación por TRIÁNGULO (torso / piernas / brazos)

Textura analizada: `app/assets/texture_2048.jpg` (2048², V invertida en UV).
Geometría: `app/assets/geom/` cargada con `bake_regions.load_geom()`.
Entorno: numpy + Pillow (sin cv2/sklearn/scipy). Solo lectura de `bake_regions.py`.

Mapeo malla -> pieza (confirmado por centro/tamaño 3D):
`meshes[k]` con k = i del manifest.
- k=5 `tripo_part_1` = TORSO (chaqueta gris + CHALECO/MOCHILA oliva + correas)
- k=1 `tripo_part_2` = PIERNAS (pantalón gris + BOTAS negras)
- k=2 `tripo_part_3`, k=4 `tripo_part_5` = BRAZOS (manga gris + GUANTES negros)
- k=6 `tripo_part_0` = CABEZA (casco gris + piel + correa barbilla)
- k=0,k=3 = detalles superiores (y≈0.77-0.84)

## Muestreo por triángulo (acordado)
Por cada triángulo se muestrean **13 puntos UV** (centroide + 3 vértices +
3 medios de arista + 6 puntos a mitad de camino hacia el centroide), se
mapean a téxel con V invertida `x=u*W, y=(1-v)*H`. Se toma:
- `med_hue`, `med_chroma`, `med_S` = **mediana** sobre los puntos NO negros (V>=0.14).
- `frac_black` = fracción de puntos con V<0.14.
- `warm` = (G >= B - 0.005) del centroide (tono oliva cálido vs gris neutro).

## Umbrales FINALES (validados)

### NEGRO (botas/guantes/correa)
`frac_black >= 0.5` (mayoría de puntos con V < 0.14).
V_negro = **0.14**. Separa limpio botas/guantes del pantalón/manga.

### OLIVA (chaleco/mochila) — SOLO en malla TORSO (k=5)
```
olive = (med_hue in [30,118]) AND ( med_chroma >= 0.06
                                    OR (med_chroma >= 0.025 AND warm) )
        OR (frac_black>=0.5 AND warm)     # sombra oliva oscura del chaleco
```
- rango hue oliva = **30..118**
- chroma_min oliva = **0.06** (oliva nítido) con rescate a **0.025** si es cálido
  (G>=B) -> captura el oliva oscuro/desgastado del chaleco.
- La tercera condición rescata las **sombras oscuras del chaleco** (V<0.14 pero
  cálidas) que antes caían en negro: de 481 triángulos oscuros del torso, 430
  son oliva-oscuro cálido (vest) y solo 51 son neutros (correa real).

Justificación del rescate (clusters medidos en torso):
- oliva fuerte: RGB≈(0.29,0.24,0.15), hue 40, chroma 0.149
- oliva débil/desgastado: RGB≈(0.20,0.19,0.17), hue 40, chroma 0.039, 195/199 con G>=B
- gris genuino: RGB≈(0.20,0.20,0.20), hue indefinido, chroma 0.016 (NEUTRO)
El gris jacket es neutro (R≈G≈B); el oliva, aun desgastado, es cálido (R>=G>=B).

### NARANJA / CUELLO — restringido
```
cuello = (med_hue in [5,33]) AND (med_S>0.45) AND (med_V>0.4)
         AND (mesh in {TORSO, CABEZA}) AND (y_centroide_3D > 0.78)
```
Antes el naranja se disparaba en la INGLE/entrepierna (piernas). Restringiendo a
torso/cabeza + parte ALTA (y>0.78), **piernas y brazos quedan con 0 triángulos
naranja**. En piernas/brazos cualquier cosa NO negra -> uniforme.

### PIEL
`med_hue in [8,45] AND med_S in [0.18,0.55] AND med_V>0.5 AND not olive`.

### Prioridad de asignación (desempate)
`oliva > naranja > piel > negro > uniforme` (no perder chaleco en bordes).

### Mapeo a REGIÓN FINAL por malla
| color dominante | TORSO(5) | PIERNAS(1) | BRAZOS(2,4) | CABEZA(6)/detalle |
|---|---|---|---|---|
| gris/uniforme | 1 uniforme | 1 uniforme | 1 uniforme | 1 (casco→1) |
| oliva | 2 chaleco | — (no aplica) | — (no aplica) | — |
| negro | 7 correa (bloq) | 3 botas | 6 guantes | 7 correa (bloq) |
| naranja+alto | 4 cuello | — | — | 4 cuello |
| piel | 0 piel (bloq) | — | — | 0 piel (bloq) |

OLIVA y NARANJA se calculan **solo** en las mallas indicadas; en piernas/brazos
NO se evalúa oliva (cualquier no-negro = uniforme).

## Recuentos por malla (clasificador final, v2 mesh-scoped)
| k | pieza | nTri | uniforme | chaleco | botas | guantes | correa | cuello | piel |
|---|---|---|---|---|---|---|---|---|---|
| 5 | TORSO | 3191 | 28% (880) | **72% (2282)** | — | — | 1% (29) | 0 | 0 |
| 1 | PIERNAS | 1827 | 65% (1179) | — | 35% (648) | — | — | **0** | 0 |
| 2 | BRAZO-tras | 1694 | 71% (1204) | — | — | 29% (488) | — | 0 | 0% (2) |
| 4 | BRAZO-del | 920 | 68% (630) | — | — | 32% (290) | — | 0 | 0 |
| 6 | CABEZA | 4508 | 90% (4063) | — | — | — | 8% (383) | 0% (8) | 1% (54) |
| 0 | detalle | 38 | 8% | — | — | — | — | — | 92% piel |
| 3 | detalle | 88 | 82% | — | — | — | 17% | — | 1% |

## Verificación de fugas
- **Chaleco completo sin azul**: de los 880 triángulos torso clasificados
  uniforme, solo **11** (0.3% del torso) son oliva-borde residual; el resto tiene
  color medio RGB=(0.265,0.266,0.270) = gris neutro real. La fuga azul anterior
  (66 triángulos hue 190-250 bajo los brazos) queda absorbida correctamente como
  oliva/gris. PROBLEMA A y C resueltos.
- **Ingle naranja**: PIERNAS con 0 triángulos naranja tras restringir cuello a
  torso/cabeza + y>0.78. PROBLEMA B resuelto.
- **Grises entre piernas**: ahora pantalón = uniforme (no negro, no naranja).

## Evidencia visual
- `Docs/_analysis/regionmap_v2.png` — mapa de región de TODO el atlas.
- `Docs/_analysis/regionmap_v2_torso.png` — torso (verde=chaleco sólido, sin azul-fuga).
- `Docs/_analysis/regionmap_legs.png` — piernas (magenta=pantalón, azul-claro=botas, 0 naranja).
- `Docs/_analysis/torso_classmap.png` — comparativa ANTES (umbral viejo, con fugas cyan).
Paleta: magenta=uniforme, verde=chaleco, azul-claro=botas, azul=guantes,
naranja=correa, rojo=cuello, amarillo=piel.
