# Design

## Context

El `develop` de partida es `c503575e152430908da3f0bb56317867e77d26c9`. ADR 0001 elige Supabase PostgreSQL, Auth y Storage; AT-264 fija trece tipos de entidad y paquetes por sujeto. No hay migraciones de aplicación en el checkout. La página de AT-208 no estuvo accesible desde este entorno; alcance y criterios se toman de la delegación y de los contratos del repositorio. El changelog de Supabase del 26/11/2026 indica cambios importantes de CLI v3; los comandos se verifican con `--help` y ninguna operación apunta al proyecto alojado.

## Goals / Non-Goals

**Goals:** esquema versionado que haga imposible una relación entre proyectos distintos, guarde historia comercial sin calcular precios y haga cumplir RLS/privilegios bajo identidad autenticada. Probar dos usuarios y dos proyectos en PostgreSQL descartable, incluido backup y restore de ensayo.

**Non-Goals:** validar JWT, configurar Supabase Auth o Storage alojados, exponer API de producción, importar catálogo real, calcular tarifas/impuestos o desplegar. AT-209 se encarga de la autenticación del servicio; AT-224 es propietario de la política de precios.

## Decisions

1. **Identidad de tenant.** `projects` tiene `id` UUID y `owner_user_id` que referencia `auth.users`. La propiedad no se actualiza mediante UPDATE directo de usuario. `project_memberships` contiene solo `editor` o `viewer`, clave `(project_id,user_id)`; el propietario se deriva de `projects`, sin fila duplicada. Una función privada de transferencia exige actor igual al propietario actual y destino miembro editor, bloquea la fila de proyecto, cambia el propietario y convierte al anterior en editor dentro de la misma transacción. Su invocación desde API con JWT verificado pertenece a AT-209.
2. **Core y referencias.** `project_entities` guarda el sobre universal (tipo, etiqueta, origen, ámbito, revisión, estado) y JSON de datos no normativos. `project_relations` y `project_packages` usan claves compuestas `(project_id,entity_id)` para referenciar sujeto y destino del mismo tenant. El catálogo `catalog_items` es global, versionado y de lectura para usuarios autenticados; su escritura queda fuera de privilegios de usuario. No se codifica un rubro en el esquema.
3. **Historia comercial.** `project_offers` es append-only, con proveedor de referencia, moneda, precio observado `numeric(18,4)`, fechas de observación y vigencia; no calcula tasas ni impuestos. `project_budgets` tiene índice único parcial para **como máximo** un presupuesto activo; un proyecto recién creado puede no tener presupuesto hasta que la API lo cree. `budget_lines` usa FKs compuestas a presupuesto y oferta del mismo proyecto. `proposal_snapshots` es append-only y guarda representación JSON versionada de la propuesta; ninguna tabla de historial admite UPDATE/DELETE a roles de usuario.
4. **RLS y roles.** Todas las tablas `public` nuevas tienen RLS. Todas salvo `audit_events` usan `FORCE ROW LEVEL SECURITY`: el trigger de auditoría necesita insertar como propietario privilegiado aun cuando no existe una política INSERT para usuarios. Se revocan privilegios generales y se otorgan comandos/columnas concretas a `authenticated`; `anon` no recibe acceso. Funciones `private` de comprobación de propietario/membresía evitan recursión de políticas; son `SECURITY DEFINER`, con `search_path` fijado, SQL calificado, sin datos devueltos y permisos `EXECUTE` limitados. Es una excepción revisable por seguridad. El contexto de `auth.uid()` solo es confiable si PostgREST/Supabase o FastAPI han verificado previamente el token; el harness local simula ese contexto y nunca se instala en producción. `service_role`/migrador eluden RLS y quedan fuera de operaciones de usuario.
5. **Auditoría.** Un trigger privado registra mutaciones de tablas de proyecto con `auth.uid()` y metadatos mínimos. Rechaza actor ausente. La función no copia `facts`, precio ni snapshot al log. Su propietario privilegiado solo escribe en `audit_events`; no se expone como RPC. Pruebas revisan que el evento aparece y que roles de usuario no pueden falsificarlo ni editarlo.
6. **Integración y reversión.** La migración se crea con la CLI oficial y no se aplica al proyecto alojado. El ensayo local restaura una copia previa en una base descartable; en producción una migración correctiva es preferible a borrar datos. `pg_dump`/`pg_restore` de prueba comprueban esquema y datos sintéticos. No hay tabla de precios calculados ni política duplicada de AT-224.

## Riesgos / Trade-offs

- [Función `SECURITY DEFINER` puede ampliar permisos] → esquema no expuesto, búsqueda fija, revocación explícita y tests de acceso; revisar en checkpoint de seguridad.
- [Una sesión SQL puede falsificar el GUC de JWT si posee conexión directa] → no conceder conexión directa a usuarios; AT-209 valida JWT y usa contexto de identidad confiable. El harness local no prueba autenticación.
- [Rol de servicio omite RLS] → reservarlo a migración/admin; no usarlo para requests de usuario ni en frontend.
- [Ofertas/snapshots crecen] → índices por proyecto/fecha y retención posterior; no aplicar borrados automáticos en AT-208.
- [Índice parcial garantiza solo máximo uno activo] → API crea primer presupuesto en transacción y maneja conflicto 23505; no proclamar existencia obligatoria.
- [Restore puede perder datos posteriores al backup] → probar recuperación con fixtures, documentar RPO/RTO antes de producción.

## Migration Plan

1. Validar OpenSpec antes de escribir SQL. Crear migración con `supabase migration new` verificado por `--help`.
2. Aplicar sobre PostgreSQL 17 descartable con roles Supabase y `auth.uid()` simulados **solo en harness local**; ejecutar pruebas de esquema, RLS, FKs, historial y auditoría.
3. Exportar la base sintética y restaurar en otra base descartable; verificar recuentos, restricciones y RLS. Ensayar reversión en copia, no en base alojada.
4. Publicar propuesta para revisión fresca de diseño de RLS, funciones privilegiadas y matriz de acceso; esperar checkpoint antes de integrar. No tocar Supabase alojado.

## Checkpoint de revisión antes de integrar

Revisor independiente debe examinar superficie `public`, cada GRANT y política, funciones privadas privilegiadas, FKs de tenant, protección del propietario, actor de auditoría, test de roles reales y plan de rollback. La aprobación se refiere al diff SQL y resultados reproducibles, no a una afirmación de seguridad de JWT o del proyecto alojado.
