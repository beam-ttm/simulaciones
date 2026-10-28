# Antena ADS-B de BEAM-TTM — Sonnet

Modelo generado desde el PCB real, con las cuatro capas de cobre, rellenos almacenados, pistas, pads, despejes, 88 vías y cuatro barriles de pads pasantes metalizados. **No hay resultados electromagnéticos completados.** El servidor remoto Windows 19.54.2026 ya responde en `10.16.100.159:56150`. El intento remoto del 19/10/2026 a las 16:24:24 llegó a 0,8 GHz y falló en el mallado conformal. Se cambió el mallado planar a RECTANGULAR; falta repetir el análisis remoto y comprobar convergencia.

Abrir `models/A_real_ready.sonx` en Sonnet. También se entrega una copia en `sonnet/patch.sonx` del workspace; su plantilla inicial se conserva en `sonnet/patch.original.sonx` y `source/blank.sonx`.

## Hallazgo que afecta al diseño

El patch F.Cu tiene seis vértices de contorno y dos esquinas truncadas. Sus límites son aproximadamente X=48,16002…114,66003 mm, Y=33,06002…99,56003 mm. **El relleno deja 0,2545 mm entre el pad de alimentación y el patch: no hay unión galvánica.** La vía RF está en (81,41011; 85,30994) mm, con pad de 0,40 mm y taladro de 0,30 mm. El modelo conserva esa separación; no convierte la antena existente en un patch convencional conectado por sonda. Esto no demuestra por sí solo si la excitación capacitiva es intencional.

Ver [verificación geométrica](reports/geometry_verification.md), [imagen de las capas](reports/copper_layers.png) y [supuestos y limitaciones](reports/limitations.md).

## Fuentes y trazabilidad

- Repositorio: https://github.com/beam-ttm/PCB, archivo `1-ADS-B/Final/ads-b/ads-b.kicad_pcb`, rama `main`.
- El conector GitHub devolvió para ese archivo el blob `14dfc0d47c17186fb33b4abe7bb53a42ed9653eb`; coincide con `git hash-object` del PCB local. Se usó esa copia completa. Las otras fuentes se copiaron del mismo checkout local.
- `source/` contiene PCB, proyecto, esquemático y Gerbers/Excellon; `source_manifest.json` registra hashes SHA-256. No se guardó ni modificó el PCB original ni se cambió la rama del repositorio.
- La extracción usa `pcbnew` de KiCad 10.0.6. Se convierten las formas con error de cuerda de 0,25 µm en memoria, se unen los polígonos y se restan las perforaciones. Los rellenos de zonas se conservan exactamente como están almacenados.
- Se compararon las cuatro capas con los Gerbers usando un parser independiente, el contorno con las líneas centrales de Edge.Cuts y los taladros con Excellon. Los resultados numéricos están en `reports/geometry_verification.json`.
- El formato XML se contrastó con los ejemplos `via`, `rfid_system` y `feedviapatch` de Sonnet instalado. Se utilizó `sonnet_macro_starter_kit.md` como referencia; las macros se probaron con el ejecutable instalado.

## Modelo y puerto

El puerto interno flotante usa terminales +1 y −1 y referencia de 50 Ω. El positivo está en el borde del pad RF de D1, en (78,5; 85,6) mm; el retorno se coloca en el borde real del cobre GND adyacente, cerca de (78,38337; 85,8005) mm. Es un plano de excitación local de la antena; no representa un conector externo ni el receptor completo. D1 y el resto de componentes no tienen modelos eléctricos añadidos.

Los barriles son polígonos de vía huecos con modelo `VOLUME`, relleno `RING`, pared nominal **supuesta** de 25 µm y niveles explícitos. La vía RF atraviesa L1–L4; las otras 87 vías conectan L3–L4. También se modelan los cuatro taladros metalizados de montaje. Los pads y antipads provienen del cobre extraído y no se agregan automáticamente.

El barrido ABS cubre 0,8–1,4 GHz y hay un cálculo discreto a 1,09 GHz. Se solicita almacenamiento de corrientes. Ambas tapas son Free Space y se desactiva de-embedding. La caja nominal es de 1600×1600 mm, con 40 mm de aire a cada lado. La malla inicial de 50 µm **no está convergida**; el gran tamaño de caja y los detalles de las vías pueden requerir muchos recursos.

`stackup.json` conserva los valores del Gerber Job. Los planos de cobre se ubican en los centros de las láminas, separados 0,1415 / 1,260 / 0,1415 mm. Los espesores de metal son 35 / 30 / 30 / 35 µm. El total nominal de 1,598 mm incluye 20 µm de máscaras; cobre más dieléctricos suma 1,578 mm. Las máscaras no se modelan, por falta de propiedades dieléctricas verificadas.

## Reproducir

Desde `simulations/sonnet/adsb_patch`:

```bash
/usr/bin/python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/extract_geometry.py
.venv/bin/python scripts/verify_geometry.py
.venv/bin/python scripts/build_all.py
.venv/bin/python scripts/run_sonnet.py A_real
.venv/bin/python scripts/verify_model.py A_real
```

Se necesita `pcbnew` instalado para el Python del sistema. `extract_geometry.py --pcb /ruta/ads-b.kicad_pcb` permite cambiar la fuente; debe tener al lado los archivos de proyecto/esquemático y `gerber/`. Las advertencias de fuentes tipográficas no afectan al cobre. Los scripts no rellenan zonas ni guardan el PCB.

Para simular cuando funcione la licencia:

```bash
.venv/bin/python scripts/run_sonnet.py A_real --analyze --timeout 86400
.venv/bin/python scripts/postprocess_s11.py models/A_real_ready.s1p
```

Las macros también se pueden ejecutar desde `macros/`: `runmacro -v A_real_prepare.smc` para verificar/guardar, o `runmacro -v A_real_run.smc` para analizar. Las rutas relativas presuponen ese directorio. Cada ejecución deja su registro y estado JSON en `reports/`. Una verificación sintáctica satisfactoria no acredita la validez electromagnética.

## Comparaciones preparadas

| Caso | Único cambio respecto de A |
|---|---|
| `A_real` | Base con cobre y barriles reales; pared de barril supuesta |
| `B_no_rf_barrel` | Se retira solamente el barril RF; quedan pads, pistas y despejes |
| `C_rf_wall_010` / `C_rf_wall_035` | Pared RF de 10 / 35 µm, manteniendo taladro y cobre planar |
| `mesh_100um` / `mesh_025um` | Celda de 100 / 25 µm |
| `box_2000mm` / `box_2400mm` | Caja de 2000 / 2400 mm; celda constante |
| `air_30mm` / `air_50mm` | Aire de 30 / 50 mm por lado |
| `loss_assumed_016` | tanδ=0,016 en los tres dieléctricos; hipótesis ilustrativa |

B es un control con vía abierta, **no una conexión ideal de inductancia cero**. No se entrega como equivalente ideal. Dado que el patch está separado del pad, trasladar el puerto al patch o puentear el despeje cambiaría el mecanismo de excitación. La comparación con un modelo de alimentación ideal queda pendiente de definir ese mecanismo; no se atribuirán sus diferencias exclusivamente a la vía.

Con licencia disponible, resolver primero cada caso y extraer S11 complejo, mínimo de adaptación, Zin y VSWR. Criterios propuestos para aceptar convergencia entre refinamientos sucesivos: desplazamiento del mínimo <0,5 %, diferencia compleja de S11 a 1090 MHz <0,02 y cambio de Zin <2 Ω; comprobar además la forma de toda la curva, modos y distribución de corriente. Aplicar esos criterios también a tamaño de caja y altura de tapas antes de aceptar resultados de antena. Son criterios de trabajo, no resultados ni requisitos previamente aprobados.

El postprocesador entrega CSV, gráfico S11 y métricas desde un Touchstone auténtico. Identifica el mínimo de adaptación; no lo confunde automáticamente con una resonancia modal. No interpola un resultado a 1090 MHz si falta ese punto. Ganancia, polarización, relación axial y campos requieren el análisis de corrientes/campos y la herramienta de campo lejano; no se derivan de S11.

## Referencias

Sonnet recomienda centrar la antena, usar tapas Free Space con planos de masa finitos y estudiar la caja; sus paredes laterales siguen siendo conductoras y el dieléctrico uniforme se extiende hasta ellas. La caja inicial sigue su recomendación de aproximadamente cuatro longitudes de onda más la antena a la frecuencia inferior: [Antennas and Radiation, 19.54](https://www.sonnetsoftware.com/support/doc_19.54/Topics/Antennas_and_Radiation/Antennas_and_Radiation.htm).

El barril hueco y su discretización se describen en [Via Tech Layers](https://www.sonnetsoftware.com/support/doc_19.52/Topics/Creating_Your_Stackup/Tech_Layers/Via_TechLayers.htm). El puerto interno y su referencia flotante se documentan en [Port Type Overview](https://www.sonnetsoftware.com/support/help-18/users_guide/PortTypeOverview.html).

La [ficha KB-6165F alojada por JLCPCB](https://rs.jlcpcb.com/static/file/kb-6165f-datasheet.pdf) ofrece valores de pérdidas para construcciones específicas. No identifica el laminado realmente contratado de esta PCB; su valor representativo no certifica `JLC2116` ni `JLC Core`. Por eso el modelo base mantiene tanδ=0 declarado en KiCad y el caso 0,016 está marcado como supuesto.

Para una prueba mínima ya resuelta de patch + GND, ver [README_simple.md](README_simple.md).
