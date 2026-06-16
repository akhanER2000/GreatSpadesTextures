# Editor del Soldado — App de escritorio

Aplicación de escritorio para **ver el modelo 3D y recolorearlo por piezas** en
tiempo real, con la piel siempre protegida. Doble clic y listo.

## Cómo abrir
- **`dist\EditorSoldado.exe`** — ejecutable independiente (no requiere Python).
- **`start.vbs`** — lanza el .exe sin consola (ideal para acceso directo).
- **`Editor del Soldado.bat`** — lanza el .exe (con aviso si falta).
- **`start_dev.bat`** — modo desarrollo (ejecuta desde el código fuente).

## Cómo construir el .exe
```
construir_exe.bat
```
Crea el entorno (Python 3.12), instala dependencias, genera los activos y
empaqueta con PyInstaller → `dist\EditorSoldado.exe` (con icono del soldado).

## Qué hace
- **Visor 3D** (three.js): rotar (arrastrar), zoom (rueda), desplazar (clic der.).
- **Panel derecho**: color por pieza, en tiempo real:
  - Uniforme y casco · Chaleco · Botas y guantes · Cuello.
  - **Piel y cara: bloqueada** (nunca se recolorea, por diseño).
- **Exportar textura (8192²)**: aplica los colores a máxima resolución y guarda
  en `Variaciones\<nombre>\blocky_humanoid_3d_model_basecolor.jpg` (junto al .exe).

## Cómo recolorea sin perder el detalle
Igual que `recolor.py`: en espacio **Lab** conserva la luminancia `L*` (todo el
detalle de la tela) y sustituye la cromaticidad por la del color objetivo,
recentrando el brillo. En el visor se hace en la **GPU** (shader) usando un
**mapa de regiones** (`app/assets/regions_2048.png`); la exportación lo hace en
Python a 8192² combinando el partmap con el color.

## Regiones por GEOMETRÍA (clasificación POR TRIÁNGULO)
Para separar piezas que comparten color (casco↔uniforme, botas↔guantes), no
dejar zonas sin colorear por el desgaste, y evitar “manchas” por píxel, cada
**triángulo** recibe UNA sola región (resultado sólido, sin motas):
1. `tools/geom_server.py` + `app/_extract.html` extraen la geometría (vía
   WebView2/three.js) a `app/assets/geom/`.
2. `bake_regions.py`: para cada triángulo toma (a) su **malla/pieza**, (b) su
   **color dominante** (muestreado en 7 puntos del triángulo) y (c) su
   **geometría**. Reglas clave:
   - **Cara 100% bloqueada** por geometría: triángulos frontales de la cabeza
     (`cxn>0.79`, banda de altura `0.77–0.875`, central) → nunca se recolorean
     (incluye cejas/ojos/mentón, aunque no sean color piel).
   - **Chaleco/mochila** = oliva (test “cálido” G>B, captura el oliva oscuro).
   - **Brazos/piernas** = todo lo no-negro → uniforme; negro = guantes (brazos)
     o botas (solo en los pies; el negro de ingle/rodilla queda bloqueado).
   - Piel, correa de barbilla y herrajes negros → bloqueados.
   Rasteriza por triángulo y dilata el *gutter* sin comerse la cara.
3. `engine.py` exporta cargando ese mapa final (NEAREST a 8192²) y aplicando Lab.
4. Validado con auditoría 3D multiángulo (`app/_audit.html`, `_recaudit.html`,
   `_multiaudit.html`), incl. test de **casco blanco** (la cara no cambia).

Mapa malla→pieza (Tripo): part_0=cabeza, part_1=torso, part_2=piernas,
part_3/part_5=brazos, part_4/part_6=accesorios de la cabeza.

## Arquitectura
```
app/
├── main.py            # ventana nativa (pywebview) + servidor local + API exportar
├── engine.py          # motor de recoloreado multi-región a 8192² (numpy/Pillow)
├── index.html         # layout (visor + panel)
├── app.js             # three.js: carga FBX, shader de recolor por región
├── styles.css
├── vendor/            # three.js vendorizado (offline)
└── assets/            # model.fbx, texture_2048.jpg, regions_2048.png, meta, texture_8192.jpg
build_assets.py        # genera los activos (textura + mapa de regiones)
EditorSoldado.spec     # receta de empaquetado (PyInstaller, onefile, icono)
```

## Notas técnicas (validadas)
- El modelo FBX (Tripo) carga directo con `FBXLoader`; requiere `flipY=true` en
  la textura. El modelo es **Z-up**: se envuelve en un *pivote* para rotarlo sin
  romper su orientación.
- Casco/uniforme comparten material gris y botas/guantes el negro: por color son
  inseparables (ver `ANALISIS_TEXTURA.md`). La separación fina por geometría es
  una mejora opcional (fase 2).
- Empaquetado con **Python 3.12** (PyInstaller no soporta aún 3.14).
