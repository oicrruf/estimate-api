# Diseño

## Entrada y almacenamiento

`--store` es obligatorio y apunta a un archivo local Relate. `seed` carga únicamente `demo/fixtures/seed.cypher` con `MERGE`, cierra la conexión y conserva el archivo. `evaluate` exige que exista, abre una conexión nueva y no modifica el grafo. `demo` ejecuta la siembra y después invoca evaluaciones en otro proceso Python, para probar la reapertura real.

## ADK y herramientas

Se fija Google ADK Python en una dependencia opcional de demo. Un agente local sin LLM recibe un request tipado en el estado de sesión del runner; sólo puede invocar herramientas con consultas Cypher constantes y parámetros enlazados. No acepta Cypher libre, nombres de labels ni rutas de archivo aportadas por un modelo. El runner produce un evento final JSON. El texto explicativo se construye a partir de códigos de razón y rutas de evidencia; ningún proveedor generativo interviene.

## Evaluación

Para switches se consultan puertos totales, puertos PoE, potencia y evidencia. El mínimo total deriva de `poe_ports_min + uplink_ports`, por lo que cambiar de 8 a 12 altera la elegibilidad de SW-16. Disponibilidad del pool y compatibilidad técnica son decisiones separadas. El UPS es un smoke de otro dominio. Precios sólo ordenan candidatos ya compatibles.

## Verificación

Tests del CLI en subprocess prueban mensajes JSON, rechazo de argumentos inválidos, archivo persistente reabierto, rutas y controles positivos/negativos. `ruff`, `mypy`, `pytest`, OpenSpec y CI deben pasar desde checkout limpio. La API y el endpoint real quedan fuera de este cambio.
