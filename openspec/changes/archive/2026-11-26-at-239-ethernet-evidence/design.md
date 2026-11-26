## Context

AT-229 aporta Relate local y AT-238 dimensiona EMT desde rutas confirmadas. AT-239 consume la misma noción de tramo, sin editar ambos paquetes.

## Decisions

- `evaluate_topology` recibe catálogo y topología declarados; devuelve enlaces, materiales medibles, incompatibilidades y pendientes.
- Cada requisito y cantidad señala regla y evidencia sintética. El seed usa `MERGE` y prefijo AT-239.
- La salida separa metros requeridos de rollos comerciales y deja verificaciones profesionales pendientes.

## Risks

La ficha de cable sintética no acredita cumplimiento normativo, PoE, ancho de banda ni ocupación de conduit. Esas comprobaciones permanecen pendientes para evidencia técnica de fabricante y medición del sitio.
