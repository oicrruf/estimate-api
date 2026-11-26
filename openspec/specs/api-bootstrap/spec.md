# api-bootstrap Specification

## Purpose

Definir el contrato mínimo y la validación reproducible del servicio API inicial, sin acoplarlo a integraciones futuras.

## Requirements

### Requirement: Health contract
The API SHALL expose exactly one application operation, `GET /health`, with operationId `health` and a HTTP 200 JSON body matching `{ "status": "ok" }`.

#### Scenario: Servicio sano
- **GIVEN** un proceso API iniciado sin secretos
- **WHEN** el cliente solicita `GET /health`
- **THEN** recibe HTTP 200 y JSON `{ "status": "ok" }`

#### Scenario: Ruta desconocida
- **GIVEN** un proceso API iniciado
- **WHEN** el cliente solicita una ruta no definida
- **THEN** recibe HTTP 404

### Requirement: Canonical versioned contract
The API SHALL export a deterministic OpenAPI 3.1 JSON artifact with info version `0.1.0` and SHALL fail validation if the tracked artifact differs from generated output.

#### Scenario: Contrato desactualizado
- **GIVEN** una modificación de código que altera OpenAPI
- **WHEN** se ejecuta la comprobación de contrato
- **THEN** falla hasta actualizar el artefacto canónico

### Requirement: Reproducible local verification
The repository SHALL provide pinned development dependencies, local validation commands and CI checks that run without production credentials.

#### Scenario: Checkout limpio
- **GIVEN** un checkout limpio con Python 3.12 y Node 24
- **WHEN** se ejecutan los comandos documentados
- **THEN** pasan lint, tipos, pruebas, contrato y OpenSpec sin secretos
