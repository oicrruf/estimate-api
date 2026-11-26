# Spec Delta

## Purpose

Demostrar evaluaciones técnicas explicables con datos ficticios y rutas de evidencia reproducibles en Relate.

## ADDED Requirements

### Requirement: Grafo de evidencia ficticio
La demo SHALL representar `REQUIREMENT`, `PRODUCT`, `CAPABILITY`, `OFFER`, `EVIDENCE` y `ACCESSORY` con IDs estables, y SHALL enlazar requisitos, capacidades, evidencia, incompatibilidades y accesorios obligatorios. El seed SHALL ser idempotente y no SHALL borrar datos ajenos.

#### Scenario: Segunda carga
- **GIVEN** una base local con el seed cargado
- **WHEN** se ejecuta el mismo seed otra vez
- **THEN** los conteos de nodos y relaciones permanecen iguales.

### Requirement: Compatibilidad técnica independiente del precio
La evaluación SHALL explicar el cumplimiento de puertos, potencia y resolución mediante rutas que terminen en evidencia. El precio SHALL ser sólo informativo.

#### Scenario: Uplink distinto
- **GIVEN** ocho puertos PoE compatibles y un uplink distinto
- **WHEN** se evalúa un switch de ocho puertos totales y otro de dieciséis
- **THEN** el primero se excluye por requerirse nueve puertos totales y el segundo satisface el requisito original.

#### Scenario: Cambio de requisito
- **GIVEN** un switch de dieciséis puertos totales con ocho puertos PoE
- **WHEN** el mínimo PoE aumenta a doce
- **THEN** el switch resulta incompatible aunque antes era compatible.

### Requirement: Disponibilidad compartida
La evaluación SHALL limitar la cantidad disponible por el pool compartido y SHALL calcular ese límite separadamente de la compatibilidad técnica.

#### Scenario: Cuatro unidades de dos ofertas
- **GIVEN** dos ofertas de dos unidades del mismo producto y un pool conjunto de dos
- **WHEN** se solicitan cuatro cámaras
- **THEN** la cantidad disponible es dos y el estado es `INSUFFICIENT_STOCK`.

#### Scenario: Control positivo de dos unidades
- **GIVEN** el mismo pool conjunto de dos
- **WHEN** se solicitan dos cámaras sin modificar el seed
- **THEN** el estado es `COMPATIBLE`.

### Requirement: Dependencias y evidencia incompleta
La evaluación SHALL mostrar accesorios requeridos sin oferta y SHALL emitir `UNKNOWN` ante campos técnicos obligatorios no documentados.

#### Scenario: Adaptador ausente
- **GIVEN** una cámara de 12 V que requiere adaptador sin oferta
- **WHEN** se evalúa su adquisición
- **THEN** se muestra la ruta `REQUIRES_ACCESSORY` y `MISSING_ACCESSORY_OFFER`.

#### Scenario: Potencia desconocida
- **GIVEN** una cámara sin `drawW` documentado
- **WHEN** se evalúa el presupuesto PoE
- **THEN** el estado es `UNKNOWN` con `drawW` entre los campos faltantes.

### Requirement: Salida con rutas y segundo dominio acotado
La demo SHALL producir rutas con nodos y relaciones identificables y SHALL incluir un caso de UPS como control de reutilización, sin afirmar que exista un endpoint de producción.

#### Scenario: UPS con evidencia
- **GIVEN** un requisito ficticio de 1000 VA y un UPS ficticio de 1500 VA
- **WHEN** se evalúa el producto
- **THEN** se obtiene una ruta positiva desde requisito y producto hasta capacidad y evidencia.
