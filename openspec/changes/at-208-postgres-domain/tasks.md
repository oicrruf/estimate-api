# Tasks

## 1. Contrato y esquema

- [x] 1.1 Confirmar la versión de CLI y crear una migración AT-208 con `supabase migration new`; verificar nombre y que solo incluye tablas de esta issue.
- [x] 1.2 Crear proyectos, membresías, entidades, relaciones, paquetes y catálogo con FKs e índices; verificar rechazos de duplicados y referencias cruzadas en PostgreSQL descartable.
- [x] 1.3 Crear ofertas históricas, presupuestos, líneas, snapshots y auditoría sin política de cálculo; verificar fechas, unicidad del presupuesto activo y conservación del historial.

## 2. Seguridad y pruebas

- [x] 2.1 Definir grants de mínimo privilegio, RLS para todas las tablas públicas y funciones privadas; verificar dos usuarios/dos proyectos, roles y fallo cerrado sin identidad.
- [x] 2.2 Probar auditoría automática y ausencia de mutaciones directas en historial; verificar actor y rechazo de falsificación en la base local.
- [x] 2.3 Ensayar backup, restore y reversión en bases descartables; comparar recuentos y documentar comandos, límites y resultado.

## 3. Integración de artefactos

- [x] 3.1 Ejecutar OpenSpec, pruebas SQL y controles de secreto sobre el diff; registrar resultados y solicitar checkpoint de revisión de seguridad antes de integrar.

## 4. Cobertura restante del objetivo AT-208 (bloquea Done)

- [x] 4.1 Modelar países, proveedores, sucursales, contactos privados, clientes por proyecto, identidad acumulativa de productos, especificaciones, fuentes y garantías sin mezclar candidatos de proyecto.
- [x] 4.2 Modelar candidatos, selecciones, evaluaciones, servicios y observaciones históricas de tarifas como datos fundacionales; dejar la política de cálculo a AT-224.
- [x] 4.3 Implementar y probar comandos transaccionales para declaraciones/evidencia curada, paquete versionado, cliente, tarifa, presupuesto, línea y borrador canónico, con autorización, idempotencia y revisión; la emisión queda en AT-222. Mantener bloqueadas mutaciones arbitrarias de hechos, evidencia y snapshots.
- [x] 4.4 Quitar DML directo de proyecto/membresía y probar creación, edición, transferencia y reintentos; alinear bloqueo proyecto→membresía y probar carrera en dos sesiones.
- [x] 4.5 Sustituir propiedad BYPASSRLS de auxiliares/mutadores/auditoría por roles NOLOGIN NOBYPASSRLS con grants/políticas acotadas; verificar localmente que el backend no tiene DML directo.
- [x] 4.5a Rechazar propietarios auxiliares LOGIN o asumibles por roles de cliente/backend/sesión ordinaria; probar admisión negativa en PostgreSQL descartable.
- [x] 4.5b Conservar evaluación adversa posterior a selección, superseder la selección activa y ordenar evaluaciones de una transacción por secuencia monotónica; probar reintento y selección vigente.
- [ ] 4.6 Probar topología exacta de conexión SQL, membresía del migrador, grants y roles en un stack Supabase local compatible; no atribuir compatibilidad a la base PostgreSQL simulada.
- [ ] 4.7 Revisar independientemente SQL, roles, evidencia fijada, modelo de autorización/idempotencia y tests; verificar CI del SHA final antes de integrar.

## Workflow follow-up

- Las specs vigentes reflejan el subconjunto probado; el cambio AT-208 sigue activo y se archivará al completar los requisitos pendientes.
- Mantener PR draft y no hacer merge ni actualizar Linear hasta revisión independiente, prueba de compatibilidad de roles y gates aplicables. FastAPI/JWT permanece en AT-209.
