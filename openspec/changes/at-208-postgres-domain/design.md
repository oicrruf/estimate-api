# Design

## Context

El `develop` de partida es `c503575e152430908da3f0bb56317867e77d26c9`; se revisó también `3adf52e2ff71556df1cddc95282a958d3b8e892e`. ADR 0001 elige Supabase PostgreSQL, Auth y Storage; AT-264 fija trece tipos de entidad y paquetes por sujeto. Se leyó la descripción completa de AT-208 en Linear el 26/11/2026. El changelog de Supabase de esa fecha indica cambios importantes de CLI v3; los comandos se verifican con `--help` y ninguna operación apunta al proyecto alojado.

Referencias de semántica RLS: [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security) y [PostgreSQL 17 row security](https://www.postgresql.org/docs/17/ddl-rowsecurity.html). En particular, FORCE RLS también somete al propietario normal; un rol con BYPASSRLS lo omite. La prueba local reproduce explícitamente ese requisito y rechaza un propietario sin él.

## Goals / Non-Goals

**Goals:** esquema versionado que haga imposible una relación entre proyectos distintos, guarde historia comercial sin calcular precios y haga cumplir RLS/privilegios bajo identidad autenticada. Probar dos usuarios y dos proyectos en PostgreSQL descartable, incluido backup y restore de ensayo.

**Non-Goals:** validar JWT, configurar Supabase Auth o Storage alojados, exponer API de producción, importar catálogo real, calcular tarifas/impuestos o desplegar. AT-209 se encarga de la autenticación del servicio; AT-224 es propietario de la política de precios.

## Decisions

1. **Identidad de tenant.** `projects` tiene `id` UUID y `owner_user_id` que referencia `auth.users`. La propiedad no se actualiza mediante UPDATE directo de usuario. `project_memberships` contiene solo `editor` o `viewer`, clave `(project_id,user_id)`; el propietario se deriva de `projects`, sin fila duplicada. Una función privada de transferencia exige actor igual al propietario actual y destino miembro editor, bloquea la fila de proyecto, cambia el propietario y convierte al anterior en editor dentro de la misma transacción. Su invocación desde API con JWT verificado pertenece a AT-209.
2. **Core y referencias.** `project_entities` guarda el sobre universal (tipo, etiqueta, origen, ámbito, revisión, estado) y JSON de datos no normativos. `project_relations` y `project_packages` usan claves compuestas `(project_id,entity_id)` para referenciar sujeto y destino del mismo tenant. El catálogo `catalog_items` es global, versionado y de lectura para usuarios autenticados; su escritura queda fuera de privilegios de usuario. No se codifica un rubro en el esquema.
3. **Historia comercial.** `project_offers` es append-only, con proveedor de referencia, moneda, precio observado `numeric(18,4)`, fechas de observación y vigencia; no calcula tasas ni impuestos. `project_budgets` tiene índice único parcial para **como máximo** un presupuesto activo; un proyecto recién creado puede no tener presupuesto hasta que la API lo cree. `budget_lines` usa FKs compuestas a presupuesto y oferta del mismo proyecto. `proposal_snapshots` es append-only y guarda representación JSON versionada de la propuesta; ninguna tabla de historial admite UPDATE/DELETE a roles de usuario.
4. **RLS, propietario y roles.** Todas las tablas `public` nuevas tienen RLS. Los tres auxiliares de lectura de propiedad/membresía pertenecen a `at208_policy_owner`, un rol `NOLOGIN NOBYPASSRLS` con SELECT solo en `projects`/`project_memberships` y políticas específicas para esas lecturas, evitando recursión aun con FORCE RLS. Las funciones mutadoras todavía pertenecen al migrador `BYPASSRLS` local; el SQL falla al inicio si no tiene esa capacidad. La prueba usa un migrador sintético no superusuario y un rol SQL `at208_backend` sin BYPASS ni DML, con EXECUTE solo de la operación de oferta. No se usa `service_role` como ruta RPC. Roles, membresías y conectividad reales del proyecto alojado son gates de despliegue pendientes, no una compatibilidad comprobada. `anon` no recibe acceso. El contexto de `auth.uid()` solo es confiable tras JWT validado; el harness local lo simula y nunca se instala en producción.
5. **Auditoría.** Un trigger privado registra mutaciones de tablas de proyecto con `auth.uid()` y metadatos mínimos. Rechaza actor ausente. La función no copia `facts`, precio ni snapshot al log. Su propietario privilegiado solo escribe en `audit_events`; no se expone como RPC. Pruebas revisan que el evento aparece y que roles de usuario no pueden falsificarlo ni editarlo.
6. **Límite de escritura confiable.** Se retiran las escrituras directas de `authenticated` sobre entidades, paquetes, ofertas, presupuestos, líneas y snapshots. `private.record_project_offer`, `record_project_candidate`, `record_project_evaluation` y `select_project_candidate` son operaciones SQL separadas para el backend: exigen actor que FastAPI deberá validar, autorización de editor en la base, idempotencia por proyecto/clave/payload, evidencia y actualización atómica de revisión. `at208_backend` solo puede ejecutarlas, sin DML directo; `service_role` no puede invocarlas. Las otras operaciones comerciales aún no tienen servicio autorizado y quedan bloqueadas; AT-208 no está listo para Done. Un snapshot es únicamente un borrador inmutable, sin permiso de emisión; la emisión con revisión canónica/evidencia/aprobación corresponde a AT-222. Los triggers de cambios dependientes aumentan la revisión del proyecto y de presupuesto cuando aplica; el contrato completo de invalidación de cálculos debe revisarse antes de integrar operaciones pendientes.
7. **Integración y reversión.** La migración se crea con la CLI oficial y no se aplica al proyecto alojado. El ensayo local restaura una copia previa en una base descartable; en producción una migración correctiva es preferible a borrar datos. `pg_dump`/`pg_restore` de prueba comprueban esquema y datos sintéticos. No hay tabla de precios calculados ni política duplicada de AT-224.
8. **Entidades comerciales fundacionales.** `countries`, `suppliers` y `supplier_branches` son directorios compartidos de lectura; `supplier_contacts` y perfiles de cliente viven en `private` sin permisos de cliente. `project_customers`, candidatos, evaluaciones y selecciones se vinculan siempre por `project_id` y FKs compuestas. `product_specs`, fuentes, equivalencias verificadas y garantías mantienen la identidad global deduplicada por marca/modelo/SKU aun si un proyecto descarta el candidato. Las ofertas enlazan proveedor/sucursal/fuente y conservan observaciones históricas; las tarifas de servicio son observaciones fechadas, no reglas de cálculo. Ninguna tabla nueva concede DML directo a `authenticated`, `service_role` o `at208_backend`; sus rutas mutadoras de servicio permanecen pendientes.

## Riesgos / Trade-offs

- [Función `SECURITY DEFINER` puede ampliar permisos] → esquema no expuesto, búsqueda fija, revocación explícita y tests de acceso; revisar en checkpoint de seguridad.
- [Una sesión SQL puede falsificar el GUC de JWT si posee conexión directa] → no conceder conexión directa a usuarios; AT-209 valida JWT y usa contexto de identidad confiable. El harness local no prueba autenticación.
- [Rol de servicio omite RLS] → reservarlo a migración/admin; no usarlo para requests de usuario ni en frontend.
- [Ofertas/snapshots crecen] → índices por proyecto/fecha y retención posterior; no aplicar borrados automáticos en AT-208.
- [Índice parcial garantiza solo máximo uno activo] → API crea primer presupuesto en transacción y maneja conflicto 23505; no proclamar existencia obligatoria.
- [Restore puede perder datos posteriores al backup] → probar recuperación con fixtures, documentar RPO/RTO antes de producción.
- [Cobertura parcial del issue] → faltan países, proveedores/sucursales/contactos, clientes, deduplicación y especificaciones de producto, candidatos/selecciones/evaluaciones, servicios/tarifas y sus transacciones. Mantener el PR draft y AT-208 In Progress; no afirmar cumplimiento del objetivo completo.

## Migration Plan

1. Validar OpenSpec antes de escribir SQL. Crear migración con `supabase migration new` verificado por `--help`.
2. Aplicar sobre PostgreSQL 17 descartable con roles Supabase y `auth.uid()` simulados **solo en harness local**; ejecutar pruebas de esquema, RLS, FKs, historial y auditoría.
3. Exportar la base sintética y restaurar en otra base descartable; verificar recuentos, restricciones y RLS. Ensayar reversión en copia, no en base alojada.
4. Publicar propuesta para revisión fresca de diseño de RLS, funciones privilegiadas y matriz de acceso; esperar checkpoint antes de integrar. No tocar Supabase alojado.

## Checkpoint de revisión antes de integrar

Revisor independiente debe examinar superficie `public`, cada GRANT y política, funciones privadas privilegiadas, FKs de tenant, protección del propietario, actor de auditoría, test de roles reales y plan de rollback. La aprobación se refiere al diff SQL y resultados reproducibles, no a una afirmación de seguridad de JWT o del proyecto alojado.
