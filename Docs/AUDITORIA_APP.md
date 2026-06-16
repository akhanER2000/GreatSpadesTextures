# Auditoría de factibilidad — App de escritorio "Editor del Soldado"

> Pregunta del usuario: ¿es factible, **sin errores**, una app de escritorio que
> muestre el modelo 3D con su textura, se pueda **rotar/mover**, y con un panel a
> la derecha permita **cambiar el color** del uniforme, casco (y opcionalmente
> chaleco, botas, guantes), **sin tocar la piel/cara nunca**? ¿Y empaquetarla en
> un **.exe** de doble clic, con icono?

## Veredicto: SÍ, factible. Con 2 matices honestos (abajo).

---

## 1. Reconocimiento del entorno (verificado)
| Componente | Estado |
|------------|--------|
| Python 3.14 (`C:\Python314`) | ✔ (numpy, Pillow). scipy roto, cv2/sklearn ausentes |
| **Python 3.12** (`py -V:3.12`) | ✔ **← se usará para empaquetar (.exe estable)** |
| pip + Internet (PyPI) | ✔ (200 OK) → se pueden instalar pywebview + PyInstaller |
| tkinter | ✔ (fallback de GUI nativa si hiciera falta) |
| git 2.53 + credenciales `akhanER2000` | ✔ (commit hecho; push disponible) |
| Modelo `…tripo_convert….fbx` | ✔ FBX binario Kaydara 7.x, 1 material Phong, 1 textura |

**Riesgo de Python 3.14:** PyInstaller/pywebview aún no soportan bien 3.14.
**Mitigación aplicada:** construir y empaquetar con **Python 3.12** (instalado).

---

## 2. Arquitectura propuesta (la más robusta y profesional)

```
┌──────────────────────────────────────────────────────────┐
│  Ventana nativa (pywebview)  →  se empaqueta a .exe        │
│  ┌────────────────────────────┬───────────────────────┐   │
│  │   Visor 3D (three.js)      │   Panel de ajustes     │   │
│  │   - carga modelo + textura │   - Uniforme  [color]  │   │
│  │   - OrbitControls          │   - Casco     [color]  │   │
│  │     (rotar / zoom / mover) │   - Chaleco   [color]  │   │
│  │   - recolor en GPU (shader)│   - Botas/Guantes[color]│  │
│  │                            │   - Piel  🔒 (bloqueada)│  │
│  └────────────────────────────┴───────────────────────┘   │
│  Backend Python (js_api): exportar textura 8192² + variar  │
└──────────────────────────────────────────────────────────┘
```

**Por qué web (three.js) dentro de ventana nativa (pywebview):**
- three.js hace 3D + textura + rotación (OrbitControls) de forma nativa y fluida.
- El **recoloreado se hace en la GPU con un shader** usando un *mapa de regiones*
  (qué texel es uniforme/casco/chaleco/etc.), con la **misma matemática Lab** que
  preserva el detalle de tela → **vista previa en tiempo real**, sin esperas.
- pywebview da una **ventana de app real** (sin barra de navegador).
- **PyInstaller** empaqueta Python + pywebview + activos en **un `.exe`** con icono.
- Lanzadores `.bat` y `.vbs` para abrir sin consola (como en tu referencia).

**Alternativas descartadas:** Electron (pesado, requiere Node), PyOpenGL/VTK
(no cargan FBX y la UI es más costosa), app 2D sin 3D (no cumple "ver/rotar 3D").

---

## 3. ¿Qué se puede cambiar y qué no? (matriz por región)

La textura es **un atlas único**; las piezas se distinguen por **color**, no por
geometría. Eso define qué es separable de inmediato:

| Pieza | Región de color | ¿Independiente? | Notas |
|-------|-----------------|-----------------|-------|
| **Uniforme + Casco** | gris (50–56 %) | Juntos ✔ / separar ⚠ | mismo material gris |
| **Chaleco** | oliva (18 %) | **Sí ✔** | cluster propio |
| **Botas + Guantes** | negro (23 %) | Juntos ✔ / separar ⚠ | mismo negro |
| **Cuello** | naranja (0.5 %) | Sí ✔ (opcional) | |
| **Piel / cara** | piel (1.4 %) | **🔒 NUNCA** | excluida de toda máscara |

**Garantía sobre la piel:** la piel se define como su propio cluster y queda
**fuera de todas las máscaras de recoloreado**. Es imposible que cambie aunque se
toquen todos los controles. (Verificado ya en el motor actual.)

### Los 2 matices (⚠)
1. **Casco vs Uniforme con colores distintos:** comparten el mismo gris, así que
   por color no se separan. *Solución:* generar una **máscara por geometría** —
   al cargar el modelo, clasificar las islas UV por su posición 3D (el casco es el
   grupo superior, sobre el cuello). Es **factible** pero es I+D; se hará en fase 2.
   En fase 1, "Uniforme" y "Casco" comparten un control (o se ofrecen dos que por
   ahora afectan a ambos, con aviso claro).
2. **Botas vs Guantes:** mismo caso (mismo negro). Mismo plan (máscara por
   geometría: guantes = extremos de brazos, botas = parte inferior).

> Honestidad de ingeniería: prometer "casco y uniforme con colores totalmente
> independientes" **sin** la máscara por geometría sería un error. El plan lo
> resuelve por fases para no bloquear la entrega.

---

## 4. Carga del modelo 3D (riesgo principal y plan)
- **Plan A:** `FBXLoader` de three.js carga el FBX tal cual (Tripo exporta FBX 7.x
  estándar, normalmente compatible). Se sustituye el material por nuestro shader.
- **Plan B (fallback):** convertir el FBX a **glTF/GLB** (estándar que three.js
  carga siempre). Se hará un conversor offline en fase 0 si el Plan A falla en la
  validación. La conversión también permite calcular las máscaras por geometría.
- **Validación obligatoria:** se probará la carga real en la ventana antes de
  seguir; no se da por bueno hasta verlo renderizado.

**Rendimiento:** el visor usará la textura a **2048²** (suficiente y fluido en
GPU); la **exportación** usa el motor Python a **8192²** (calidad final).

---

## 5. Empaquetado a .exe (plan verificado)
1. Crear entorno con **Python 3.12**: `py -3.12 -m venv .venv`.
2. `pip install pywebview pyinstaller pillow numpy`.
3. `pyinstaller` con `--onefile --windowed --icon app.ico --add-data` (activos:
   modelo, textura, mapa de regiones, frontend web).
4. Salida: `dist/EditorSoldado.exe` (doble clic, con icono).
5. Lanzadores adicionales: `start.bat` (con consola para depurar) y
   `start.vbs` (sin consola), como en tu carpeta de referencia.
6. Icono: se generará un `app.ico` temático (casco del soldado) desde la textura.

---

## 6. Plan de implementación por fases
- **F0 – Base estable + activos:** commit ✔ → push; validar carga del modelo
  (Plan A/B); generar textura 2048² + **mapa de regiones**.
- **F1 – App funcional:** ventana pywebview + visor three.js (rotar) + panel de
  color (uniforme/casco juntos, chaleco, botas/guantes, **piel bloqueada**) +
  recolor en shader en tiempo real.
- **F2 – Separación por geometría:** casco↔uniforme y botas↔guantes con máscara
  derivada de la posición 3D.
- **F3 – Export:** botón "Guardar variación" → textura 8192² en `Variaciones/`.
- **F4 – Empaquetado:** `.exe` + icono + `.bat`/`.vbs`; **validación** doble clic.

## 7. Criterios de aceptación (cómo se valida "sin errores")
- [ ] La ventana abre con doble clic (.exe y .bat/.vbs).
- [ ] Se ve el modelo 3D con su textura y se puede **rotar/zoom**.
- [ ] Cambiar cada color actualiza el modelo en tiempo real.
- [ ] La **piel/cara nunca** cambia bajo ninguna combinación.
- [ ] Exportar produce una textura 8192² válida en `Variaciones/`.
- [ ] No hay errores en consola; arranque limpio en una carpeta nueva.

## 8. Conclusión
Es **factible y sin riesgos bloqueantes**. Los dos únicos puntos delicados
(casco↔uniforme y botas↔guantes con colores distintos) tienen solución conocida
(máscara por geometría) y se abordan por fases. Todo lo demás —visor 3D, panel,
piel bloqueada, .exe con icono— es directo con el stack elegido.
