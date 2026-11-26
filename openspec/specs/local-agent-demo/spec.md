# local-agent-demo Specification

## Purpose

Permitir una demostración local reproducible con agente ADK sin LLM y evidencia consultada en Relate.

## Requirements

### Requirement: Entrada local persistente
La demo SHALL exigir una ruta de archivo Relate explícita, SHALL sembrar el fixture ficticio de forma idempotente y SHALL reabrir el archivo desde otro proceso para evaluar. No SHALL requerir credenciales ni proveedor externo durante la ejecución.

#### Scenario: Reapertura después de sembrar
- **GIVEN** un archivo nuevo en una ruta local indicada por el operador
- **WHEN** se ejecuta `seed` y después `evaluate` en otro proceso
- **THEN** la segunda ejecución obtiene los mismos productos y rutas de evidencia sin volver a sembrar.

### Requirement: Herramientas delimitadas
El agente ADK SHALL invocar sólo consultas Cypher fijas y de lectura con parámetros validados. No SHALL aceptar texto Cypher arbitrario como entrada.

#### Scenario: Argumento inválido
- **GIVEN** un escenario o un mínimo PoE fuera del esquema de la CLI
- **WHEN** se invoca la evaluación
- **THEN** la CLI rechaza el argumento sin ejecutar una consulta libre ni modificar el store.

### Requirement: Selección respaldada por evidencia
La demo SHALL clasificar compatibilidad técnica y disponibilidad por separado, SHALL conservar rutas hasta nodos de evidencia y SHALL ordenar por precio sólo entre productos elegibles.

#### Scenario: Ocho puertos PoE más uplink
- **GIVEN** el requisito de ocho puertos PoE y un uplink distinto
- **WHEN** se evalúan SW-8 y SW-16
- **THEN** SW-8 es incompatible por tener ocho puertos totales y SW-16 es seleccionable con rutas de evidencia.

#### Scenario: Requisito cambiado a doce PoE
- **GIVEN** el mismo store sin modificar
- **WHEN** el operador pasa un mínimo PoE tipado de doce
- **THEN** SW-16 deja de ser elegible y se muestra la capacidad PoE documentada de ocho.

#### Scenario: Pool compartido
- **GIVEN** cuatro cámaras solicitadas, dos ofertas y un pool físico de dos
- **WHEN** se consulta la disponibilidad
- **THEN** la salida indica dos disponibles y stock insuficiente con evidencia del pool.

#### Scenario: Segundo dominio
- **GIVEN** un UPS ficticio de 1500 VA y un mínimo de 1000 VA
- **WHEN** se ejecuta el smoke de UPS
- **THEN** la salida muestra compatibilidad y una ruta a la ficha ficticia.
