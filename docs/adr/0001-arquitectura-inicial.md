# ADR 0001 — Arquitectura inicial de Estimate Agent (AT-206)

- **Fecha:** 2026-11-26
- **Estado del ADR:** propuesto para integración por el PR de [AT-206](https://linear.app/oicrruf/issue/AT-206/definir-adr-de-arquitectura-hosting-sql-identidad-y-dos-repositorios); decisión de producto previamente registrada, con revisión independiente previa del borrador. La aprobación del PR se comprueba en GitHub.
- **Alcance:** H0 Relate y arquitectura inicial del MVP; la plataforma multiusuario completa se implementa en issues posteriores.

## Contexto y evidencia

El [plan de dependencias](https://linear.app/oicrruf/document/estimate-agent-orden-de-ejecucion-y-dependencias-openspec-codex-bebc78949703) coloca AT-206 primero, sin bloqueos, y AT-207 detrás. AT-215 valida Relate y AT-229 prepara la demo independientemente. AT-261 guía la separación del núcleo y el conocimiento; AT-264 detallará el metamodelo.

Consulta de metadata, 26/11/2026: `estimate-api` y `estimate-app` son públicos y se observaron inicialmente vacíos. Tras la excepción de bootstrap documental aprobada por el usuario, `main` y `develop` de cada repositorio apuntaban al mismo commit raíz, que contiene solo `README.md` y atribuye autor y committer a Víctor M. Reyes. El conector Supabase confirmó un proyecto existente de Estimate Agent en `us-west-2`, estado `ACTIVE_HEALTHY` y PostgreSQL 17. Solo se consultó metadata; no se leyó ni modificó base de datos, Storage, Auth o claves. No se comprobó el plan efectivo de facturación de la cuenta.

## Decisión 1 — núcleo universal y paquetes de conocimiento

El core maneja identificadores y revisiones de proyecto, requisitos, dependencias, alternativas, decisiones y referencias de evidencia. Catálogos de especialidad, reglas técnicas, jurisdicción, vigencia y fuentes se empaquetan por rubro y versión. Un paquete declara su esquema y ámbito; un validador impide usar reglas incompatibles o vencidas. La salida incluye versión de paquete y evidencia utilizada. Si falta cobertura, se devuelve `cobertura_insuficiente`; no se afirma cumplimiento normativo universal. Incorporar un rubro nuevo no debe exigir cambiar el código del core. AT-261/264/265 detallarán contratos y registro, y fixtures sintéticos multirrubro verificarán el límite.

## Decisión 2 — datos, objetos e identidad

Supabase gestionado es la fuente de verdad del MVP: PostgreSQL para catálogo, BOM, cantidades, propuestas, selección, revisiones e índices de evidencia; Auth para identidad; Storage **privado** para PDF y activos. Angular/A2UI solicita cambios a FastAPI. PostgreSQL usa RLS en tablas expuestas, políticas por pertenencia y rol de proyecto, con default deny. FastAPI comprueba firma, emisor, audiencia y caducidad del JWT y revalida permiso por recurso antes de API y MCP; no confía en un `project_id` enviado por cliente. La clave de servicio y credenciales privadas viven solo en backend. La clave publicable y URL del proyecto, cuando se usen, son las únicas variables Supabase admisibles en frontend. Una sesión de ChatGPT MCP autentica el acceso al conector de ChatGPT, **no** sustituye la identidad de usuario ni el JWT de Supabase de Estimate Agent. GitHub Auth como proveedor de inicio de sesión es una configuración futura de Supabase Auth; tampoco equivale al token del conector GitHub que permite consultar repositorios. El flujo concreto de login y claims se cerrará en AT-209/219.

Las operaciones mutables aceptan revisión esperada y clave de idempotencia vinculada a actor, recurso, tipo y huella de carga. Devuelven revisión nueva, identificador de operación y resultado. Reintento idéntico devuelve el resultado previo; carga distinta con misma clave, o revisión obsoleta, produce conflicto. La auditoría registra actor, proyecto, recurso, acción, hora y resultado, sin tokens ni payload comercial completo. Se ensayan usuario autorizado, usuario ajeno, token inválido, reintento y conflicto. RLS es defensa adicional: una credencial de servicio que la elude nunca se expone a cliente.

Los objetos usan bucket privado, rutas vinculadas al proyecto y enlaces firmados de objeto único con TTL breve. El backend autoriza cada emisión y registra el acceso concedido. No se usan enlaces públicos permanentes. [Supabase advierte que la descarga mediante URL firmada ya no reevalúa la política al consumirse](https://supabase.com/docs/guides/storage/security/access-control); por eso el TTL y la protección del enlace son relevantes. Los respaldos de base de datos **no incluyen los bytes de Storage**, solo su metadata; el plan de backup debe exportar ambos conjuntos y ensayar restauración conjunta ([documentación de backups](https://supabase.com/docs/guides/platform/backups)).

No se despliegan PostgreSQL propio, D1, MinIO/S3 independiente ni Keycloak. No se reintroduce Google Sheets bidireccional ni Drive para PDF. Un importador histórico y exportadores pueden existir como adaptadores futuros sin entrar en el flujo crítico.

## Decisión 3 — runtime H0 y despliegue previsto

Supabase no hospeda FastAPI, ADK Python, MCP, Angular ni Relate. **Estrategia Docker para H0:** preparar en AT-215 un `compose.yaml` reproducible con servicio Python, volumen de datos Relate, fixture sintético y healthcheck. El perfil demo deberá conservar el volumen entre restart y redeploy, y ensayar exportación y restauración. Este ADR no afirma que exista o se haya probado ese Compose. Una prueba local independiente reportó Relate **1.3.0** con Python **3.12.14** y funcionamiento bajo **un solo escritor**; no probó hosting, SQL, despliegue, recuperación ni concurrencia de varios escritores. AT-215 conserva esos gates. La UI puede servirse estática o con Nginx. El destino previsto para runtime es la instancia llamada «Dockploy» por el usuario; proveedor/host real y acceso operativo no están confirmados. No hay despliegue.

**Checklist de comprobación Dockploy previo a publicar:** identificar URL y proveedor reales, acceso al panel y permisos; método de conexión de ambos repos y refs; soporte de Docker/Compose y recursos CPU/RAM/disco; volumen persistente de Relate, rutas y permisos; supervivencia a restart/redeploy y restauración de backup; inyección y rotación de secretos por entorno; red saliente a Supabase y APIs, puertos entrantes mínimos; dominios, DNS, TLS y renovación; healthchecks, logs, rollback y límites de recursos. MCP debe estar autenticado y restringido por red si no hay necesidad pública. Un solo escritor por dataset de Relate hasta que AT-215 pruebe concurrencia y recuperación; las lecturas concurrentes también requieren evidencia.

## Opciones examinadas

| Decisión | Opción | Resultado |
| --- | --- | --- |
| SQL | Supabase PostgreSQL | Elegido: proyecto existente, Auth/Storage integrados, RLS y SQL relacional; dependencia del servicio y cuotas Free. |
| SQL | Cloudflare D1 | Aplazado: SQLite y acceso centrado en Workers exigirían otro adaptador y Auth/Storage aparte; no hay beneficio medido para backend Python. [Límites D1](https://developers.cloudflare.com/d1/platform/limits/) documentan 500 MB por DB Free y ejecución por DB de un hilo. |
| SQL | PostgreSQL propio | Aplazado: control mayor, pero añade operación, backups, seguridad y costo de host para H0. |
| Python | Dockploy del usuario | Destino previsto, condicionado a verificaciones operativas anteriores. |
| Python | PaaS externo | Reserva si Dockploy falla; se comparará costo, volumen persistente, límites y salida de datos con datos reales del proveedor. |
| Objetos | Supabase Storage privado | Elegido para MVP; requiere backup separado y control de enlaces. |

La [página de precios de Supabase](https://supabase.com/pricing) consultada el 26/11/2026 indica Free a **$0/mes** dentro de cuotas, 500 MB de base, 1 GB de Storage, 5 GB de egress, 50 000 usuarios activos mensuales, máximo dos proyectos activos y pausa tras una semana de inactividad. Son límites sujetos a cambio y a confirmar en la cuenta antes de aprovisionar o publicar. Dockploy, dominios, proveedor de modelo y tráfico pueden costar dinero adicional; no se estiman como $0. Free no ofrece backup diario gestionado: [Supabase recomienda exportación regular fuera del sitio](https://supabase.com/docs/guides/platform/backups). Se evaluará Pro u otra alternativa si cuotas, continuidad o RPO/RTO no son aceptables.

## Contratos preliminares

**Proyecto:** entrada `{project_id, package_ref: {id, version, jurisdiction}, revision}`; salida `{project_id, revision, package_ref, coverage_status}`. **Mutación de recurso:** cabeceras `Authorization: Bearer <JWT>` e `Idempotency-Key`; entrada `{project_id, resource_id, expected_revision, value}`; salida `{resource_id, revision, operation_id, audit_ref}`. Errores: 401 token ausente/inválido; 403 permiso insuficiente; 404 recurso oculto; 409 revisión/clave incompatible; 422 carga inválida. No se consideran esquemas OpenAPI finales: AT-207 crea contrato versionado, AT-209 implementa API y AT-219 consume desde Angular. El identificador de usuario se deriva del JWT, nunca del cuerpo.

**Persistencia y archivos:** interfaces tipadas `ProjectRepository` y `FileStorage` con métodos que reciben contexto de actor/proyecto y devuelven revisión, referencia u error tipado. El adaptador de Storage no devuelve URL pública permanente. Los tests contractuales usan un adaptador en memoria y fixtures sintéticos; no precisan credenciales reales.

## Amenazas, pruebas y reversión

Amenazas principales: filtración de clave de servicio en frontend; IDOR por `project_id`; JWT falsificado o vencido; RLS mal configurada; URL firmada reenviada; doble escritura Relate; pérdida de datos al reiniciar o pausar Free; secretos en repositorio público. Mitigaciones: escaneo de secretos, privilegio mínimo, JWKS/validación completa de claims, matriz de permisos por recurso y RLS, TTL de enlace, escritor único, backups cifrados y restauración ensayada, variables por entorno.

| Capa | Positivo | Negativo | Evidencia requerida |
| --- | --- | --- | --- |
| ADR/OpenSpec | CLI valida todos los deltas | Requisito sin escenario falla | versión CLI y salida `validate --strict` |
| Contrato API | mutación autorizada con revisión | 401/403/404/409/422; reintento distinto | pruebas unitarias/contrato en AT-209 |
| DB/RLS | miembro accede a su proyecto | usuario B no ve ni modifica proyecto A | integración con dos usuarios sintéticos en AT-208 |
| Storage | PDF privado y enlace breve | acceso sin permiso o enlace vencido | integración con objetos sintéticos en AT-222 |
| Relate/Compose | arranque, lectura, restart, restore | datos faltantes, dos escritores | spike AT-215 y vertical slice AT-227 |
| E2E | Angular → API → datos/Relate | token inválido y red/redeploy | AT-226 antes de declarar despliegue |

Una futura migración SQL debe tener script revisado, copia previa, ensayo de restauración, plan de reversión compatible con datos y ventana de mantenimiento. La reversión de esta ADR documental se realiza mediante commit correctivo trazado; no se borran refs ni historia. Las exportaciones de backup deben cifrarse, guardarse fuera de Git/Dockploy y probarse periódicamente.

## Historial Git y ruta para repositorios vacíos

Política objetivo: `main` producción, `develop` integración, `feature/AT-XXX-slug`, `release/vX.Y.Z`, `hotfix/AT-XXX-slug`; issue PR por Squash & Merge para dejar un commit convencional por issue/repositorio; sin merge commits. Promoción de release fast-forward-only de commits ya integrados; hotfix por squash y reconciliación/cherry-pick trazado, sin merge commit. Autor local aprobado: `Víctor M. Reyes <vm.reyesal@gmail.com>`, sin trailers opcionales de coautoría. AT-207 implementará reglas, CI, templates, OpenSpec en ambos repos y protecciones. No se toca configuración GitHub aquí.

| Ruta | Ventaja | Coste respecto a gates |
| --- | --- | --- |
| **Base mínima documental revisada** en cada `main` (p. ej. README con nombre y enlaces), crear `develop` desde esa ref, después feature AT-206 | Permite PR de AT-206 contra `develop`, revisión y un commit final de issue; mantiene AT-207 separado. | Bootstrap sin AT-XXX requiere registrar excepción operativa; al crear la base no había CI, por lo que AT-206 incorpora solo un gate documental propio. |
| Primer commit directamente AT-206 en `main`, crear `develop` después | Menos commits y sin bootstrap extra. | No hay PR ni revisión previa del primer commit; contradice el gate de cierre de AT-206 y dificulta corregirlo sin otro commit del mismo issue. |

**Resultado:** el usuario aprobó la excepción de un commit inicial con solo `README.md` por repositorio; se establecieron las refs descritas arriba. AT-206 se propone en una feature de `estimate-api` hacia `develop`. Este PR incorpora un gate documental limitado a comprobar sus propios artefactos con OpenSpec 2.2.0; la CI general, contratos y entornos permanecen en AT-207. El gate no sustituye revisión independiente ni autoriza cierre antes de CI verde, aprobación y merge efectivo. No se crea un tercer repo.

## Fuentes y estado de verificación

- Linear: [AT-206](https://linear.app/oicrruf/issue/AT-206/definir-adr-de-arquitectura-hosting-sql-identidad-y-dos-repositorios) y [plan](https://linear.app/oicrruf/document/estimate-agent-orden-de-ejecucion-y-dependencias-openspec-codex-bebc78949703), consultados el 26/11/2026.
- GitHub: metadata de [estimate-api](https://github.com/oicrruf/estimate-api) y [estimate-app](https://github.com/oicrruf/estimate-app), más `git ls-remote`; la única escritura previa a este PR fue el bootstrap documental aprobado.
- Supabase: consulta de metadata del proyecto existente, sin publicar ID/ref; estado de cuotas/plan de la cuenta y esquema no comprobados en esta tarea.
- Documentación oficial: [precios Supabase](https://supabase.com/pricing), [backups](https://supabase.com/docs/guides/platform/backups), [Storage](https://supabase.com/docs/guides/storage/security/access-control), [JWT](https://supabase.com/docs/guides/auth/jwts), [D1](https://developers.cloudflare.com/d1/platform/limits/), [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md).
