# chat-intake-preview Specification

## ADDED Requirements

### Requirement: Vista previa tipada de alcance
El sistema SHALL aceptar datos estructurados AT-246 de un proyecto nuevo y devolver un borrador y preguntas sin inventar hechos ni materiales.

#### Scenario: Descripción incompleta
- **WHEN** el usuario entrega una descripción y deja detalles sin declarar
- **THEN** la respuesta conserva la descripción y presenta preguntas específicas
- **AND** la respuesta indica revisión requerida

### Requirement: Frontera de confirmación
La vista previa SHALL ser de solo lectura y MUST NOT persistir, aprobar, seleccionar productos ni iniciar investigación comercial. La respuesta SHALL distinguir explícitamente una propuesta pendiente de una confirmación.

#### Scenario: Hecho inferido y gabinete del cliente
- **WHEN** la entrada marca una ubicación inferida y un gabinete disponible sin validar
- **THEN** se piden confirmación y validación del gabinete
- **AND** el gabinete no figura en compras

### Requirement: Fallo cerrado
La operación SHALL rechazar hechos confirmados sin evidencia y solicitudes de cambio de proyecto existente hasta que exista el límite de autorización y concurrencia.

#### Scenario: Evidencia ausente
- **WHEN** un hecho se declara confirmado sin evidencia
- **THEN** la operación devuelve un error de validación y no produce vista previa
