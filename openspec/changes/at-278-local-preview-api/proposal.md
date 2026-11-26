# Propuesta: HTTP local de evaluación sintética (AT-278)

## Why

La prueba del dueño requiere que Angular consuma el resultado real de AT-227 mediante HTTP, sin convertir la demo en una ruta productiva.

## What Changes

- Servidor FastAPI independiente, enlazado sólo a `127.0.0.1`, con una operación GET versionada y tipada.
- Parámetros cerrados por escenario; evaluación ADK/Relate real sobre store local sembrado por la CLI existente.
- Pruebas de HTTP, reapertura entre procesos, errores y CI con extra `demo`.

## Impact

Se usan únicamente fixtures ficticios. No se monta la ruta en `estimate_api.app`, no se configura CORS, no se aceptan consultas ni rutas de archivos del cliente. La pantalla Angular y la entrega al dueño son trabajo de integración aparte; este cambio no completa AT-278.
