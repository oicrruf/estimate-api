# Spec Delta

## Purpose

Capturar un alcance incompleto de forma trazable, conservando la incertidumbre y la responsabilidad de suministro.

## ADDED Requirements

### Requirement: Borrador tipado y versionado
El sistema SHALL conservar una versión explícita del contrato y campos para objetivo, ubicación, ambiente, croquis, medidas, restricciones, exclusiones, suministros, activos del cliente y preguntas bloqueantes.

#### Scenario: Descripción incompleta
- **WHEN** la entrada contiene solo una descripción breve
- **THEN** el borrador conserva la descripción y pregunta de forma específica por los campos ausentes
- **AND** los campos desconocidos permanecen vacíos

### Requirement: Certeza verificable
El sistema SHALL diferenciar hechos confirmados e inferidos. Un hecho confirmado MUST indicar evidencia explícita. El sistema SHALL pedir confirmación para un hecho inferido sin cambiar su certeza.

#### Scenario: Ubicación inferida
- **WHEN** la ubicación se declara como inferida
- **THEN** permanece inferida y se genera una pregunta para confirmarla

### Requirement: Activos aportados por el cliente
El sistema SHALL registrar disponibilidad y validación del activo por separado. Un activo del cliente MUST quedar fuera de la lista de compra.

#### Scenario: Ausencia confirmada
- **WHEN** el cliente confirma con evidencia que no hay activos existentes ni suministros
- **THEN** las colecciones permanecen vacías y no se generan preguntas para ellas

#### Scenario: Gabinete disponible sin validar
- **WHEN** un gabinete aportado por el cliente está disponible pero sin validar
- **THEN** el borrador pregunta por su estado, dimensiones y compatibilidad
- **AND** el gabinete no aparece entre los artículos de compra

### Requirement: Adaptación y fallo cerrado
El sistema SHALL generar un paquete de dominio del documento universal v1 sin mutar el documento de entrada. SHALL rechazar documentos inválidos, sujetos inexistentes, identificadores duplicados y medidas no finitas antes de devolver un resultado.

#### Scenario: Documento inválido
- **WHEN** la entrada al adaptador viola el contrato universal
- **THEN** el adaptador rechaza la operación y no devuelve documento parcial
