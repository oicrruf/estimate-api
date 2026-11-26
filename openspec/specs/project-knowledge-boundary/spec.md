# project-knowledge-boundary Specification

## Purpose

Permite representar proyectos de distintos rubros con un núcleo común y conocimiento especializado versionado, manteniendo visibles sus límites de competencia y evidencia.

## Requirements

### Requirement: Separación de conocimiento
El sistema SHALL admitir un proyecto y un paquete de conocimiento identificado por rubro, versión y jurisdicción sin exigir cambios del núcleo para incorporar otro rubro.

#### Scenario: Nuevo rubro compatible
- **GIVEN** un paquete válido de un rubro nuevo
- **WHEN** se registra un proyecto que lo referencia
- **THEN** el núcleo conserva el mismo contrato de proyecto y vincula el paquete y su versión.

### Requirement: Alcance de afirmaciones técnicas
El sistema SHALL identificar la fuente, la versión y la jurisdicción de cada regla técnica usada en una conclusión, y SHALL indicar ausencia de cobertura cuando no haya regla aplicable.

#### Scenario: Sin paquete aplicable
- **GIVEN** un requisito sin regla vigente para su jurisdicción
- **WHEN** se solicita una conclusión técnica
- **THEN** el resultado indica cobertura insuficiente y no presenta conformidad normativa universal.

### Requirement: Registro versionado y alcance verificable
El sistema SHALL registrar paquetes por namespace y versión con taxonomía, esquemas de categoría, patrones de instalación, conjuntos de reglas, fuente, jurisdicción, aplicabilidad, límites y revisor requerido. SHALL rechazar identidades duplicadas y metadatos de revisión verificada sin referencia del revisor y evidencia.

#### Scenario: Paquete reproducible
- **GIVEN** un paquete sintético con versión y metadatos completos
- **WHEN** se valida el registro
- **THEN** el paquete conserva su identidad y su alcance sin modificar el contrato universal del proyecto.

### Requirement: Resolución conservadora de cobertura
El sistema SHALL resolver la cobertura con coincidencia explícita de versión, categoría, jurisdicción y ámbito. SHALL entregar resultados deterministas para solapes y declaraciones contradictorias. SHALL señalar revisión especializada para paquetes no verificados, solapes, conflictos o entradas inválidas; SHALL indicar ausencia de cobertura si no hay paquete aplicable. La resolución del registro SHALL NOT emitir conclusiones técnicas ni normativas.

#### Scenario: Paquete no verificado
- **GIVEN** un proyecto que referencia un paquete aplicable sin revisión verificada
- **WHEN** se resuelve su cobertura
- **THEN** el resultado es `pending_specialist` y no afirma cumplimiento técnico.

#### Scenario: Solape contradictorio
- **GIVEN** dos paquetes aplicables con elecciones distintas para el mismo tema declarado
- **WHEN** se resuelve su cobertura en cualquier orden de registro
- **THEN** el resultado es `pending_specialist` con conflictos ordenados de forma estable.
