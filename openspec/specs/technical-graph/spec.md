# technical-graph Specification

## Purpose

Conservar conocimiento técnico reutilizable y contextualizar candidatos por proyecto con un grafo reconstruible desde el catálogo persistido.

## Requirements

### Requirement: Identidades y evidencia estable
El sistema SHALL conservar los IDs de productos, capacidades y evidencias al reconstruir el grafo; SHALL mantener historial de revisión y motivo de rectificación de evidencia.

#### Scenario: Rectificación y reconstrucción
- **GIVEN** un catálogo con una evidencia de dos revisiones
- **WHEN** se construye el grafo y se consulta desde otro proceso
- **THEN** ambas revisiones y el ID de evidencia están presentes, y el snapshot es igual al reconstruido.

### Requirement: Contexto de proyecto
El sistema SHALL conservar relaciones técnicas al descartar un candidato de un proyecto y SHALL calcular elegibilidad por proyecto.

#### Scenario: Producto descartado en un proyecto
- **GIVEN** el mismo producto candidato en dos proyectos
- **WHEN** se marca descartado en el primero y elegible en el segundo
- **THEN** conserva capacidades y evidencia; solo el segundo lo devuelve como elegible.

### Requirement: Consultas técnicas reales
El sistema SHALL permitir consultar mediante Cypher capacidades, compatibilidades, requisitos y alternativas.

#### Scenario: Catálogo sintético
- **GIVEN** productos y relaciones de la fixture
- **WHEN** se ejecutan las consultas Cypher
- **THEN** cada tipo de relación produce el resultado esperado.

### Requirement: Persistencia local e integridad
El runtime SHALL conservar el snapshot tras cierre y nueva apertura del archivo y SHALL rechazar un segundo escritor concurrente.

#### Scenario: Proceso nuevo
- **GIVEN** un archivo Relate cerrado
- **WHEN** un proceso o contenedor nuevo lo abre
- **THEN** obtiene el mismo snapshot Cypher.

#### Scenario: Segundo escritor
- **GIVEN** una conexión que mantiene escritura sobre el archivo
- **WHEN** otro proceso intenta abrirlo para escritura
- **THEN** recibe un error de bloqueo y no adquiere escritura.

### Requirement: Restauración local
La prueba SHALL restaurar una copia del archivo cerrado en otro volumen nombrado y SHALL verificar la igualdad de consultas.

#### Scenario: Copia de respaldo
- **GIVEN** una copia tomada después de cerrar el store
- **WHEN** se abre desde el volumen de restauración
- **THEN** el snapshot coincide con el original.
