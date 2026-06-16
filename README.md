# Recoloreador del Soldado Voxel — GreatSpades

Genera versiones del soldado con **distinto color de uniforme y casco**
manteniendo intactos los detalles de la tela y el resto de elementos.

## 🖥️ App de escritorio (Editor del Soldado)
Aplicación con **visor 3D** y panel de colores en tiempo real. Doble clic en
**`dist\EditorSoldado.exe`** (o en `start.vbs`). Para generarlo: `construir_exe.bat`.
Detalles en [Docs/APP.md](Docs/APP.md). El resto de este README cubre la
herramienta de línea de comandos `recolor.py`.

---

## Requisitos
- Python 3.x con `numpy` y `Pillow` (ya disponibles en este entorno).

## Uso en 10 segundos
```powershell
# Cambiar el uniforme+casco a azul marino (textura final 8192²)
python recolor.py --color "#1b2f5e" --name azul_marino
```
El resultado queda en:
```
Variaciones/azul_marino/
  ├── blocky_humanoid_3d_model_basecolor.jpg   <- ÚSALA en el modelo
  └── preview_azul_marino.png                   <- control: original | nueva | máscara
```

## Formas de indicar el color
| Forma | Ejemplo |
|-------|---------|
| Hex   | `--color "#1b2f5e"` |
| Nombre de la paleta | `--color forest` |
| (Paleta editable) | `palette.json` |

## Opciones útiles
| Opción | Para qué |
|--------|----------|
| `--name <txt>` | Nombre de la carpeta de salida |
| `--size 2048` | Vista previa rápida (no resolución completa) |
| `--all-palette` | Genera TODAS las variaciones de `palette.json` |
| `--chroma-scale 1.2` | Color más saturado (1.0 = exacto al objetivo) |
| `--contrast 1.1` | Más contraste en la tela |
| `--helmet-color` + `--helmet-mask` | Casco con color distinto (avanzado) |

## Cómo aplicar la textura al modelo
La textura generada es un **reemplazo directo** del archivo
`blocky_humanoid_3d_model_basecolor.jpg`. En tu motor / Blender, sustituye la
textura *base color* del material por la de la carpeta de la variación.

## ¿Casco y uniforme con colores diferentes?
El modelo usa **un único material gris** para ambos, así que por defecto un
color cambia los dos a la vez. Para diferenciarlos hace falta una **máscara
del casco** (PNG blanco=casco). Ver `Docs/ANALISIS_TEXTURA.md`.
