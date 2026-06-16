# Bitácora de decisiones (PROCESO)

## D1 — Enfoque: visión por computador clásica, no IA generativa
**Decisión:** segmentación por color + recoloreado en Lab, en local con
`numpy`/`Pillow`.
**Por qué:** preserva el detalle de tela **píxel a píxel** (la IA generativa
re-inventa texturas y pierde costuras/dibujos), es **determinista**,
**reproducible**, **gratis** y **rápido** (~23 s a 8192²). El usuario quería
"no perder los detalles" → este método los garantiza al 100 %.

## D2 — Espacio Lab con preservación de L*
**Decisión:** conservar `L*` (luminancia) y reemplazar `a*b*` (cromaticidad).
**Por qué:** la tela es monocroma; su detalle es puramente lumínico. Preservar
`L*` conserva todo; cambiar `a*b*` cambia el color exacto.

## D3 — Brillo recentrado hacia el color objetivo
**Decisión:** `L_new = L_target + (L_src - L_media) * contraste`.
**Por qué:** si solo se mantuviera `L*` original, un objetivo oscuro (p.ej. azul
marino) saldría demasiado claro. Recentrar la media hace que el color final
coincida con el elegido, conservando la variación (detalle).

## D4 — Casco y uniforme: un solo color por defecto
**Decisión:** por defecto el color se aplica a todo el gris (casco+uniforme).
**Por qué:** comparten material y son el mismo gris (ver ANALISIS_TEXTURA §4).
Cumple el requisito ("cambiar casco y uniforme, nada más"). Modo avanzado con
máscara para colores distintos.

## D5 — Salida a 8192² (resolución original)
**Decisión:** mantener 8192² en las variaciones.
**Por qué:** reemplazo directo de la textura del modelo, sin pérdida de detalle.
Modo `--size` disponible solo para previews rápidas.

## D6 — Sin scipy
**Decisión:** feather con `PIL.ImageFilter.GaussianBlur` en vez de
`scipy.ndimage`.
**Por qué:** `scipy` está roto en el entorno (`No module named 'scipy._lib'`).

## Incidencias resueltas
- `scipy` roto → reemplazado por PIL (D6).
- Memoria a 8192² → procesamiento por bandas de 1024 filas.
- Línea corrupta en la paleta (`coyote`) → corregida.
