# Design

## Context

Véase `proposal.md`. AT-206 está en Backlog, sin `blockedBy`, y bloquea AT-207. Tras la excepción documental aprobada, ambos repositorios tienen `main` y `develop` con un único commit README por repositorio. Supabase informa `estimate-agent` (`ivvwdabsgdajorvxgnpp`, `us-west-2`, `ACTIVE_HEALTHY`). Una prueba local separada reportó Relate 1.3.0 con Python 3.12.14 y un solo escritor; el host, SQL y panel Dockploy no están comprobados. El detalle está en `docs/adr/0001-arquitectura-inicial.md` y `docs/evidence/at-206.md`.

## Goals / Non-Goals

**Goals:** establecer una decisión inicial para H0 y la plataforma posterior, contratos de entrada/salida y controles que puedan verificarse sin datos reales; permitir que AT-207 inicialice ambos repositorios sobre una base clara.

**Non-Goals:** desplegar infraestructura, demostrar concurrencia o persistencia de Relate (AT-215), crear dataset de demo (AT-229), diseñar el metamodelo completo (AT-264/AT-261), ni implementar migraciones, RLS, API o UI.

## Decisions

1. **Core y paquetes.** El core modelará proyecto, requisito, dependencia, revisión y referencia a paquete técnico. Los paquetes aportarán taxonomía, reglas, jurisdicción, vigencia y evidencia. Se rechaza codificar normas de un rubro en el core. Una conclusión sin paquete aplicable se marca como cobertura insuficiente.
2. **Datos e identidad.** Supabase Auth, PostgreSQL y Storage privado son la decisión aprobada para el MVP. FastAPI valida JWT y permisos por proyecto antes de API/MCP, con RLS como defensa adicional para tablas expuestas. Un adaptador tipado de datos y otro de archivos limitan el acoplamiento. D1 se descarta por ahora porque introduciría SQLite y separaría Auth/Storage, sin ventaja probada para esta ruta Python.
3. **Runtime.** FastAPI/ADK/MCP/Relate corren fuera de Supabase. Para H0 se define un perfil Docker local y uno de demo con almacenamiento persistente de Relate; AT-215 debe confirmar hosting, SQL, recuperación y concurrencia. La prueba local de Relate 1.3.0/Python 3.12.14 solo sustenta un escritor. Dockploy es destino previsto, condicionado a inspección de host, panel, volúmenes, red, TLS y backups. Angular/A2UI se sirve estático o con Nginx.
4. **Contrato preliminar.** Entrada mutable: `actor` derivado de JWT, `project_id`, `resource_id`, `revision`, `idempotency_key` y carga validada; salida: recurso/revisión, identificador de operación y resultado auditable. Errores: 401 identidad inválida, 403 permiso insuficiente, 404 recurso no visible, 409 revisión o clave incompatible, 422 carga inválida. Las formas exactas pasan al OpenAPI de AT-207/209.
5. **Integración Git.** La base mínima aprobada ya creó `main` y `develop` en cada repositorio. Esta feature AT-206 se dirige a `develop` mediante PR y futuro Squash & Merge. Un workflow limitado a este PR valida la documentación sin incorporar la CI general de AT-207. Revisión humana, CI verde y merge siguen siendo gates de cierre.

## Risks / Trade-offs

- [Supabase Free puede pausarse y no incluye backup diario gestionado] → exportación cifrada fuera del proyecto, ensayo de restauración y umbral de migración a Pro.
- [Un enlace firmado puede circular durante su vigencia] → TTL corto, ámbito de objeto único, autorización antes de emitirlo y auditoría.
- [Service role o secreto en frontend elude controles] → secretos solo en backend y configuración separada por entorno.
- [RLS y autorización API pueden divergir] → pruebas contractuales de aislamiento con dos usuarios y proyectos sintéticos.
- [Dos escritores sobre estado Relate pueden producir pérdida o conflicto] → un escritor por dataset hasta que AT-215 demuestre semántica segura.
- [Gate documental insuficiente para comportamiento en producción] → este PR valida estructura y revisión del ADR; pruebas RLS/JWT, Relate, Storage y E2E permanecen en issues de implementación.

## Migration Plan

1. Revisar ADR y specs con responsables de arquitectura; conservar las referencias base documentales ya verificadas.
2. Aplicar AT-206 como cambio de documentación OpenSpec al repositorio API. Inicializar OpenSpec de `estimate-app` independientemente en AT-207.
3. Archivar/sincronizar el cambio al cumplir las tareas y validar con CLI fijado; ejecutar revisión, CI y merge efectivo antes de marcar AT-206 completado.
4. En AT-207 y posteriores, implementar API, RLS, almacenamiento y runtime por capas con fixtures sintéticos y contratos versionados.

**Rollback:** revertir configuración por promoción fast-forward controlada o nuevo commit correctivo trazado; restaurar datos desde exportación verificada si una migración futura falla. Este cambio documental no toca datos ni servicios y se revierte con un commit de documentación, preservando el historial lineal.
