# PLAN DE TRABAJO — Metodología Ultracode

> Objetivo del usuario: una herramienta (con apoyo de IA/visión por computador)
> que, dado un color, genere variaciones del soldado cambiando **solo** el color
> del **uniforme y el casco** (zona gris), **sin perder los detalles de la tela**,
> y guarde el resultado en una carpeta de variaciones.

## Fases (ultracode workflow)

### Fase 0 — Reconocimiento  ✅
- Inventario de archivos: textura origen `...basecolor.jpg` (8192²), variante
  verde previa (Clone1), 4 renders de referencia, modelo FBX (Tripo).
- Entorno: Python 3.14, `numpy`+`Pillow` OK; `cv2`/`sklearn`/`scipy` NO.

### Fase 1 — Análisis exhaustivo de la textura  ✅
- Segmentación cuantitativa del espacio de color (HSV/Lab).
- Identificación de clusters: gris (50–56%), negro (23%), oliva (18%),
  piel (1.4%), naranja (0.5%).
- Validación visual de máscaras (overlay + mapa de clasificación).
- Conclusión: casco y uniforme = mismo gris (no auto-separables).
- → Detalle completo en `ANALISIS_TEXTURA.md`.

### Fase 2 — Motor de recoloreado preservando detalle  ✅
- Espacio Lab: preservar `L*` (detalle), recentrar brillo, sustituir `a*b*`.
- Máscara con feather; procesamiento por bandas (memoria 8192²).
- CLI por color hex o nombre de paleta.

### Fase 3 — Separación casco/uniforme  ✅ (decisión)
- Auto-separación inviable (un solo material). Por defecto: color único para
  ambos. Modo avanzado: máscara del casco pintada → `--helmet-color/--helmet-mask`.

### Fase 4 — Documentación + agentes especializados  ✅
- `CLAUDE.md`, `README.md`, `PLAN.md`, `ANALISIS_TEXTURA.md`, `PROCESO.md`.
- `.claude/agents/`: texture-analyst, recolor-engineer, qa-visual-reviewer,
  palette-designer.

### Fase 5 — Generación de variaciones + QA visual  ✅
- Paleta de colores generada en `Variaciones/`.
- Verificación visual: detalle de tela conservado; zonas protegidas intactas.

## Criterios de aceptación
- [x] Solo cambia uniforme + casco (gris). Oliva/negro/piel/naranja intactos.
- [x] Se conservan trama, costuras, dibujos y sombras de la tela.
- [x] Entrada por color (hex o nombre).
- [x] Salida 8192² lista para el modelo, en `Variaciones/<color>/`.
- [x] Comparativa de control por cada variación.

## Roles de los agentes especializados
| Agente | Responsabilidad |
|--------|-----------------|
| `texture-analyst` | Analiza el atlas, define/ajusta umbrales de máscara |
| `recolor-engineer` | Mantiene/extiende `recolor.py` (Lab, bandas, CLI) |
| `qa-visual-reviewer` | Verifica visualmente cada variación (detalle + fugas) |
| `palette-designer` | Propone paletas coherentes para el juego |
