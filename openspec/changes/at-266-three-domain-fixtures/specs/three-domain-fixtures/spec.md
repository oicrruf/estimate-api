# three-domain-fixtures Specification

## Purpose

Ofrece datos ficticios reproducibles para comprobar límites entre dominios y preparar la integración del descubrimiento de alcance.

## ADDED Requirements

### Requirement: Casos de tres dominios
El sistema SHALL conservar casos sintéticos para ocho cámaras PoE con UTP y EMT, pintura de salón con superficie y capas/consumibles, y montaje audiovisual con cargas y recursos. Cada caso SHALL declarar cantidades de prueba y SHALL referenciar un proyecto válido y un paquete versionado del registro.

#### Scenario: Caso reproducible
- **GIVEN** uno de los tres casos
- **WHEN** se validan su documento y registro
- **THEN** ambos contratos son válidos, la cobertura identifica solo el paquete del dominio y permanece `pending_specialist` por revisión no verificada.

### Requirement: Relación genérica de faltantes e impactos
El arnés de prueba SHALL procesar los tres casos con la misma entrada tipada y SHALL comparar partidas derivadas y cantidades al cambiar la cantidad semilla, sin afirmar que el pipeline AT-240 ya está integrado.

#### Scenario: Cambio de cantidad ficticia
- **GIVEN** una semilla y reglas ficticias declaradas
- **WHEN** se cambia la cantidad de la semilla
- **THEN** las partidas por unidad cambian de forma determinista y las partidas fijas conservan su valor.

### Requirement: Aislamiento entre rubros
El arnés de prueba SHALL rechazar una regla cuyo paquete no cubra el dominio solicitado y SHALL rechazar reglas no declaradas o de versión incompatible.

#### Scenario: Regla de cámaras en pintura
- **GIVEN** un caso de pintura con una regla del paquete de cámaras
- **WHEN** se evalúa el caso
- **THEN** la regla se rechaza antes de producir partidas de cámaras.
