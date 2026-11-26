# Proposal

## Why

AT-208 necesita convertir el contrato universal de proyecto y la decisión PostgreSQL del ADR 0001 en persistencia versionada con integridad e aislamiento comprobables. El backend aún no tiene esquema de aplicación; los ejemplos y fixtures actuales no establecen permisos entre usuarios.

## What Changes

- Crear migración inicial para proyectos, membresías, entidades y relaciones universales, paquetes asociados, catálogo reutilizable, ofertas históricas, presupuestos, snapshots y auditoría.
- Aplicar claves compuestas por proyecto, restricciones de vigencia e índices para impedir referencias entre tenants y más de un presupuesto activo.
- Definir privilegios mínimos y RLS por identidad validada y pertenencia; la prueba local simula la identidad únicamente en un PostgreSQL descartable.
- Documentar restauración/reversión, límites del rol de servicio y pruebas positivas/negativas con dos proyectos sintéticos.

## Capabilities

### New Capabilities

- `project-persistence`: almacenamiento relacional versionado y trazable de proyectos, catálogo global, ofertas, presupuestos, snapshots y auditoría.
- `project-data-isolation`: permisos por proyecto, referencias del mismo tenant y rechazo por defecto de identidades ausentes o no autorizadas.

### Modified Capabilities

Ninguna; `platform-data-boundary` y `protected-project-operations` siguen como contratos de arquitectura. Esta issue concreta el esquema SQL sin cambiar sus requisitos.

## Impact

Solo `estimate-api`: `supabase/migrations/`, documentación de restauración y pruebas SQL locales. No cambia API, frontend, Auth, Storage, precios ni el proyecto Supabase alojado. AT-224 define cálculos y tasas; AT-209 conecta JWT verificados con esta frontera de datos.
