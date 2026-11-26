# hardware-dependencies Specification

## Purpose

Derivar dependencias de ferretería explicables desde topología confirmada y conservar incertidumbre cuando falta información.

## ADDED Requirements

### Requirement: Topología confirmada
El sistema SHALL derivar unidades comerciales de EMT por sección medida y cantidades de uniones, conectores y soportes sólo desde conteos confirmados; cada cantidad SHALL señalar regla y evidencia.

#### Scenario: Ruta ficticia de dos secciones
- **GIVEN** una ruta ficticia de EMT de 1 pulgada con dos secciones medidas, una unión, dos entradas y tres soportes confirmados
- **WHEN** se evalúa la ruta
- **THEN** se obtienen dos piezas comerciales, una unión, dos conectores y tres soportes con evidencia identificable.

### Requirement: Compatibilidad por diámetro
El sistema SHALL invalidar accesorios seleccionados cuyo diámetro no coincide y SHALL proponer tipos genéricos compatibles documentados, sin seleccionar automáticamente productos de fabricante.

#### Scenario: Cambio a tres cuartos
- **GIVEN** accesorios de 1 pulgada seleccionados
- **WHEN** la ruta confirmada cambia a 3/4 de pulgada
- **THEN** esos accesorios se invalidan y se muestran alternativas de 3/4 con evidencia.

### Requirement: Condiciones y desconocidos
El sistema SHALL mantener pendientes las cantidades de ruta no confirmada. No SHALL crear LB ni tomacorriente interior sin condición de diseño confirmada. El resultado SHALL exigir validación profesional para seguridad y normativa.

#### Scenario: Ruta desconocida
- **GIVEN** una ruta sin medidas ni topología confirmadas
- **WHEN** se evalúa
- **THEN** las cantidades permanecen pendientes y no se produce BOM de instalación.

### Requirement: Grafo reproducible
La fixture SHALL cargar relaciones técnicas y rutas a evidencia en Relate de forma idempotente, sin borrar datos ajenos.

#### Scenario: Consulta local
- **GIVEN** un archivo Relate temporal con el seed ficticio
- **WHEN** se consulta compatibilidad y evidencia y se recarga el seed
- **THEN** se recuperan las relaciones esperadas y los conteos no cambian.
