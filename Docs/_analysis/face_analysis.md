# Análisis geométrico de la CARA (malla CABEZA #6) — selección por triángulo

## Objetivo
Regla GEOMÉTRICA por triángulo que seleccione TODA la cara (piel + cejas +
ojos + nariz + boca + mentón) y EXCLUYA el casco, para bloquear el recoloreado
del rostro al 100 %. Necesario porque las cejas/ojos/contorno NO son color piel
(son oscuros) y porque el atlas UV está MUY fragmentado (las islas de cara y
casco se entremezclan), así que una regla solo-color falla.

## Datos de la malla #6 ('tripo_part_0' = cabeza, incluye casco + cara)
- Triángulos: 4508. Vértices: 13524.
- Caja global (gmin/gmax): min[-0.1636, 0, -0.3807] max[0.1636, 1, 0.3807],
  size [0.3272, 1.0, 0.7613]. Y-up; frente del modelo = +X.
- Normalización del centroide: `cn = (centroide - gmin) / (gmax - gmin)`.
- Textura: `app/assets/texture_2048.jpg` (2048²). Conversión V-invertida:
  `x = u*2047`, `y = (1-v)*2047`.

## Hallazgos clave
1. **El plano frontal de la cara está aislado por cxn (profundidad +X).**
   - Triángulos de piel: cxn 0.804–0.831 (mediana 0.828), muy compactos.
   - Casco gris en la misma banda Y/Z: cxn 0.10–0.25 (mediana 0.18).
   - Hueco enorme entre ambos → `cxn > 0.79` separa cara de casco limpiamente.
   - La normal.x NO sirve sola: el winding es inconsistente y los bordes de la
     cara (mejillas/mandíbula) tienen normal lateral (nx≈0) aunque su cxn sigue
     siendo alto. Por eso se usa cxn, no nx.

2. **Las cejas/ojos (oscuros) están embebidos en el mismo plano que la piel.**
   - 66–86 triángulos "oscuros" (V<0.30) caen dentro de la caja de la cara,
     rodeados de piel. Quedan capturados por la regla geométrica (no se
     clasifican por color), que es justo lo que se exige.

3. **El límite superior de la cara (frente↔ala del casco) es un acantilado de
   calidez (R−B) en cyn ≈ 0.875.**
   - cyn 0.84–0.87: cálido (R−B ≈ +0.26) = piel (frente/ceja).
   - cyn 0.87–0.875: transición (mitad cálido) = línea de la ceja/ala.
   - cyn ≥ 0.88: neutro (R−B ≈ +0.01, S ≈ 0.03) = casco gris.
   - En cyn 0.875–0.89 la frente cálida (19 tris) y el ala del casco (223 tris)
     comparten el MISMO rango czn → físicamente entremezclados en la sombra del
     ala. Ninguna caja geométrica los separa ahí. Por eso `yhi = 0.875` es el
     corte óptimo: subirlo a 0.88 inunda de casco (gris 4 %→34 %).

4. **El ancho lateral.** Piel czn 0.41–0.58 → `|czn-0.5| < 0.11` cubre todo el
   ancho de la cara sin tocar los laterales/atrás de la cabeza (que además
   tienen cxn bajo).

## Umbrales finales (malla #6)
| parámetro | valor | significado |
|-----------|-------|-------------|
| T_cxn (cxlo) | **0.79** | profundidad frontal mínima (separa cara de casco) |
| ylo | **0.77** | base de la cara (mentón) |
| yhi | **0.875** | tope de la cara (línea ceja / ala del casco) |
| zw  | **0.11** | medio-ancho lateral (`|czn-0.5| < zw`) |

> Nota: el campo pedido `T_nx` se SUSTITUYE por `T_cxn` porque la normal.x no
> es discriminante fiable (winding inconsistente; bordes de cara con normal
> lateral). El centroide cxn separa cara/casco con un margen enorme (0.83 vs 0.18).

## Recuentos con los umbrales finales (cxn>0.79, cyn∈[0.77,0.875], |czn-0.5|<0.11)
- FACE = **156** triángulos (de 4508 de la cabeza).
- Piel capturada: **57 / 57 = 100 %** (0 triángulos de piel perdidos).
- Oscuros embebidos (cejas/ojos/nariz) dentro de FACE: **86**.
- Gris-casco dentro de FACE: **6** (3.8 %); son texels de piel en sombra
  (V 0.33–0.45, croma baja) en cxn≈0.83, NO casco (el casco está en cxn≈0.18).
- Cobertura del atlas 2048²: **1.16 %** (coherente con el clúster de piel ≈1.4 %).

## Verificación visual
- `Docs/_analysis/face_front_scatter2.png`: proyección frontal (Z×Y). El óvalo
  facial completo en magenta (ceja→mentón, incluida la banda de ojos); el verde
  interior son triángulos de la nuca/laterales (cxn<0.79) que se solapan en la
  proyección.
- `Docs/_analysis/face_island_overlay.png` (+ `_small`): máscara FACE rasterizada
  sobre el atlas. El magenta cae en texels cálidos (piel) y oscuros (ojos/cejas)
  dispersos por las islas UV fragmentadas, SIN tocar las manchas grises del casco.

## Fugas / límites conocidos
- ~19 triángulos de frente cálida justo en cyn 0.875–0.878 (sombra del ala)
  quedan FUERA de FACE. Son inseparables del casco por geometría (mismo czn).
  Pérdida mínima y en la zona de contacto física cara/casco.
- Estos umbrales son específicos de la malla #6 y de esta caja global. Si se
  re-extrae la geometría con otra normalización, recalibrar cxlo/ylo/yhi/zw.

## Función lista para pegar
```python
def is_face_triangle(normal, cxn, cyn, czn) -> bool:
    \"\"\"True si el triángulo de la malla CABEZA (#6) pertenece a la CARA
    (piel + cejas + ojos + nariz + boca + mentón) y NO al casco.
    Geometría pura: cxn/cyn/czn = centroide normalizado a [0,1] con la caja
    GLOBAL (cn = (centroide - gmin)/(gmax - gmin)). 'normal' se ignora (winding
    inconsistente); la profundidad frontal cxn es el discriminante real.
    \"\"\"
    return (cxn > 0.79) and (0.77 <= cyn <= 0.875) and (abs(czn - 0.5) < 0.11)
```
