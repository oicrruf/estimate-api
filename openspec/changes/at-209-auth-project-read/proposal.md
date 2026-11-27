# AT-209: autenticación y lectura mínima de proyectos

## Por qué

El backend vigente ofrece `/health` y la entrada determinista de intake `/v1/chat/intake-preview`, pero no hay una entrada HTTP que valide la identidad antes de consultar los proyectos y membresías de AT-208. Este corte define esa frontera sin adelantar operaciones mutables ni el cliente Angular.

## Alcance propuesto

- Validar `Authorization: Bearer` como token de acceso de **Supabase Auth** emitido después de iniciar sesión con GitHub, proveedor único decidido para el producto. El token GitHub o de un conector no es credencial de Estimate Agent.
- `GET /projects` lista proyectos visibles para el usuario; `GET /projects/{project_id}` lee uno y oculta la existencia del ajeno con 404.
- Derivar el actor del token verificado y consultar PostgreSQL con el rol `authenticated` y RLS de AT-208 dentro de una transacción acotada. Los comandos mutables posteriores usan `at208_backend` en una conexión separada.
- Exigir admisión explícita al modo interactivo por `sub` verificado antes de cada lectura. La configuración de prueba en backend es una lista de UUID administrable por entorno y deniega por defecto; pertenecer a GitHub o portar un token válido no concede acceso al producto.

## Fuera de este corte

Configurar OAuth real, credenciales o Supabase alojado; crear/editar proyectos; tarifas, presupuestos o Storage; exposición MCP; administración persistente y auditada de admisiones o membresías. `contracts/openapi.json` se genera en esta rama para verificar el contrato propuesto, pero no se integra hasta coordinar el ancla AT-280 del frontend.

## Dependencia y comprobación pendiente

AT-208 está integrado en `develop` `057787fdece717267ebc1768b19febc57c18a901`. El responsable del hilo principal consultó Linear: AT-209 también incluye CRUD de proyectos, clientes, requisitos, catálogo y proveedores/contactos, con idempotencia, auditoría y OpenAPI. **Este cambio es solo un corte parcial y no cierra AT-209.** El conector Linear de este worktree devolvió `Unknown tool`; el texto completo aún debe contrastarse antes de integrar. El OpenAPI generado de esta rama se propone para revisión, sin cambiar todavía el frontend ni su ancla AT-280.
