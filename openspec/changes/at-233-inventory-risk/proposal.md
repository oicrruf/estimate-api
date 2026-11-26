# AT-233: riesgo de inventario con evidencia

## Why

La demo AT-229 muestra dos ofertas de dos cámaras sobre un único pool de dos, pero las cifras publicadas no son confirmación de proveedor. Hace falta una evaluación comercial separada de elegibilidad técnica que preserve procedencia y desconocimiento.

## What Changes

- Contrato tipado de observaciones de oferta y pool, estado, cantidad, proveedor, sucursal, fechas, reposición y evidencia.
- Lector Relate de sólo consulta sobre el grafo sintético AT-229 y observaciones sintéticas adicionales.
- Evaluador de cobertura, brecha y riesgo configurable; dependencias documentadas de pool y distribuidor.
- Pruebas con archivo Relate temporal cerrado y reabierto, más casos negativos.

## Impact

Sólo dominio y pruebas. A2UI, endpoint AT-227, integración de elegibilidad AT-216 y explorador AT-230 quedan pendientes. Ningún contacto o selección automática.
