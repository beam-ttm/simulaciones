# Verificación geométrica

Vía RF: [81.41011, 85.30994] mm; pad 0.4 mm; taladro 0.3 mm.
Despeje medido entre pad y relleno F.Cu: 0.254500 mm.
**El patch F.Cu no está unido galvánicamente al pad RF en el archivo fuente.** No se agregó cobre para corregirlo.

| Capa | Área KiCad mm² | Área Gerber mm² | Diferencia fuera de 2 µm mm² | Coincide |
|---|---:|---:|---:|---|
| F.Cu | 4463.457765 | 4463.444424 | 0 | True |
| In1.Cu | 5817.624832 | 5817.611491 | 0 | True |
| In2.Cu | 5781.132072 | 5781.119395 | 0 | True |
| B.Cu | 5590.722051 | 5590.729529 | 0 | True |

Se conservan los rellenos almacenados; no se ejecutó refill ni se guardó el PCB original.
Comparación de Gerbers después de restar taladros. El JSON contiene diferencias y cotejo de vías contra Excellon.
Contorno Edge.Cuts contra línea central Gerber: diferencia de área 0 mm²; distancia Hausdorff 0 mm.
Las comprobaciones geométricas no validan los sólidos dieléctricos ni la convergencia electromagnética.
