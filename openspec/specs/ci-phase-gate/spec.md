# ci-phase-gate Specification

## Purpose

Hacer visible cada fase de CI de API sin debilitar el contexto protegido `verify`.

## Requirements

### Requirement: Fases visibles con cobertura preservada

El workflow SHALL mostrar jobs separados para calidad Python, pytest, OpenAPI, OpenSpec y evidencia de arquitectura, secretos y metadatos, y build y health smoke del contenedor. SHALL conservar triggers, permisos de lectura, versiones fijadas, comandos existentes y workflows especializados.

#### Scenario: Falla localizada
- **GIVEN** un error de tipos Python y las demás fases verdes
- **WHEN** termina CI
- **THEN** el job de calidad Python indica el fallo y el resumen protegido también falla.

#### Scenario: Push a develop
- **GIVEN** un evento push a develop
- **WHEN** corre el job de seguridad
- **THEN** se ejecuta el análisis de secretos y sólo se omite el paso de metadatos PR.

### Requirement: Resumen protegido fail-closed

El job `verify` SHALL conservar el nombre del contexto protegido, depender de todas las fases requeridas y ejecutarse después de fallos u omisiones. SHALL aprobar únicamente cuando cada fase requerida termine en `success`.

#### Scenario: Todos los jobs verdes
- **GIVEN** seis resultados `success`
- **WHEN** se ejecuta el resumen
- **THEN** `verify` aprueba.

#### Scenario: Un resultado no exitoso
- **GIVEN** cinco resultados `success` y uno `failure`, `skipped`, `cancelled` o ausente
- **WHEN** se ejecuta el resumen
- **THEN** `verify` falla y no da un verde accidental.
