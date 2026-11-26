# Tasks

## 1. Decisión de arquitectura

- [ ] 1.1 Revisar `docs/adr/0001-arquitectura-inicial.md` contra AT-206, AT-261 y el plan; verificar que un responsable acepta el límite entre core y paquetes.
- [ ] 1.2 Confirmar límites y plan de Supabase de la cuenta sin exponer claves; verificar metadata de `estimate-agent` y registrar fecha y resultado en ADR.
- [ ] 1.3 Revisar contrato de identidad/autorización, idempotencia, auditoría y objetos con un caso de dos usuarios sintéticos; verificar que los escenarios de las tres specs cubren éxito y rechazo.

## 2. Reproducibilidad e integración documental

- [x] 2.1 Resolver bootstrap de `main`/`develop` con base documental aprobada y registrar excepción operativa; verificado con `git ls-remote` y commits raíz antes de crear feature AT-206.
- [ ] 2.2 Fijar versión de OpenSpec con lockfile del repositorio y validar `openspec validate at-206-arquitectura-inicial --strict`; verificar salida y ausencia de cambios de otros issues.
- [ ] 2.3 Definir comprobación CI mínima para este PR sin mezclar la implementación AT-207; verificar ejecución verde antes de cerrar AT-206.
- [ ] 2.4 Revisar ADR y especificaciones con responsable; verificar decisión documentada y trazabilidad de PR AT-206.

## Workflow follow-up

- Archivar/sincronizar specs en el commit final de AT-206 cuando las tareas estén completas y la revisión lo permita.
- Integrar por Squash & Merge a `develop`, comprobar CI y merge efectivo, y solo entonces actualizar AT-206.
- Ejecutar PoC Docker/Relate y pruebas de persistencia/concurrencia en AT-215; preparar dataset en AT-229. Mantener AT-207 separado para CI, contratos y entornos de ambos repositorios.
