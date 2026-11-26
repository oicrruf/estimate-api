# local-preview-http Specification

## ADDED Requirements

### Requirement: Vista HTTP local de evaluación real
El servicio SHALL ejecutarse separado de FastAPI productivo, enlazado sólo a loopback, y SHALL devolver la evaluación ADK/Relate de la fixture persistida sin simular resultados.

#### Scenario: Cambio de requisito PoE
- **WHEN** se evalúa switch con ocho y luego doce puertos PoE mínimos
- **THEN** la respuesta explica la elegibilidad distinta mediante `reasonCodes` y `evidencePaths`

### Requirement: Contrato versionado y parámetros cerrados
La operación `GET /v1/demo/evaluate` SHALL aceptar sólo `scenario=switch|camera|ups`, `poe_ports_min` para switch y `quantity` para camera. SHALL rechazar parámetros ajenos, duplicados, inadecuados o fuera de rango.

#### Scenario: Parámetro inaplicable
- **WHEN** se pasa `quantity` con escenario UPS
- **THEN** se responde error de validación sin consultar el grafo

### Requirement: Ausencia de escritura y exposición
El servicio SHALL leer un store local explícito, sembrado en paso separado. MUST NOT aceptar rutas o Cypher del cliente, habilitar CORS global ni exponer `storePath` en la respuesta.

#### Scenario: Store ausente
- **WHEN** la ruta configurada no contiene una fixture
- **THEN** el servidor falla al iniciar sin crear un store
