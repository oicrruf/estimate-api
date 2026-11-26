# installation-patterns Specification

## Purpose

Derivar candidatos de instalación trazables a partir de patrones sintéticos versionados.

## ADDED Requirements

### Requirement: Condiciones evidenciadas
El sistema SHALL expandir dependencias obligatorias sólo con hechos confirmados y evidencia identificable; SHALL dejar condiciones desconocidas o supuestas pendientes.

#### Scenario: Mesh cableado
- **GIVEN** backhaul cableado confirmado con evidencia
- **WHEN** se evalúa el patrón mesh
- **THEN** aparecen UTP, conectores y prueba de enlace con ruta y regla.

#### Scenario: Mesh desconocido
- **GIVEN** backhaul desconocido
- **WHEN** se evalúa el patrón mesh
- **THEN** no se selecciona UTP ni la rama inalámbrica y ambas quedan pendientes.

### Requirement: Condiciones de caja y energía
LB y tomacorriente interior SHALL requerir condiciones de diseño confirmadas. Un patrón SHALL señalar montaje y pruebas cuando sus hechos de aplicación están evidenciados. La salida SHALL exigir revisión profesional sin declarar aprobación normativa.

#### Scenario: Gabinete con toma confirmada
- **GIVEN** una condición confirmada para la toma interior con cantidad evidenciada
- **WHEN** se evalúa el patrón de gabinete
- **THEN** aparece un candidato de toma trazable y se exige revisión profesional.

### Requirement: Grafo acotado
La expansión SHALL detectar ciclos, deduplicar dependencias y respetar límites de profundidad y aristas. La fixture SHALL persistir y consultar relaciones con evidencia en Relate de forma idempotente, sin eliminar datos ajenos.

#### Scenario: Segundo seed y ciclo
- **GIVEN** un archivo Relate sintético y un patrón con ciclo
- **WHEN** se carga la fixture dos veces y se expande el patrón
- **THEN** los conteos no cambian y el ciclo queda informado sin expansión infinita.

### Requirement: Compatibilidad de contratos
El paquete SHALL referenciar el formato `installationPatterns` de AT-265 y exponer candidatos tipados para una futura propuesta AT-240, sin modificar esos módulos.

#### Scenario: Referencia del registro
- **GIVEN** los cinco patrones sintéticos
- **WHEN** se agregan sus referencias a un paquete AT-265 aplicable
- **THEN** el registro valida y los candidatos conservan regla, fuente y evidencia.
