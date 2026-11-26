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

- [ ] 4.1 Modelar países, proveedores, sucursales, contactos, clientes, identidad acumulativa de productos, especificaciones, fuentes y garantías sin mezclar candidatos de proyecto.
- [ ] 4.2 Modelar candidatos, selecciones, evaluaciones, servicios y tarifas como datos fundacionales; dejar la política de cálculo a AT-224.
- [ ] 4.3 Implementar y probar operaciones transaccionales de servicio para entidades, paquetes, presupuestos, líneas y snapshots, con autorización, idempotencia, revisión canónica e invalidación; la emisión queda en AT-222.
- [ ] 4.4 Verificar atributos y grants reales del propietario de migración y `service_role` antes de aplicar en Supabase, probar JWT y rutas FastAPI en sus issues, obtener revisión independiente del SQL y CI del SHA final.

## Workflow follow-up

- Las specs vigentes reflejan el subconjunto probado; el cambio AT-208 sigue activo y se archivará al completar los requisitos pendientes.
- Mantener PR draft y no hacer merge ni actualizar Linear hasta completar cobertura, revisión independiente y gates aplicables.
