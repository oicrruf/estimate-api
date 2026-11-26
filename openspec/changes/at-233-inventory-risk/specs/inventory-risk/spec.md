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

#### Scenario: Observaciones ambiguas
- **GIVEN** dos observaciones para una oferta o una observación que identifica simultáneamente oferta y pool
- **WHEN** se lee Relate
- **THEN** el lector rechaza el snapshot sin escoger una cantidad arbitraria.

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

Una dependencia de pool SHALL identificar el mismo pool que ambas ofertas vinculadas; una identidad discordante SHALL rechazarse sin sumar esas ofertas como independientes.

#### Scenario: Distribuidor común
- **GIVEN** dos relaciones `DISTRIBUTED_BY` con evidencia verificable
- **WHEN** se evalúan las ofertas
- **THEN** se informa el distribuidor común, conservando las fuentes y elevando riesgo bajo a medio, sin inferir pool compartido.

#### Scenario: Pool declarado sin identidad coherente
- **GIVEN** una dependencia de pool documentada pero una oferta sin ese ID de pool
- **WHEN** se evalúan las ofertas
- **THEN** el snapshot se rechaza antes de calcular cobertura.

### Requirement: Reservas vinculadas a la cotización

El dominio SHALL contar reservas de oferta y pool sólo con ID, evidencia, fuente, proyecto, cotización y vencimiento explícitos. El proyecto y la cotización SHALL coincidir exactamente con el contexto; el vencimiento es exclusivo. Una reserva inválida SHALL conservar evidencia sin afirmar capacidad ni inventario cero. Un mismo ID de hold SHALL contarse una sola vez entre ofertas.

#### Scenario: Hold válido para cuatro unidades
- **GIVEN** dos unidades confirmadas independientes y un hold de dos para el proyecto y la cotización actual
- **WHEN** se evalúan cuatro unidades antes de vencer el hold
- **THEN** la cobertura confirmada es 100%.

#### Scenario: Hold ajeno o sin referencia
- **GIVEN** el mismo hold con cotización diferente o ausente
- **WHEN** se evalúan cuatro unidades
- **THEN** la capacidad total es desconocida, se conservan las dos unidades confirmadas independientes y la evidencia del hold se explica sin contarlo.

#### Scenario: Vencimiento exacto
- **GIVEN** un hold del pool con referencia correcta
- **WHEN** se evalúa exactamente en su vencimiento
- **THEN** el límite reservado no respalda capacidad y la evaluación informa `POOL_EXPIRED_RESERVATION`.

### Requirement: Separación de decisiones

La salida SHALL mantener riesgo comercial independiente de elegibilidad técnica, score y selección manual. SHALL solicitar revisión de alternativas cuando exista riesgo no bajo sin comprar, contactar o seleccionar automáticamente.

#### Scenario: Evidencia incompleta
- **GIVEN** una oferta con stock desconocido
- **WHEN** se evalúa el suministro
- **THEN** cantidad confirmada, cobertura y brecha son desconocidas; se requiere revisión de alternativas.
