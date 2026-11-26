# Proposal

## Why

AT-206 necesita una decisión verificable de arquitectura antes de AT-207 y de cualquier persistencia o despliegue. Los repositorios ya tienen una base documental mínima; el diseño debe distinguir lo aprobado, lo comprobado y lo pendiente para no declarar la plataforma implementada.

## What Changes

- Registrar el ADR de límites entre core universal, paquetes de conocimiento versionados, identidad, datos, objetos y runtime.
- Definir contratos iniciales de entrada/salida y controles exigibles a operaciones mutables.
- Comparar Supabase PostgreSQL con D1 y documentar la ruta local/demo con Relate Python, Dockploy previsto, riesgos, costes, backups y rollback.
- Registrar una secuencia de bootstrap de referencias Git compatible con OpenSpec, revisión, historial lineal y un commit por issue y repositorio afectado.

## Capabilities

### New Capabilities

- `project-knowledge-boundary`: el core interpreta proyectos y paquetes técnicos versionados sin codificar una especialidad ni prometer validez normativa universal.
- `protected-project-operations`: las operaciones de proyecto exigen identidad, autorización por recurso, idempotencia y auditoría.
- `platform-data-boundary`: fuente de verdad, almacenamiento privado y límites de ejecución definidos para el MVP.

### Modified Capabilities

Ninguna; el repositorio todavía no tiene especificaciones vigentes.

## Impact

Documento ADR y especificaciones en `estimate-api`; contratos futuros de FastAPI, Supabase y Relate. `estimate-app` consumirá el contrato OpenAPI cuando AT-207 inicialice ese repositorio de forma independiente. No se cambia código, esquema, servicios ni datos en AT-206.
