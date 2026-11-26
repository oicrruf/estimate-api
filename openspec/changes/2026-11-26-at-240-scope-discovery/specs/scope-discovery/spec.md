# scope-discovery Specification

## Purpose

Descubrir y revisar el alcance técnico a partir de una intención de proyecto y conocimiento especializado trazable.

## ADDED Requirements

### Requirement: Ingreso neutral y cobertura especializada
El sistema SHALL conservar objetivo, necesidades, hechos y supuestos separados y SHALL resolver un paquete por rubro, versión y jurisdicción. Sin cobertura aplicable SHALL devolver `pending_specialist`.

#### Scenario: Nuevo rubro
- **GIVEN** un proyecto de un rubro distinto y un paquete sintético válido
- **WHEN** se descubre su alcance
- **THEN** el núcleo conserva el mismo contrato y cita la fuente y versión del paquete.

### Requirement: Expansión acotada y explicable
El sistema SHALL producir líneas solicitadas, propuestas y pendientes, con cantidad o ausencia explícita, unidad, regla, evidencia, relación y paquete de trabajo. SHALL detener ciclos y respetar límites configurables.

#### Scenario: Proyecto ficticio de red
- **GIVEN** la solicitud de ocho cámaras, nodos y switch y un patrón versionado de ejemplo
- **WHEN** se descubre el alcance
- **THEN** aparecen enlaces, terminaciones, montaje, canalización, energía y servicios con preguntas sobre mediciones desconocidas.

### Requirement: Puerta de revisión
El sistema SHALL exigir aprobación de líneas añadidas y cantidades conocidas antes de permitir necesidades comerciales. SHALL bloquear una propuesta cuando se rechaza una dependencia requerida.

#### Scenario: Accesorio necesario rechazado
- **GIVEN** una BOM propuesta con terminaciones requeridas
- **WHEN** el usuario las rechaza
- **THEN** la propuesta queda bloqueada y no está lista para investigación comercial.

### Requirement: Revalidación
Al cambiar requisitos o arquitectura, el sistema SHALL repetir descubrimiento, señalar altas, bajas y cambios, e invalidar aprobaciones comerciales previas.

#### Scenario: Aumento de cámaras
- **GIVEN** una propuesta revisada para ocho cámaras
- **WHEN** la entrada cambia a doce
- **THEN** se recalculan las cantidades derivadas y se exige nueva revisión.

### Requirement: Contrato de revisión y evidencia conservadora
El sistema SHALL producir una salida de servicio versionada que distinga solicitud, propuesta, pendiente, rechazo y cambios. SHALL conservar `unknown` si falta evidencia o medición. Una ruta Relate de capacidad SHALL identificarse como contexto y no como validación de una regla de instalación.

#### Scenario: Grafo sintético AT-229
- **GIVEN** el seed sintético en un store local aislado
- **WHEN** el servicio evalúa un proyecto y consulta referencias de evidencia
- **THEN** muestra la ruta de capacidad presente, mantiene desconocidas las dependencias sin evidencia y no habilita cotización comercial.

### Requirement: Cobertura de paquete fail-closed
El servicio SHALL consumir el resultado de cobertura del registro versionado y SHALL mantener `pending_specialist` si falta revisión, hay incompatibilidad de identidad, existe una necesidad raíz sin reglas o la cobertura es insuficiente. Un paquete catalogado SHALL no equivaler a validación técnica.

#### Scenario: Necesidad sin patrón
- **GIVEN** un proyecto con una necesidad adicional sin regla en el paquete aplicable
- **WHEN** se genera la propuesta
- **THEN** la necesidad permanece visible, aparece una pregunta de cobertura y no se habilita cotización.

### Requirement: Candidatos versionados y topología medible
El sistema SHALL conservar como candidatos revisables las rutas, reglas, fuentes y evidencias de patrones versionados. SHALL mantener cada enlace requerido aunque falte su medida, y SHALL no publicar totales comerciales de cable de una topología parcialmente medida.

#### Scenario: Patrón y enlace sintéticos
- **GIVEN** una necesidad declarada con hechos confirmados AT-247 y topología AT-239 parcialmente medida
- **WHEN** se descubre el alcance
- **THEN** aparecen candidatos con procedencia, todos los enlaces exigidos y cable pendiente sin metraje total inventado.

### Requirement: Alternativa condicionada y revalidación
El sistema SHALL bloquear rechazo de una pieza imprescindible y SHALL mostrar una alternativa únicamente cuando la arquitectura y los hechos que activan el patrón alternativo estén confirmados; SHALL invalidar aprobación anterior y señalar altas y bajas.

#### Scenario: Backhaul mesh
- **GIVEN** un enlace cableado rechazado
- **WHEN** el backhaul cambia a inalámbrico con evidencia confirmada
- **THEN** el diff retira las piezas cableadas, propone las tareas inalámbricas y mantiene la nueva solución pendiente de revisión y validación técnica.
