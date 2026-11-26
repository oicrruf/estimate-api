# inventory-risk Specification

## Purpose

Evaluar riesgo comercial de suministro a partir de evidencia trazable sin inferir elegibilidad técnica ni prometer disponibilidad.

## ADDED Requirements

### Requirement: Observaciones de stock diferenciadas

El dominio SHALL distinguir `unknown`, `published`, `supplier_confirmed` y `reserved`; SHALL conservar proveedor, sucursal, cantidad, fecha de observación, vigencia, reposición, fuente y evidencia cuando existan. Una cifra pública SHALL NOT contar como confirmación de suministro.

#### Scenario: Dos ofertas publicadas
- **GIVEN** dos ofertas sintéticas AT-229 de dos unidades cada una sin confirmación de proveedor
- **WHEN** se solicitan cuatro unidades
- **THEN** el riesgo y la brecha confirmada son desconocidos, y las cifras públicas se muestran como evidencia.

#### Scenario: Evidencia caducada
- **GIVEN** una confirmación con vigencia anterior al tiempo de evaluación
- **WHEN** se evalúa la oferta
- **THEN** la confirmación no respalda capacidad y la salida indica dato caducado.

### Requirement: Cobertura confirmada y pool compartido

El dominio SHALL calcular cobertura y brecha sólo desde capacidad confirmada vigente y SHALL limitar ofertas del mismo pool al límite confirmado de ese pool. Los umbrales de riesgo SHALL ser configurables. Un pool público o sin evidencia SHALL NOT respaldar capacidad confirmada.

#### Scenario: Dos de cuatro
- **GIVEN** dos ofertas confirmadas de dos cámaras cada una y un pool confirmado de dos
- **WHEN** se solicitan cuatro cámaras
- **THEN** la cobertura es 50%, la brecha es dos y el riesgo es alto con el umbral configurado de 50%.

#### Scenario: Dos de dos
- **GIVEN** el mismo pool confirmado
- **WHEN** se solicitan dos cámaras
- **THEN** la cobertura es 100%, la brecha es cero y el riesgo es bajo.

### Requirement: Dependencias documentadas

El dominio SHALL exponer dependencia común de pool o distribuidor sólo con fuente y evidencia. Compartir distribuidor SHALL NOT, por sí solo, demostrar un pool físico común ni reducir capacidad confirmada de ofertas independientes.

#### Scenario: Distribuidor común
- **GIVEN** dos relaciones `DISTRIBUTED_BY` con evidencia verificable
- **WHEN** se evalúan las ofertas
- **THEN** se informa el distribuidor común, conservando las fuentes, sin inferir pool compartido.

### Requirement: Separación de decisiones

La salida SHALL mantener riesgo comercial independiente de elegibilidad técnica, score y selección manual. SHALL solicitar revisión de alternativas cuando exista riesgo no bajo sin comprar, contactar o seleccionar automáticamente.

#### Scenario: Evidencia incompleta
- **GIVEN** una oferta con stock desconocido
- **WHEN** se evalúa el suministro
- **THEN** cantidad confirmada, cobertura y brecha son desconocidas; se requiere revisión de alternativas.
