## ADDED Requirements

### Requirement: Enlaces condicionados por topología

El sistema SHALL exigir enlace para cada extremo PoE, backhaul cableado confirmado y uplink declarado. Una cámara Wi-Fi/solar SHALL NOT generar UTP por defecto.

#### Scenario: Medios distintos

- **GIVEN** cámaras PoE y Wi-Fi/solar y nodos mesh con y sin backhaul cableado
- **WHEN** se evalúa la topología
- **THEN** sólo se generan enlaces exigidos por el diseño declarado.

### Requirement: Metraje sustentado

El sistema SHALL sumar longitudes de secciones medidas, holgura y desperdicio explícitos por enlace. SHALL conservar rutas no medidas como pendientes sin añadir metros ficticios.

#### Scenario: Aumento de cámaras

- **GIVEN** una ruta medida y cámaras nuevas sin trayecto
- **WHEN** se recalcula
- **THEN** aparecen enlaces pendientes y el metraje confirmado no cambia.

### Requirement: Compatibilidad y evidencia

El sistema SHALL identificar cable, terminaciones, puerto y ambiente incompatibles con rutas de evidencia. SHALL separar metros requeridos de compra comercial y exigir revisión profesional de límites y condiciones no verificados.

#### Scenario: Cambio de ambiente

- **GIVEN** un cable de interior en un trayecto exterior
- **WHEN** se evalúa
- **THEN** se marca incompatibilidad, sin eliminar candidatos del catálogo.

### Requirement: Relate reproducible

La fixture SHALL crear caminos de extremo a enlace, cable y evidencia mediante `MERGE`, sin borrar otros datos.

#### Scenario: Segunda carga

- **GIVEN** archivo Relate temporal con seed sintético
- **WHEN** se carga dos veces
- **THEN** los conteos no cambian y las consultas recuperan los caminos esperados.
