# Spec Delta

## Purpose

Permite representar proyectos de distintos rubros con un núcleo común y conocimiento especializado versionado, manteniendo visibles sus límites de competencia y evidencia.

## ADDED Requirements

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
