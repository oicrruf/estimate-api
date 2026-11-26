# AT-227 — Vertical ejecutable ADK + Relate

## Why

AT-229 dejó un grafo ficticio y consultas reproducibles, pero no una entrada de usuario que conecte selección, evidencia y persistencia local. La demo H0 necesita una ejecución determinista y pública sin proveedor de modelo ni credenciales.

## What Changes

- CLI con `seed`, `evaluate` y `demo`, ruta de archivo Relate explícita y salida JSON estructurada.
- Agente ADK Python sin LLM que invoca herramientas de consultas Cypher fijas y de sólo lectura; validación y selección deterministas.
- Pruebas con Relate real de switch de 8 frente a 16 puertos, cambio tipado de puertos PoE, pool 2 de 4 y UPS; cierre y reapertura desde otro proceso.
- Instrucción reproducible y CI aislada para esta entrada de demo.

## Out of Scope

No se implementa UI, endpoint canónico FastAPI, LLM remoto, catálogo real, inventario transaccional, credenciales de producción, despliegue ni publicación externa. El ejemplo OpenAPI de AT-229 continúa siendo planificado.
