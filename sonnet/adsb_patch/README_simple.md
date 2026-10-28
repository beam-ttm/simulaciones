# Prueba simplificada: patch + GND

Abrir en Sonnet 19 el archivo del workspace `sonnet/patch_simple.sonx` y seleccionar **Launch → Analyze**, servidor `10.16.100.159:56150`.

- `patch_simple.sonx`: un único punto a **1090 MHz**, para comprobar que el solver puede mallar y resolver el modelo.
- `patch_simple_barrido.sonx`: barrido ABS **800–1400 MHz** más el punto a 1090 MHz, para explorar la adaptación después de la prueba inicial.

Se usa el contorno exterior original de seis vértices de F.Cu, incluidas las dos esquinas truncadas. El GND es un rectángulo de 76×76 mm tomado del contorno de la zona In1.Cu y tratado aquí como plano de referencia. No se incluyen los recortes, taladros, pads, pistas, electrónica ni el cobre In2.Cu/B.Cu.

Se conserva el primer dieléctrico del stackup: 0,109 mm, εr=4,6. Los centros de las láminas de 35 y 30 µm quedan separados 0,1415 mm. Es un modelo del patch sobre el plano adyacente In1, no sobre la cara inferior completa de la placa. Se supone tanδ=0 y cobre liso de σ=5,8×10⁷ S/m.

Para excitar el patch se elimina el despeje alrededor del punto RF y se coloca un **via port de 50 Ω entre patch y GND**, con sección cuadrada artificial de 1×1 mm cerca de las coordenadas de alimentación originales. No reproduce el barril físico de 0,3 mm ni el mecanismo de acoplamiento de la placa original. Esta modificación es intencional para aislar la prueba de funcionamiento.

La caja tiene 1600×1600 mm y 40 mm de aire a cada lado, con tapas Free Space. La malla es RECTANGULAR, con celdas de 0,5 mm: 3200×3200 frente a 32000×32000 del modelo completo. La cantidad de celdas es cien veces menor; eso no garantiza que tiempo y memoria se reduzcan en esa misma proporción. La discretización es gruesa y no está convergida.

La generación es reproducible desde este directorio:

```bash
.venv/bin/python scripts/generate_simple.py
.venv/bin/python scripts/run_sonnet.py patch_simple
.venv/bin/python scripts/run_sonnet.py patch_simple_barrido
```

Los proyectos preparados se guardan en `models/patch_simple_ready.sonx` y `models/patch_simple_barrido_ready.sonx`. Las copias para abrir desde Sonnet están en `sonnet/`, en la raíz del workspace. La prueba remota también puede iniciarse desde Linux con:

```bash
emclient -Server 10.16.100.159:56150 -ProjectName /home/alan/Escritorio/CubeSat/sonnet/patch_simple.sonx -Analyze
```

Un resultado de este modelo no certifica la antena real, la polarización ni la independencia de la caja. El archivo JSON `models/patch_simple.json` detalla las simplificaciones. Los registros de la prueba se conservan en `reports/patch_simple_remote_analysis.log` y en `sonnet/sondata/patch_simple/`.

## Prueba ejecutada

El cálculo remoto de un punto a 1090 MHz terminó sin errores ni advertencias: 15 segundos y 354 MB de memoria pico, según el registro del solver. El servidor informa 32 GB de RAM y 24 procesadores lógicos.

Se obtuvo S11 ≈ −0,102 dB y Zin ≈ 0,293 − j1,439 Ω a 1090 MHz: el modelo puede resolverse, pero esta excitación simplificada no está adaptada a 50 Ω. Un solo punto no permite localizar la resonancia. No se ha comprobado convergencia ni patrón de radiación.

Touchstone y métricas: `results/simple/`. Registro completo: `reports/patch_simple_solver.log`. Verificación: `reports/patch_simple_validation.json`.

## Visualizar el punto calculado

Abrir `sonnet/patch_simple_s11.sgrx` desde File → Open de Sonnet. Este gráfico lee directamente `patch_simple.s1p`, muestra símbolos y tiene límites adecuados para el único punto a 1,09 GHz. Evita seleccionar por error una respuesta SID de otro proyecto o un tipo de datos no calculado. Se regenera con `.venv/bin/python scripts/make_simple_graph.py` después de disponer del Touchstone. Para una curva frente a frecuencia hay que ejecutar `patch_simple_barrido.sonx`; el modelo de un punto no contiene ese barrido.

## Corrección de consistencia de resultados

El generador ahora incluye Header con fechas persistentes Created, Modified y Change MEDIUM/HIGH. Antes la ausencia de cabecera hacía que Sonnet asignara nuevas revisiones al leer el archivo. Se verificó que dos ciclos nativos de lectura y escritura mantienen las fechas de revisión. No se cambió el cobre. El intento de repetir la prueba remota después de la corrección no pudo conectarse al servidor.

Para un nuevo análisis se entregan `sonnet/patch_simple_estable.sonx` y `sonnet/patch_simple_barrido_estable.sonx`, con nombres nuevos y cabecera corregida. Cerrar las versiones anteriores sin guardar antes de abrirlos.

El barrido ya exportado se conserva y puede verse en `sonnet/patch_simple_barrido_s11.sgrx`, que lee `patch_simple_barrido_resultados.s1p`. Se extrajo el último bloque de exportación y se ordenaron sus siete frecuencias efectivamente calculadas; no se generaron valores intermedios. Original sin alterar y métricas en `results/simple_barrido/`. El mínimo entre esos siete puntos es −5,585 dB a 1054 MHz; esto no localiza con precisión el mínimo de toda la banda ni valida la antena real.

## Campo lejano calculado desde la interfaz de Sonnet — 21/10/2026

Se calculó el campo lejano a 1090 MHz usando las corrientes guardadas del modelo simplificado. Las operaciones de selección de frecuencia, cálculo, agregado del corte perpendicular, vista 3D, guardado y exportación se realizaron en la interfaz de Sonnet mediante la accesibilidad del escritorio. No se instaló ningún plugin nuevo ni se ejecutó otra simulación EM.

Archivos en `sonnet/` del workspace:

- `patch_campo_lejano_1090_2D.sptx`: patrón polar E-Total, normalización Power Gain (dB), cortes φ=0° y φ=90°, θ de −90° a 90° con paso 5°.
- `patch_campo_lejano_1090_3D.sptx`: vista 3D E-Total a la misma frecuencia, θ de 0° a 180° y φ de −180° a 180°, ambos con paso 5°.
- `campo_lejano_1090_2D.png` y `campo_lejano_1090_3D.png`: exportaciones nativas de Sonnet.
- `campo_lejano_1090_2D.csv`: valores de ambos cortes exportados desde Output → All Curves to Spreadsheet.
- `patch_campo_lejano.sonx` y su carpeta `sondata/patch_campo_lejano`: copia del proyecto y de las corrientes calculadas, para poder reabrir los patrones sin depender de la sesión anterior.

Se normalizaron únicamente los finales de línea CRLF a LF del archivo interpolado que fallaba; se preservaron sus tokens y valores, y se guardó el original. También se corrigió el generador y los proyectos: la frecuencia única STEP lleva Start=1.09 sin Stop ni Step, como en los ejemplos nativos de Sonnet. El intervalo de longitud cero funcionaba en el solver pero fallaba en el visor gráfico. No se cambiaron polígonos ni materiales. Las copias previas están en `reports/windows_line_endings_backup/` y `reports/single_frequency_syntax_backup/`.

Los archivos .sptx contienen datos de campo efectivamente calculados por Sonnet, no campos copiados de un ejemplo. La verificación de archivos y del número de muestras está en `reports/farfield_gui_validation.json`. Se necesita mantener las rutas relativas entre .sptx, .sonx y sondata.

Estos patrones corresponden al modelo simplificado con alimentación idealizada y malla gruesa. No se ha verificado convergencia, polarización circular ni la radiación de la PCB real. La normalización de potencia seleccionada en Sonnet debe conservarse al comparar las curvas.
