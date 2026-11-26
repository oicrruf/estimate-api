# Tasks

## 1. Decisión de arquitectura

- [x] 1.1 Contrastar `docs/adr/0001-arquitectura-inicial.md` con AT-206, AT-261 y el plan; el borrador recibió revisión independiente previa y separa core y paquetes en ADR y spec.
- [x] 1.2 Registrar metadata verificada del proyecto Supabase y límites públicos del plan Free con fecha y fuentes en el ADR; dejar el plan real de la cuenta como gate posterior sin consultar claves.
- [x] 1.3 Revisar los contratos de identidad, autorización por recurso, idempotencia, auditoría y objetos; comprobar escenarios de éxito y rechazo en las tres delta specs. Las pruebas con dos usuarios quedan en AT-208/209.

## 2. Reproducibilidad e integración documental

- [x] 2.1 Resolver bootstrap de `main`/`develop` con base documental aprobada y registrar excepción operativa; verificado con `git ls-remote` y commits raíz antes de crear feature AT-206.
- [x] 2.2 Fijar OpenSpec 2.2.0 y dependencias en `ci/at-206-docs/package-lock.json`; comprobar `npm ci` y validar el cambio exacto con `openspec validate at-206-arquitectura-inicial --strict` antes de archivar.
- [x] 2.3 Preparar workflow documental mínimo para este PR y comprobar localmente sus archivos y comandos; confirmar resultado remoto CI como gate del PR, fuera de las tareas archivadas.
- [x] 2.4 Registrar revisión independiente previa del borrador y trazabilidad del PR AT-206 en evidencia y descripción, sin presumir aprobación de GitHub.

## Workflow follow-up

- Archivar/sincronizar specs tras completar estas tareas; comprobar los tres specs vigentes y `openspec validate --archived` antes del merge.
- Exigir revisión/aprobación del PR en GitHub, CI verde y merge efectivo por Squash & Merge a `develop` antes de actualizar AT-206.
- Verificar plan real de cuenta, RLS/JWT y Storage en AT-208/209/222; PoC Docker/Relate, persistencia y concurrencia en AT-215; dataset en AT-229; despliegue/E2E en AT-226. Mantener AT-207 separado para CI general, contratos y entornos de ambos repositorios.
