# ADR: SQL para catálogo y ofertas; grafo para explicación

**Estado:** propuesta para la integración, 2026-11-26.

## Decisión

Conservar SQL como fuente de verdad de productos, ofertas, precios, proveedores y disponibilidad. Construir una proyección de grafo versionada para requisitos, capacidades, accesorios y evidencia. La API obtiene el cálculo de inventario desde SQL (incluidos pools compartidos) y usa el grafo para rutas explicables. Cada evaluación guarda IDs de fuente y versión de proyección.

## Motivo

Las relaciones técnicas tienen varias etapas: una necesidad exige capacidad; un producto declara otra capacidad respaldada por evidencia; un accesorio puede ser obligatorio. El grafo hace visibles esos caminos y los cambios de requisito. Las sumas, reservas, transacciones y concurrencia de inventario siguen siendo más simples y seguras en SQL.

## Costes y límites

- La proyección puede quedar atrasada. Mostrar versión/fecha y marcar `UNKNOWN` si faltan afirmaciones; no convertir ausencia de datos en compatibilidad.
- No sumar ofertas que comparten `poolId`. El pool se resuelve en SQL; el fixture de grafo reproduce el límite para la demo.
- `INCOMPATIBLE_WITH` puede materializar razones de una evaluación concreta, pero debe recalcularse cuando cambian requisitos o evidencia. No usarlo como verdad universal.
- Los caminos de evidencia no sustituyen la validación de calidad de la fuente. Una ficha ficticia sólo demuestra la forma del contrato.

## Alternativas consideradas

SQL solamente: menos infraestructura, pero las rutas de varias relaciones requieren joins y lógica de explicación adicional. Grafo como fuente única: facilita recorridos, pero complica transacciones de precios y reservas. Para esta demo se elige una proyección aislada, sin sincronización de producción.
