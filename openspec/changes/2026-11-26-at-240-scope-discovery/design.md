# Diseño

## Contrato

`ProjectIntake` registra meta, rubro, jurisdicción, necesidades, hechos y supuestos por separado. `PatternProvider` obtiene un `KnowledgePackage` por rubro y jurisdicción. Cada `Rule` posee ID, versión y fuente del paquete, evidencia, relación, paquete de trabajo y fórmula de cantidad. Los paquetes especializados pueden implementar el protocolo sin modificar el núcleo. El fixture vincula identificadores de evidencia sintética de AT-229; el lector consulta capacidad, pero aún no hay relaciones de instalación validadas.

`evaluate_scope` es la entrada del servicio local. Devuelve la propuesta y `scope-review.v1`, un contrato JSON Schema para la futura capa API/A2UI. El contrato AT-264 permanece canónico para el documento de proyecto; la adaptación del levantamiento AT-246 a `ProjectIntake` queda fuera de este slice.

`RelateEvidenceReader` ejecuta dos consultas Cypher fijas `MATCH/RETURN` con límite y devuelve `capability_context`, `node_only` o `unknown`. El lector no muta la base. El test levanta un store temporal desde el seed ficticio AT-229 y confirma conteos antes y después de leer. Las relaciones de capacidad AT-229 solo aportan contexto; no demuestran reglas de montaje. `commercialReady` en la salida pública exige propuesta aprobada, validación externa del paquete y referencias presentes. La fixture tiene referencias desconocidas, por lo que permanece bloqueada.

`hardware_adapter.evaluate_hardware_scope` consume el contrato ya integrado de AT-238 sin modificarlo. Conserva solo cantidades de ruta confirmada y deja las alternativas como faltantes separados; una ruta desconocida emite cero líneas y cero cantidades faltantes. El bloque `hardware` del payload es opcional (`null` cuando no aplica), y su validación profesional pendiente impide `commercialReady`. El puente entre ese bloque y una BOM persistida queda para el contrato de integración.

`registry_adapter.resolve_pattern_coverage` reutiliza `resolve_coverage` de AT-265. Solo comprueba la identidad del proyecto y que el paquete de patrones corresponda exactamente al ID y versión catalogados. `unsupported`, revisión no verificada, solape o referencia ausente quedan `pending_specialist` en la propuesta del servicio. `cataloged` indica cobertura declarada, no conformidad técnica; `commercialReady` exige además validación técnica externa, aprobación y evidencia suficiente. Las necesidades raíz sin reglas se conservan visibles y bloquean el alcance.

## Orquestación

`discover` recorre reglas aplicables en orden estable, con límite de profundidad y líneas, detección de ciclos y cantidades desconocidas expresadas como `None` y pregunta. La propuesta conserva solicitud, aportes y mediciones pendientes. Una pieza requerida rechazada bloquea la salida. `review` exige cantidad positiva antes de aprobar. `revalidate` reconstruye el alcance y marca cambios; invalida aprobaciones y preparación comercial anteriores. Cambiar la arquitectura requiere hechos nuevos y una nueva ejecución, no elegir una alternativa implícita.

## Límites de confianza

La aceptación comercial depende de cobertura especializada validada, revisión explícita y mediciones. El paquete de ejemplo solo garantiza comportamiento determinista. El resultado no produce precios, inventario ni selección de productos. La conexión con A2UI y escenarios sigue pendiente de sus contratos de integración.
