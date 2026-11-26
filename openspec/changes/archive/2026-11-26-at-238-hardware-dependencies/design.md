# Diseño

## Entrada y salida

El paquete recibe un catálogo de tipos genéricos con evidencia y una ruta sintética. Una ruta confirmada aporta longitudes por sección, extremos que entran a caja, uniones y puntos de soporte observados. Esos datos se consideran observaciones de la fixture, no una fórmula de instalación. El resultado incluye líneas de material, reglas y IDs de evidencia, faltantes, accesorios seleccionados incompatibles y alternativas compatibles. Una ruta sin confirmación produce pendientes y ninguna cantidad inferida.

## Cantidades

Cada sección se redondea a unidades comerciales de EMT según la longitud de la pieza del catálogo; las uniones, entradas y soportes se toman de conteos explícitos confirmados. El desperdicio sólo se aplica si se proporciona explícitamente. Un cambio de dirección o gabinete no crea LB o toma interior automáticamente. Ninguna línea contiene costo.

## Grafo

El seed ficticio aislado usa `INSTALLATION_SEGMENT`, `MATERIAL`, `ACCESSORY`, `ENCLOSURE`, `REQUIREMENT`, `SPEC` y `EVIDENCE`. Las aristas `REQUIRES`, `FITS_DIAMETER`, `CONNECTS_TO`, `MOUNTS_TO`, `SUPPORTED_BY` y `ALTERNATIVE_TO` tienen IDs/reglas estables. Los tipos genéricos no se confunden con productos de fabricante. Una consulta Cypher verifica rutas a evidencia y compatibilidad.

## Límites

La evaluación no decide normativa, capacidad/llenado, ambiente, separación de soportes ni seguridad eléctrica; marca `professionalValidationRequired`. El paquete se puede integrar en flujos posteriores sin acoplarlo a escenarios o persistencia SQL.
