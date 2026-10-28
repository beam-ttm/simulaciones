# Comparación Altium / Sonnet — 2026-10-21

Se leyeron los polígonos TOP directamente de los streams Polygons6/Data de los PcbDoc, sin modificar los originales. El feed se extrajo mediante el importador de Altium de KiCad en memoria y se alineó respecto al centro del patch; la misma importación reprodujo el contorno nativo con diferencia menor que 0,00001 mm. Se leyeron todos los bloques Points de cada polígono XML de Sonnet y se unió el cobre de nivel 0 antes de comparar. Las coordenadas se trasladaron al centro y se invirtió Y de Altium; no hubo escalado ni rotación arbitraria.

## Resultados

- PCB1.PcbDoc y antena_modulo_gnss.PcbDoc de PCB/2-Antena_patch/CubeSat_antenapatch: patch 66,5 × 66,5 mm; dos esquinas diagonalmente opuestas con catetos de 0,65 mm, diagonal aproximada 0,91924 mm. El contorno del antena_modulo_gnss.PcbDoc bajo PCB/1-ADS-B/ads-b-payload/altium también coincide.
- PCB2.PcbDoc: 66,5 × 66,5 mm, sin truncados. No es la variante usada en Sonnet.
- patch.sonx: mismas dimensiones exteriores y ubicación nominal de los truncados. El cobre rellenado presenta redondeos en las esquinas: distancia máxima de contornos respecto al polígono nominal de Altium 0,055943 mm; diferencia de área exterior 0,010392 mm². No son contornos estrictamente idénticos.
- patch_campo_lejano.sonx / patch_simple_barrido.sonx: contorno nominal de seis vértices coincidente; distancia máxima respecto a Altium 0,000003544 mm.
- Feed Altium: aproximadamente X=0 e Y=+19 mm respecto al centro, con Y hacia abajo en el dibujo; a 14,25 mm del borde próximo. Desviación del centro del barrel en patch.sonx: 0,000000707 mm; del centro de la fuente simplificada: 0,000127475 mm.
- La posición no implica una alimentación equivalente. patch.sonx usa la vía RF de la PCB KiCad (pad 0,4 y taladro 0,3 mm) y excitación flotante en D1/B.Cu. El modelo simplificado usa una fuente cuadrada 1 × 1 mm entre patch y primer plano, y rellena el despeje del feed. No reproduce el montaje de alimentación de Altium.
- El importador lee pad Feed de Altium de 0,8 mm y taladro 1,27 mm. Ese taladro supera el diámetro del pad: se conserva la anomalía como resultado de importación, pendiente de confirmar en Altium nativo; no debe asumirse una alimentación equivalente ni un diseño fabricable basándose en esta lectura. No se verificó el stackup de Altium; hubo avisos de planos internos no mapeados.

## Escalonado de las esquinas

Los archivos usan malla rectangular. La geometría nominal tiene diagonales; el metal discretizado puede verse escalonado. patch.sonx: celda 0,05 mm, unos 13 intervalos por cateto del recorte. Modelos simplificados: celda 0,5 mm, unos 1,3 intervalos. Este último caso resuelve mal la perturbación responsable de separar los modos de polarización. No se cuantificó el error de frecuencia, ganancia o relación axial.

Probar celdas 0,1 y 0,05 mm en copias del mismo modelo y comparar S11, AR y ganancia; refinar más si no convergen. Diagonal Edges permite subsecciones triangulares y puede mejorar diagonales, sin garantizar su coincidencia exacta ni sustituir una prueba de convergencia. Conformal tampoco elimina necesariamente el escalonado de la celda base.

La relación axial de 54,56 dB obtenida anteriormente corresponde al simplificado de celda 0,5 mm y feed artificial. No demuestra que la PCB real tenga polarización lineal.

No se cambió ningún PCB ni modelo Sonnet, ni se ejecutó otra simulación. Valores y hashes: altium_sonnet_comparison.json. Vista superpuesta: altium_sonnet_comparison.png.

Referencia: https://www.sonnetsoftware.com/support/doc_19.54/Topics/Subsectioning/Subsectioning.htm
