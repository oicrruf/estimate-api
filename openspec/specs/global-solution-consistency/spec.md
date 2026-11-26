# global-solution-consistency Specification

## Purpose

Evaluar restricciones globales declaradas con evidencia y hallazgos tipados, sin inferir datos técnicos ausentes.

## Requirements

### Requirement: Hallazgos tipados y trazables
El sistema SHALL producir un finding por check de cardinalidad, capacidad, compatibilidad o cobertura, con estado pass, fail o pending, sujeto, paquete, fuente, revisión y evidencia cuando ésta es válida.

#### Scenario: Puertos y potencia independientes
- **GIVEN** ocho cámaras, un uplink, ocho puertos totales, ocho puertos PoE y presupuesto de potencia insuficiente
- **WHEN** se evalúan los checks declarados
- **THEN** puertos totales y potencia fallan, mientras el check de puertos PoE pasa.

#### Scenario: Uplink y presupuesto suficientes
- **GIVEN** ocho cámaras, un uplink, nueve puertos totales, ocho puertos PoE y potencia suficiente
- **WHEN** se evalúan los tres checks independientes
- **THEN** cada check pasa; reducir sólo puertos totales, puertos PoE o potencia hace fallar únicamente su check correspondiente.

#### Scenario: Cobertura en otro dominio
- **GIVEN** un proyecto sintético de pintura con tareas requeridas y provistas declaradas
- **WHEN** se evalúa cobertura mediante el mismo paquete global
- **THEN** un faltante produce fail y la cobertura completa produce pass sin campos de cámara en el núcleo.

### Requirement: Desconocidos críticos bloqueantes
El sistema SHALL marcar pending y blocking si falta evidencia, la revisión fuente no coincide, el estado de conocimiento no es known o la regla está incompleta; SHALL NOT convertir desconocidos en pass.

#### Scenario: Permiso sin confirmación
- **GIVEN** una fuente de permiso unknown
- **WHEN** se evalúa cobertura de permisos
- **THEN** el finding queda pending y bloqueante.

### Requirement: Compatibilidad declarada
El sistema SHALL bloquear una selección que no pertenece a los modelos admitidos declarados y evidenciados.

#### Scenario: Modelo EMT incompatible
- **GIVEN** una selección sintética `emt-3-4` y una lista evidenciada que sólo admite `emt-1`
- **WHEN** se evalúa compatibilidad
- **THEN** el finding es fail y bloqueante.
