# AT-247: patrones de instalación versionados

## Why

El registro AT-265 referencia patrones, pero no define su grafo ni la evaluación condicional. Se requiere una derivación sintética y reproducible sin convertir datos desconocidos en selección.

## What Changes

- Agregar contrato tipado y fixture versionada para cámara PoE, mesh, EMT, gabinete y energía.
- Evaluar relaciones condicionales con evidencia confirmada, límites de expansión y deduplicación.
- Cargar el grafo sintético en Relate de forma idempotente y consultar rutas de evidencia.
- Reservar una salida tipada para la propuesta AT-240 sin integrarla.

## Impact

Sólo archivos nuevos; no cambia AT-238, AT-265, esquemas universales ni servicios. La salida exige revisión profesional y no afirma cumplimiento normativo.
