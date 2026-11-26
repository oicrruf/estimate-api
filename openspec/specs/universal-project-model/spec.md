# universal-project-model Specification

## Purpose

Permite intercambiar y validar proyectos de distintos dominios mediante una estructura común, preservando la procedencia y el grado de certeza de cada entidad.

## Requirements

### Requirement: Contrato de entidades comunes
El sistema SHALL admitir ProjectGoal, Requirement, Capability, Resource, Task, Deliverable, Constraint, SiteCondition, Evidence, Dependency, BOMLine, Rule y Approval con id estable, origen, ámbito, revisión y estado de conocimiento.

#### Scenario: Tipos compartidos
- **WHEN** un documento incluye una entidad de cualquiera de los trece tipos
- **THEN** la entidad usa los mismos campos obligatorios de identidad y trazabilidad

### Requirement: Versión y validación
El sistema SHALL identificar la versión del contrato en cada documento y SHALL rechazar documentos que incumplan el esquema de esa versión.

#### Scenario: Documento válido
- **WHEN** un consumidor valida un documento que cumple el esquema declarado
- **THEN** la validación termina sin errores

#### Scenario: Documento inválido
- **WHEN** falta un campo obligatorio, aparece un tipo desconocido o la versión no está soportada
- **THEN** la validación informa errores y rechaza el documento

### Requirement: Integridad de referencias
El sistema SHALL rechazar ids duplicados y referencias a entidades inexistentes dentro del documento.

#### Scenario: Referencia rota
- **WHEN** una relación o un paquete apunta a un id ausente
- **THEN** el documento se rechaza con un error identificable

### Requirement: Extensión por paquetes
El sistema SHALL mantener los hechos específicos del dominio en paquetes vinculados a entidades, sin introducir campos específicos de ese dominio en el núcleo.

#### Scenario: Tres dominios con la misma estructura
- **WHEN** se modelan cámaras, pintura de inmueble y montaje de evento
- **THEN** los tres documentos se validan con el mismo contrato de núcleo y conservan los hechos propios en paquetes
