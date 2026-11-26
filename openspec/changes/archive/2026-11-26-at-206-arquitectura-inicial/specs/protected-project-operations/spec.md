# Spec Delta

## Purpose

Protege proyectos y artefactos comerciales al definir identidad, autorización, repetición segura y trazabilidad para las operaciones expuestas por la API y herramientas MCP.

## ADDED Requirements

### Requirement: Autorización por recurso
La API SHALL verificar identidad vigente y permiso sobre el proyecto específico antes de leer o modificar un recurso; las herramientas MCP SHALL aplicar la misma política.

#### Scenario: Proyecto ajeno
- **GIVEN** una identidad autenticada sin acceso al proyecto solicitado
- **WHEN** intenta leerlo o modificarlo por API o MCP
- **THEN** se rechaza la operación sin revelar su contenido.

#### Scenario: Token inválido
- **GIVEN** un token ausente, expirado o de emisor no confiable
- **WHEN** se solicita un recurso protegido
- **THEN** la operación se rechaza antes de acceder a datos.

### Requirement: Mutación idempotente y auditada
Cada operación mutable SHALL aceptar una clave de idempotencia ligada a identidad, recurso y tipo de operación, y SHALL registrar actor, acción, recurso, resultado y hora sin secretos.

#### Scenario: Reintento idéntico
- **GIVEN** una mutación aceptada con clave de idempotencia
- **WHEN** el mismo actor reenvía la misma solicitud y clave
- **THEN** recibe el resultado previo sin aplicar una segunda mutación.

#### Scenario: Clave reutilizada con contenido distinto
- **GIVEN** una clave previamente usada
- **WHEN** el actor la reenvía con una carga diferente
- **THEN** la operación se rechaza y queda un evento auditable.
