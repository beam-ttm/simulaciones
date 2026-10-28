# Skill: Diseño, Ruteo Programático (`pcbnew`) y Optimización RF de PCBs en KiCad + Sonnet

Esta guía documenta la metodología completa utilizada para analizar, configurar el stackup de fabricación, rutear señales digitales/alimentación/RF de $50\ \Omega$, generar jaulas coaxiales de vías y costuras coplanares (`GCPW`), verificar reglas de diseño (`DRC`) y co-simular antenas microstrip en **Sonnet 19.54**.

---

## 1. Reglas de Oro Antes de Modificar un `.kicad_pcb`

1. **Backup obligatorio y preservación de ediciones manuales:**
   Antes de correr cualquier script sobre la placa, guardar una copia fechada (`cp placa.kicad_pcb placa.backup.kicad_pcb`) y verificar la fecha de modificación (`stat`) por si hubo cambios manuales recientes desde la interfaz gráfica de KiCad.
2. **No eliminar comentarios ni metadatos del proyecto:**
   Al editar bloques S-expression (como `(stackup ...)` en `.kicad_pcb`) o JSON (`.kicad_pro`), reemplazar únicamente el bloque objetivo conservando intactos los comentarios y propiedades existentes.
3. **Respetar estrictamente `Edge.Cuts`:**
   Ninguna zona de cobre (`F.Cu`, `In1.Cu`, `In2.Cu`, `B.Cu`), vía o pista puede superar el contorno físico de `Edge.Cuts`. Mantener un margen mínimo de **`0.50 a 0.60 mm`** hacia adentro respecto a todos los segmentos y arcos de `Edge.Cuts`.

---

## 2. Configuración del Stackup Real de Fabricación (JLCPCB 4 Capas `1.6 mm`)

Para placas de 4 capas con impedancia controlada y antena patch en `F.Cu` + circuito receptor/RF en `B.Cu`:

### Stackup Oficial **`JLC04161H-2116`** (`1.6 mm` prensado)

| Capa KiCad | Material JLCPCB | Espesor real prensado | $\varepsilon_r$ (`1 GHz`) | $\tan\delta$ | Rol en el Diseño |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `F.Cu` (`L1`) | Cobre externo `1 oz` | `0.0350 mm` | — | — | Parche radiante (`Zone 0` en red `/1090_RF_IN`) |
| `dielectric 1` | Prepreg `2116 × 1` | **`0.1164 mm`** *(4.58 mil)* | **`4.16`** | **`0.02`** | Prepreg superior |
| `In1.Cu` (`L2`) | Cobre interno `0.5 oz` | `0.0152 mm` | — | — | **Vaciada debajo del parche** (evita cortocircuitar la cavidad a `0.116 mm`) |
| `dielectric 2` | Core FR-4 | **`1.2650 mm`** | **`4.60`** | **`0.02`** | Núcleo central |
| `In2.Cu` (`L3`) | Cobre interno `0.5 oz` | `0.0152 mm` | — | — | **Plano `GND` sólido cruciforme** (referencia del parche en `F.Cu` y de las líneas `GCPW` en `B.Cu`) |
| `dielectric 3` | Prepreg `2116 × 1` | **`0.1164 mm`** *(4.58 mil)* | **`4.16`** | **`0.02`** | Sustrato de las líneas coplanares RF (`B.Cu` ↔ `In2.Cu`) |
| `B.Cu` (`L4`) | Cobre externo `1 oz` | `0.0350 mm` | — | — | Pistas RF `GCPW` de $50\ \Omega$, componentes y plano `GND` coplanar |

*(Otros stacks de 4 capas de JLCPCB: **`JLC04161H-3313`** usa prepreg `3313` de $h = 0.0994\text{ mm}$, $\varepsilon_r = 4.10$; **`JLC04161H-7628`** usa prepreg `7628` de $h = 0.2104\text{ mm}$, $\varepsilon_r = 4.40$).*

---

## 3. Síntesis de Líneas Coplanares con Plano de Tierra (`GCPW`) de $50\ \Omega$

Cuando el prepreg entre `B.Cu` (`L4`) e `In2.Cu` (`L3`) es fino ($h = 0.1164\text{ mm}$, $\varepsilon_r = 4.16$, cobre $t = 0.035\text{ mm}$):

* Con ancho de pista **`W = 0.200 mm`** y separación coplanar al plano `GND` **`G = 0.200 mm`**:
  $$Z_0 = \mathbf{50.31\ \Omega} \quad (\varepsilon_{\text{eff}} = 3.16)$$
* **Regla de consistencia:** Evitar saltos de ancho en las trazas de RF (por ejemplo, pasar de `0.20 mm` a `0.40 mm` baja la impedancia local a $\sim 32\ \Omega$, generando capacidad parásita). Todas las redes del camino de RF deben pertenecer a una clase de red dedicada **`RF_50ohm`** en el archivo `.kicad_pro`:

```json
{
  "name": "RF_50ohm",
  "track_width": 0.2,
  "clearance": 0.2,
  "via_diameter": 0.5,
  "via_drill": 0.3,
  "microvia_diameter": 0.3,
  "microvia_drill": 0.1
}
```

---

## 4. Transición Vertical Coaxial de $50\ \Omega$ y Costura de Vías (`GND` Stitching)

### 4.1 Jaula Coaxial de Vías en la Alimentación de la Antena (`VIA /1090_RF_IN`)
Para que el paso vertical desde `B.Cu` hasta el parche en `F.Cu` mantenga $50\ \Omega$:
* **Vía central de señal (`F.Cu - B.Cu`):** perforación $d = 0.30\text{ mm}$, pad $0.50\text{ mm}$.
* **Anillo coaxial en "C" de 5 vías de `GND`:** ubicadas a un radio $R = 0.90\text{ mm}$ ($D = 1.80\text{ mm}$) alrededor de la vía central (en ángulos $-90^\circ, -30^\circ, +30^\circ, +150^\circ, -150^\circ$, dejando libre a $+90^\circ$ la salida de la pista hacia `JP3`):
  $$Z_{0,\text{via}} = \frac{60}{\sqrt{\varepsilon_{r,\text{eff}}}} \ln\left(\frac{2R}{d}\right) = \frac{60}{\sqrt{4.56}} \ln\left(\frac{1.80}{0.30}\right) = \mathbf{50.3\ \Omega}$$

### 4.2 Costura de Vías Coplanares (`GCPW` Via Fencing)
* Colocar dos hileras simétricas de vías de `GND` (`pad = 0.30 mm`, `drill = 0.10 mm` ciegas `In2.Cu - B.Cu`, o pasantes según proceso) a **`±0.75 mm`** del eje central de cada pista de RF (`W = 0.20 mm`, `G = 0.20 mm`), con paso longitudinal de **`1.2 a 1.5 mm`**.
* Esto deja un margen limpio de `0.50 mm` entre el borde de la pista RF y el borde del pad de la vía, suprimiendo modos paralelos entre `B.Cu` e `In2.Cu` sin violar `clearance` ni `hole_clearance`.

---

## 5. Estrategia de Ruteo en `B.Cu` con `pcbnew` (Python API)

### 5.1 Inspección de Pads y Ruteo Existente
Antes de agregar pistas programáticamente, extraer las coordenadas exactas en milímetros con `pcbnew`:

```python
import pcbnew

board = pcbnew.LoadBoard("ads-b.kicad_pcb")
for fp in board.GetFootprints():
    for pad in fp.Pads():
        pos = pad.GetPosition()
        print(fp.GetReference(), pad.GetNumber(), pad.GetNetname(),
              round(pcbnew.ToMM(pos.x), 3), round(pcbnew.ToMM(pos.y), 3))
```

### 5.2 Reglas de Geometría al Crear Pistas (`PCB_TRACK`)
1. **Ángulos de $45^\circ$ (octogonales):** Nunca cruzar en ángulos arbitrarios; para ir de $(x_1, y_1)$ a $(x_2, y_2)$, usar un tramo diagonal a $45^\circ$ ($\Delta x = \pm \Delta y$) seguido de un tramo recto horizontal o vertical.
2. **No encerrar islas de `GND`:**
   * En un diseño donde los componentes están en `B.Cu` y el plano `GND` coplanar también está en `B.Cu`, **evitar anillos cerrados de pistas en `B.Cu`** que corten el plano de tierra en islas desconectadas.
   * Si una señal o alimentación (`+3V3`, `+5V`, `I2C`, `UART`) debe cruzar de un extremo a otro, rutearla bordeando el perímetro exterior del bloque digital o usar puentes cortos en capa interna con vías que no corten la referencia debajo de las líneas de RF.
3. **Anchos según función:**
   * **RF ($50\ \Omega$ `GCPW`):** `0.200 mm` exactos.
   * **Alimentación (`+5V`, `+3V3`):** `0.40 a 0.80 mm` en los tramos troncales, reduciendo a `0.25–0.30 mm` únicamente en la entrada a pads SMD finos (`SOT-23-5`, `0402`).
   * **Señales digitales (`UART`, `SPI`, `I2C`, `GPIO`):** `0.20 a 0.25 mm`.

### 5.3 Función Auxiliar para Agregar Cadenas de Pistas y Rellenar Zonas

```python
def add_polyline(board, net_code, layer_id, width_mm, pts_mm):
    for (x1, y1), (x2, y2) in zip(pts_mm[:-1], pts_mm[1:]):
        if abs(x1 - x2) < 1e-4 and abs(y1 - y2) < 1e-4:
            continue
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
        t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
        t.SetWidth(pcbnew.FromMM(width_mm))
        t.SetLayer(layer_id)
        t.SetNetCode(net_code)
        board.Add(t)

# Siempre rellenar todas las zonas antes de guardar y correr DRC:
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
pcbnew.SaveBoard("ads-b.kicad_pcb", board)
```

---

## 6. Verificación Automática con `kicad-cli pcb drc`

Nunca dar por terminado un ruteo sin ejecutar el DRC por línea de comandos y auditar el JSON resultante:

```bash
kicad-cli pcb drc --format json --output /tmp/drc.json ads-b.kicad_pcb
```

Verificar con Python que:
* `len(d["unconnected_items"]) == 0` (**0 redes sin conectar**).
* **0 errores eléctricos:** `clearance = 0`, `shorting_items = 0`, `tracks_crossing = 0`, `hole_clearance = 0`, `annular_width = 0`, `via_diameter = 0`, `via_dangling = 0`, `isolated_copper = 0`, `copper_edge_clearance = 0`.

---

## 7. Co-Simulación Electromagnética y Optimización de la Antena en Sonnet 19.54

### 7.1 Ejecución en el Servidor Remoto (`10.16.100.159:56150`)
* Si el servicio `emserver.exe` en el servidor Windows (`COMPETENCIA-ING-02`, IP `10.16.100.159`, usuario `Desarrollo2`, clave `Ingenieria.2024`) se detiene o entra en `core dumped`, levantarlo por SSH con:
  ```cmd
  "C:\Program Files\Sonnet Software\19.54.2026\bin\emserver.exe" -Hostname 10.16.100.159 -Port 56150
  ```
* Para lanzar la simulación desde Linux aprovechando los 24 hilos del servidor:
  ```bash
  rm -f sonnet/sondata/<proyecto>/lock.lck
  LC_ALL=C /home/alan/sonnet19/bin/emclient -Server 10.16.100.159:56150 \
    -ProjectName /home/alan/Escritorio/CubeSat/sonnet/<proyecto>.sonx -Analyze
  ```
* Al terminar la corrida remota en Windows, normalizar los saltos de línea `CRLF -> LF` de los archivos `.sid` antes de abrir el visor de radiación en Linux:
  ```python
  for sid in Path("sonnet/sondata/<proyecto>").glob("*.sid"):
      sid.write_bytes(sid.read_bytes().replace(b"\r\n", b"\n"))
  ```

### 7.2 Solución a Errores Comunes de Sonnet 19.54 en Ubuntu (`es_AR.UTF-8`)
1. **`Values Are Not Compatible. Start must be less than stop. (SetAllWithError:168)`:**
   Ocurre porque en el locale en español (`es_AR.UTF-8`) el separador decimal es la coma `,`, por lo que Qt/C++ trunca `"0.8"` a `0` y `"1.09"` / `"1.4"` a `1`.
   * **Solución:** Ejecutar siempre `sonnet`, `xgeom`, `emgraph` y `patvu` anteponiendo:
     ```bash
     LC_ALL=C.UTF-8 LC_NUMERIC=C LANG=C.UTF-8 /home/alan/sonnet19/bin/sonnet
     ```
2. **`The specified template file is not compatable with requested plot (GetProjectTemplates:625)`:**
   Ocurre cuando se invoca `sonnet -Additional -farfield -template <archivo.sptx>` con una plantilla `.sptx` cuyo nombre de proyecto interno no coincide o contiene múltiples vistas incompatibles con la exportación CSV por lotes. Usar siempre `templates/campo_AR_1090.sptx` para cortes 2D/AR o `templates/campo_esfera_1090.sptx` para la esfera 3D completa, o bien abrir directamente el `.sptx` generado con `patvu`.

### 7.3 Optimización del Parche y del Reflector `GND` dentro de `Edge.Cuts` (`1090.0 MHz`, $50\ \Omega$)
1. **Efecto del Core $\varepsilon_r = 4.60$:** En el stack `JLC04161H-2116`, el parche en `F.Cu` referenciado a `In2.Cu` ve $h_1 = 0.1164\text{ mm}$ ($\varepsilon_r = 4.16$) + $h_2 = 1.265\text{ mm}$ ($\varepsilon_r = 4.60$), dando $\varepsilon_{r,\text{eff}} \approx 4.56$.
2. **Dimensiones óptimas para `1090.0 MHz` y $50\ \Omega$:**
   * **Lado del parche (`F.Cu`):** **`64.00 × 64.00 mm`** (chaflanes de polarización circular de **`0.75 mm`** en esquinas diagonalmente opuestas).
   * **Offset del punto de alimentación ($d = 0.30\text{ mm}$):** **`18.250 mm`** desde el centro del parche (manteniendo la vía en `(81.410, 85.310)` y centrando el parche en `(81.410, 67.060)` para no alterar el ruteo de `B.Cu`).
   * **Reflector `GND` cruciforme (`In2.Cu` y `B.Cu`):** expandido a **`96.8 × 96.8 mm`** siguiendo las 4 aletas de `80 mm` del contorno PC/104 pero manteniéndose **`0.60 mm` hacia adentro de `Edge.Cuts`** en todo el perímetro.
   * **Resultado medido en Sonnet:** $|S_{11}(1090\text{ MHz})| = \mathbf{-28.03\text{ dB}}$, $Z_{\text{in}}(1090\text{ MHz}) = \mathbf{49.18 + j3.85\ \Omega}$, ancho de banda ($-10\text{ dB}$) de **`1082 – 1100 MHz` (`18 MHz`)** y ganancia realizada hacia el cenit de **`9.85 dBi`** (`+5.43 dB` respecto al parche de `66.5 mm` desadaptado).
