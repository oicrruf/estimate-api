# Frontera AT-209 → AT-211 para ejecución interactiva

Estado: contrato propuesto sobre `develop` `838834287a9a9fd002509925b5232e2222f78ab4`, sin ruta de cobro desplegada. AT-211 integrado hoy ofrece `preview_specialist_handoff`, una función local pura; su documentación advierte que no autentica llamadores ni verifica procedencia de evidencia. No se debe conectar esa función a un proveedor de pago o modelos desde un endpoint público sin esta frontera.

## Entrada HTTP mínima

- `GET /projects` y `GET /projects/{project_id}` son las rutas implementadas aquí. Reciben `Authorization: Bearer <access token Supabase Auth>`. `get_actor` valida firma JWKS, `iss`, `aud`, tiempos, rol y `sub` UUID; `get_interactive_actor` admite solo UUID presentes en `ESTIMATE_INTERACTIVE_ALLOWED_SUBJECTS` del backend; `require_project_access` consulta propiedad/membresía actual con AT-208 RLS y devuelve `ProjectView(id, name, revision, access_role)` o 404.
- Para una futura `POST /projects/{project_id}/agent/runs` de AT-211, el `project_id` de la ruta es obligatorio y todo recurso, evidencia, presupuesto y paquete debe pertenecer a ese proyecto. La política de roles para iniciar gasto está pendiente de aprobación en AT-211; hasta entonces la ruta debe denegar. La sesión de ChatGPT/MCP o el token de GitHub nunca reemplazan el access token Supabase Auth.

```python
from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException
from estimate_api.authorization import get_interactive_actor
from estimate_api.projects import ProjectView, require_project_access

# Ejemplo de integración para AT-211; no es una ruta instalada.
def start_agent_run(
    project_id: UUID,
    actor: Annotated[UUID, Depends(get_interactive_actor)],
    project: Annotated[ProjectView, Depends(require_project_access)],
    # command: RunCommand, service: AgentRunService,
):
    # AT-211 debe fijar roles autorizados; hasta entonces no iniciar gasto.
    raise HTTPException(403, "Agent run role policy pending")
    # service.start(project_id=project_id, actor=actor,
    #               expected_project_revision=project.revision,
    #               idempotency_key=command.idempotency_key)
```

La dependencia HTTP es un filtro temprano, **no** una autorización irrevocable para cobrar. La operación mutable deberá revalidar actor, admisión, membresía, rol aprobado, proyecto/revisión y clave de idempotencia dentro de su transacción de servicio, antes de reservar presupuesto o llamar al proveedor; si algún requisito cambia, no inicia ni cobra. Debe registrar auditoría y vincular consumo/resultado al proyecto. Un token puede seguir vigente después de revocar la membresía; la consulta AT-208 ya devuelve 404 en ese caso, pero el servicio mutable debe repetir el control en su propia frontera transaccional. No confiar en datos comerciales, `project_id`, rol o evidencia enviados por el cliente sin resolución canónica.

## Prueba de la frontera disponible

`bash tests/at209/run_official_auth.sh` usa GoTrue v2.198.0 y PostgreSQL 17 fijados por digest, usuarios y claves efímeras. Ejercita la API real con token ausente (401), inválido (401), usuario autenticado sin admisión (403), admitido sin membresía (lista vacía y detalle 404), propietario/miembro autorizados (200) y revocación con el mismo token (detalle 404). Incluye un smoke de Uvicorn en loopback por HTTP real (401/200). No invoca modelos, cobros, OAuth GitHub real ni sistemas alojados.

## Preview HTTP local con stub descartable

El backend declara `POST /v1/projects/{projectId}/scope-review-preview` con JSON `{ "brief": "..." }` (1..4000 caracteres) y cabecera `Idempotency-Key` (1..100). Por defecto devuelve 503 a un actor autorizado porque no hay extractor instalado; el flag local y un DSN por sí solos no montan proveedor. Solo `tests.at209.preview_server` inyecta el extractor sintético, exclusivamente en el servidor descartable de pruebas. La respuesta `scope-review-preview.v1` informa `state=pending_review`, `reviewRequired=true`, `persisted=false`, `commercialReady=false`; el ejemplo de cuatro cámaras y stock dos es un fixture, no evidencia comercial.

`tests/at209/local_preview_reservations.sql` crea una tabla privada **solo en PostgreSQL descartable**, sin `brief` ni tokens. El LOGIN de reserva carece de SUPERUSER/BYPASSRLS/herencia, tiene SELECT/INSERT y UPDATE limitado al recibo, y usa `SET LOCAL ROLE authenticated` para volver a evaluar propietario/editor bajo RLS en la misma transacción. `pg_advisory_xact_lock` serializa los recuentos de una hora: 2 por actor, 4 por proyecto y 8 globales. Una clave completada repite la respuesta guardada sin segundo extractor; pendiente o fallida responde 409. Cuota responde 429 y fallo SQL 503. Las pruebas HTTP con GoTrue real incluyen dos conexiones que degradan o revocan un editor mientras la petición espera el bloqueo: ambas denegaciones dejan cero reservas y cero llamadas al stub.

Esta reserva es un presupuesto **de prueba**, no dinero ni autorización para modelos. La transacción confirma el cupo antes de ejecutar el stub; el recibo cambia a `complete` o `failed` después, en otra transacción. Si el stub o la escritura final falla, la reserva sigue ocupando cupo y el reintento no ejecuta otra llamada. Ningún bloqueo de base dura durante el stub. El punto de autorización es la lectura de rol antes del INSERT; una revocación que confirme después puede adelantarse a la llamada externa. Evitar esa carrera en un servicio pagado exige un protocolo coordinado de cancelación/autorización que este prototipo no implementa. AT-280 aún debe aceptar este contrato exacto antes de integrar el OpenAPI nuevo.

Angular puede tratar `200` como propuesta pendiente que exige revisión humana y que no se guardó; `401` requiere sesión, `403` indica falta de admisión o rol de edición, `404` oculta un proyecto inexistente o revocado, `422` indica entrada/cabecera inválida, `409` indica recibo pendiente o fallido sin reintento automático, `429` indica cupo agotado y `503` indica servicio deshabilitado o error interno. La misma clave completada devuelve el mismo `200` sin nueva extracción. Esta descripción no activa la ruta en Angular ni concede capacidad comercial.

For the disposable proof, a receipt binds the exact UTF-8 brief to actor, project and idempotency key through a versioned SHA-256-derived internal UUID. The private table stores neither the raw brief nor a new column. Reusing a completed key with a different brief returns 409 and never replays the prior answer; a whitespace-only key returns 422 before reservation. The digest is a request-binding check, not a confidentiality control. No hosted schema or provider is involved.
