# Análisis exhaustivo de la textura

Textura: `Docs/blocky_humanoid_3d_model_basecolor.jpg` — **8192×8192 RGB**, atlas
UV muy fragmentado (islas pequeñas dispersas, típico de Tripo AI).

## 1. Distribución de saturación (muestreo 1.05 M px)
| Saturación S | % de píxeles | V medio |
|--------------|-------------:|--------:|
| 0.00–0.08 | 58.5 % | 0.30 |
| 0.08–0.15 |  9.2 % | 0.31 |
| 0.15–0.25 |  5.5 % | 0.25 |
| 0.25–0.40 |  5.8 % | 0.26 |
| 0.40–1.00 | 21.0 % | 0.28 |

La textura está dominada por píxeles de **baja saturación** (gris) → la zona
recoloreable es grande.

## 2. Clusters de color (categorías)
| Categoría | % | RGB medio | Acción |
|-----------|--:|-----------|--------|
| **Gris (uniforme+casco)** | **50–56 %** | (96, 95, 93) | **RECOLOREAR** |
| Negro (guantes/botas/correas) | 23 % | (10, 10, 8) | preservar |
| Oliva (chaleco) | 18 % | (79, 67, 42) | preservar |
| Piel (cara) | 1.4 % | (170, 129, 105) | preservar |
| Naranja (cuello) | 0.5 % | (152, 77, 47) | preservar |
| Sin clasificar | 2 % | (74, 67, 61) | (bordes/AO) |

Mapa de clasificación validado visualmente en `_analysis/classify_map.png`
(magenta=gris, verde=oliva, azul=negro, amarillo=piel, rojo=naranja).

## 3. Umbrales de la máscara recoloreable (validados)
```python
gray       = (chroma < 0.07) & (V >= 0.14) & (V <= 0.82)
olive_like = (hue 33..105) & (chroma >= 0.045)     # protege el chaleco
mask       = gray & ~olive_like
```
- `chroma = max(R,G,B) - min(R,G,B)` (0..1).
- El gris del uniforme tiene croma ≈ 0.01 → muy separable del oliva (croma ≈ 0.14).
- El suelo de valor `V≥0.14` excluye el negro; el techo `V≤0.82` evita reflejos.
- Cobertura de la máscara ≈ **56 %** del atlas (uniforme + casco).

## 4. ¿Casco vs uniforme separables?
- k-means(2) sobre el **valor** del gris → centros 0.276 y 0.417, separación
  **0.141** (eso es sombra vs luz, **no** dos materiales distintos).
- El **FBX** tiene **un único material Phong** y **una sola textura** para todo
  (mallas `Mesh_0`/`Mesh_1` comparten material).
- **Conclusión:** casco y uniforme son el **mismo gris** → no se pueden separar
  automáticamente por color. Un color cambia ambos. Para diferenciarlos se
  necesita una **máscara del casco** (PNG), pintada o derivada de las islas UV.

## 5. Estrategia de recoloreado (por qué preserva el detalle)
La tela es prácticamente **monocroma**: todo su "dibujo" (costuras, MOLLE,
bolsillos, pliegues, sombras) vive en la **luminancia**, no en el color. Por eso:
- Convertimos a **Lab**.
- **Conservamos `L*`** (= todo el detalle) y solo recentramos su media.
- **Sustituimos `a*`, `b*`** por la cromaticidad del color objetivo.
Resultado: misma tela, color nuevo. Verificado en `_analysis/detail_crop.png`.

## 6. Artefactos del análisis (`Docs/_analysis/`)
- `analyze.py` — segmentación cuantitativa.
- `mask_preview.py` → `mask_overlay.png`, `mask_binary.png`.
- `classify_map.py` → `classify_map.png`.
- `detail_crop.png` — comparativa de detalle (original vs recoloreado).
