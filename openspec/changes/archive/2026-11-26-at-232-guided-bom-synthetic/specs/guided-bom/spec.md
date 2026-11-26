# guided-bom.v1

## ADDED Requirements

### Requirement: Evaluación sintética de EMT

El sistema SHALL aceptar sólo `cable_count` 3 o 6 y `cable_variant`
`thick`, `slim` o `unknown` para el escenario ficticio fijo. SHALL comparar
los tres EMT genéricos con dimensiones nominales documentadas y el criterio
de 40 % ilustrativo del fixture, usando Decimal antes del redondeo mostrado.
SHALL devolver candidatos, motivos y rutas de evidencia de Relate, y
alternativas de accesorios del diámetro preliminar. La revisión profesional
SHALL permanecer pendiente.

#### Scenario: Cambio de cantidad y OD

- **GIVEN** un store Relate sembrado con la fixture sintética
- **WHEN** la cantidad cambia de tres a seis UTP o se elige otro OD
- **THEN** la selección preliminar y los accesorios del mismo diámetro
  se actualizan con rutas de evidencia verificables

### Requirement: Hechos insuficientes

El sistema SHALL distinguir supuestos, requisitos confirmados y preguntas
desconocidas. SHALL dejar conectividad, energía, trazado, certificación y
precio como pendientes. Switch y gabinete SHALL aparecer sólo cuando exista
una justificación confirmada.

#### Scenario: Falta un dato de cable o tramo

- **WHEN** OD es desconocido
- **THEN** la compatibilidad y selección permanecen pendientes

#### Scenario: Falta longitud

- **WHEN** longitud del tramo es desconocida
- **THEN** la selección preliminar puede mostrarse, pero no se generan
  cantidades de BOM

### Requirement: GET local restringido

El sistema SHALL servir `GET /v1/demo/guided-bom` sólo en un proceso local
separado, con store Relate fijado al arranque y consultas de lectura fijas.
SHALL devolver el wire completo `guided-bom.v1` y rechazar parámetros extra,
duplicados, faltantes o fuera de los enums con HTTP 422.

#### Scenario: Solicitud con parámetros válidos

- **WHEN** una solicitud GET local usa los enums cerrados
- **THEN** devuelve el wire completo con rutas de evidencia sin consultar
  URLs, rutas ni Cypher proporcionados por la petición

#### Scenario: Solicitud con parámetros inválidos

- **WHEN** faltan parámetros, se duplican o se añaden parámetros ajenos
- **THEN** responde HTTP 422 sin ejecutar evaluación
