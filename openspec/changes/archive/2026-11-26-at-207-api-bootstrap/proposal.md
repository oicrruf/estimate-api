# Propuesta: AT-207 bootstrap de estimate-api

## Why
El ADR AT-206 define la frontera de arquitectura. Se necesita un servicio reproducible y un contrato mínimo verificable para iniciar el trabajo de API y frontend.

## What Changes
- Servicio FastAPI con un único endpoint GET /health y OpenAPI 3.1 versionado.
- Estructura explícita para futuros módulos, sin implementar dominio, persistencia, ADK, MCP ni Relate.
- CI reproducible con lint, tipos, pruebas, contrato, OpenSpec, escaneo de secretos y reglas de PR.
- Docker local sin credenciales productivas.

## Impact
No hay migraciones ni cambios de infraestructura remota. El frontend consumirá el JSON canónico exportado de este repositorio y comprobará su cliente generado contra una referencia versionada.
