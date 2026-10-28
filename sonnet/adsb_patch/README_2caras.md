# Patch de dos caras, FR-4 de 1,6 mm

Proyecto principal: `sonnet/patch_2caras.sonx`. Patch y GND finito, sin electrónica receptora, excitados por una sonda ideal de 50 Ω. Los proyectos anteriores de 1,4 mm y los diagnósticos de caja pequeña no deben usarse como resultados finales de este modelo.

## Modelo físico

- Patch de 66,5 × 66,5 mm; dos esquinas diagonalmente opuestas con catetos recortados de 0,65 mm.
- GND continuo de 76 × 76 mm. No se incluyen aperturas de conectores: la alimentación solicitada es ideal.
- Feed en X=0, Y=19 mm respecto al centro del patch. Sonda circular sólida de diámetro 0,8 mm supuesto, conectada directamente al patch y al puerto entre las caras; referencia de 50 Ω. No incluye conector ni cable.
- **Espesor dieléctrico FR-4: 1,6 mm por instrucción del usuario**, sustituyendo los 1,4 mm del Altium PCB1. Esto se interpreta como FR-4 sin sumar cobre.
- εr=4,4 del CAD. tanδ=0,02 supuesto. Cobre liso σ=5,8×10⁷ S/m y espesor de 0,0999998 mm por cara, leído del Altium. El espesor exterior total modelado es aproximadamente 1,8 mm.
- Modelo Thick Metal de dos láminas por conductor: patch hacia arriba y GND hacia abajo, ambos dentro del aire; la separación libre entre metales conserva los 1,6 mm de FR-4. No se añade cobre al espesor dieléctrico.
- Máscara y bordes del sustrato finito omitidos. Sonnet considera un dieléctrico uniforme extendido lateralmente hasta infinito en el cálculo de campo lejano. No equivale a una validación de la placa fabricada.

## Discretización y dominio

Malla rectangular, **Diagonal Edges desactivado**: Sonnet 19.54 omite la radiación de las subsecciones triangulares en el visor de campo lejano. Por eso se verifica la aproximación escalonada mediante refinamiento de celda, en vez de usar triángulos para ocultar el escalonado.

La caja principal mide 1638,4 × 1638,4 mm. Tiene 16384 celdas por eje con paso 0,1 mm, o 32768 con paso 0,05 mm: dimensiones de grilla en potencias de dos. Geometría centrada y tapas superior e inferior Free Space. Aire inicial de 40 mm por lado. El tamaño principal cumple la recomendación de Sonnet de cuatro longitudes de onda más la antena incluso a 800 MHz.

Comparaciones a **1090 MHz**:

1. Caja 1638,4 mm, aire 40 mm: celda 0,1 frente a 0,05 mm.
2. Celda 0,1 mm y aire 40 mm: caja 1228,8 frente a 1638,4 mm. Ambas cumplen el mínimo de cuatro longitudes de onda más la antena a 1090 MHz; la caja menor no se propone para todo el barrido desde 800 MHz.
3. Caja 1638,4 mm y celda 0,1 mm: aire 40 frente a 50 mm por lado. La distancia eléctrica entre tapas sigue por debajo de media longitud de onda a la frecuencia de prueba.

Los primeros cálculos de caja 400 mm son diagnósticos del flujo de exportación y **no validan el espacio libre**. Los casos triangulares y los de 1,4 mm fueron retirados del servidor al ser sustituidos.

## Resultados y criterio

La finalización de `runmacro analyze` no significa que el solver haya terminado. Se requiere el final correcto de emclient, cero errores del solver y los datos de corrientes transferidos. No editar ni regenerar proyectos durante el análisis.

Los campos se exportan con el propio visor Sonnet mediante `sonnet -Additional -farfield -template ... proyecto.sonx -csv salida.csv`. Los gráficos se generan exclusivamente a partir de esos datos. Las plantillas no contienen campos copiados de otro proyecto.

`results/patch_2caras_h16/convergencia.json` identifica cada caso y los resultados disponibles. Los criterios seleccionados son: |ΔS11|≤0,1 dB, |ΔΓ|≤0,005, |ΔZin|≤1 Ω, diferencia de Power Gain≤0,2 dB en toda la esfera donde ambos casos estén a menos de 20 dB del máximo, además de los cortes φ=0/90 y θ=−60…60°, y diferencia del desequilibrio circular normalizado≤0,02 en θ=0. Cuando AR<10 dB en cualquiera de los casos se exige además |ΔAR|≤0,2 dB. Cerca de polarización lineal la AR es muy sensible y el visor la limita a 40 dB; se calcula la AR sin ese límite usando las magnitudes RHCP/LHCP exportadas, y se usa el desequilibrio circular como criterio de estabilidad.

Son pruebas de convergencia a un punto y en las direcciones indicadas, no de toda la banda ni de la placa real. El proyecto principal contiene el punto de 1090 MHz. `sonnet/patch_2caras_barrido.sonx` contiene un barrido ABS 0,8–1,4 GHz; prepararlo no implica que ese barrido ya esté calculado.

## Reproducir

Desde el workspace, con ningún caso objetivo en análisis:

```
simulations/sonnet/adsb_patch/.venv/bin/python simulations/sonnet/adsb_patch/scripts/generate_two_sided.py
```

Opciones `--box-mm`, `--cells` y `--air-mm` generan los casos de comparación; `--no-main` conserva el proyecto principal al crear un caso auxiliar. Ejecutar las macros `_prepare.smc` con runmacro para verificar y guardar el formato nativo. La ejecución remota se realiza con emclient apuntando al proyecto concreto en `sonnet/`, servidor 10.16.100.159:56150.

Después de completados los casos:

```
simulations/sonnet/adsb_patch/.venv/bin/python simulations/sonnet/adsb_patch/scripts/evaluate_two_sided.py CASO_REFERENCIA CASO_MALLA_FINA CASO_CAJA CASO_AIRE --sphere
```

La opción `--sphere` exporta 2664 muestras de Power Gain de Sonnet para la esfera completa del último caso y guarda una figura 3D. El radio del dibujo representa magnitud de campo normalizada y el color Power Gain; no se interpola una simulación EM ni se generan campos analíticos sustitutos.

Referencias del fabricante:

- https://www.sonnetsoftware.com/support/doc_19.54/Topics/Antennas_and_Radiation/Antennas_and_Radiation.htm
- https://www.sonnetsoftware.com/support/doc_19.54/Topics/Graphs_and_Patterns/Far_Field_Patterns/ff_pat_overview.htm
- https://www.sonnetsoftware.com/support/doc_19.54/Topics/Graphs_and_Patterns/Common/scripting.htm

## Ajuste por memoria del servidor

La combinación caja 1638,4 mm / celda 0,05 mm falló antes de resolver: Sonnet solicitó 34 GB y el servidor dispone de 32 GB. No produjo S11 ni campo válidos. La prueba de malla fina se trasladó a la caja de 1228,8 mm, que todavía supera cuatro longitudes de onda más el GND a 1090 MHz. Se compara con el caso de celda 0,1 mm de esa misma caja, sin mezclar ambos cambios. La prueba de frontera compara por separado cajas 1228,8 / 1638,4 mm con la misma celda de 0,1 mm.

El modelo principal de un punto corresponde por ello a caja 1228,8 mm y celda 0,05 mm. El barrido separado conserva caja 1638,4 mm y celda 0,1 mm; no se afirma convergencia del barrido. Los resultados finales sólo se pueden aceptar si las comparaciones independientes pasan sus tolerancias.

Para reproducir las parejas del estudio en el orden REFERENCIA_GRANDE, CAJA_MENOR, AIRE_50, MALLA_FINA, añadir `--pair 1 3 --pair 1 0 --pair 0 2 --sphere` al evaluador.

## Estado posterior del refinamiento

El servidor dejó de responder en el intento 1228,8 mm / 0,05 mm; no se generaron S11 ni corrientes finales válidas, aunque emclient terminó su postprocesado sin un código de error útil. El evaluador exige la finalización real del solver y no acepta ese archivo Touchstone vacío.

La siguiente malla es 0,075 mm en caja 1228,8 mm: 16384 celdas por eje, con geometría física idéntica y aproximadamente 8,67 intervalos por cateto del truncado. Se debe comparar con 0,1 mm en la misma caja. Esto no sustituye una validación con 0,05 mm: el límite de recursos y el grado de convergencia logrado se informarán expresamente en los resultados.
