# Diseño

Cada patrón tiene ID, versión, categoría, nodo raíz, fuente y límites. Las aristas `REQUIRES` tienen condición explícita (`always`, `confirmed_true`, `equals`), cantidad y regla. Los hechos de entrada distinguen `confirmed`, `assumed` y `unknown`, con ID de evidencia sólo en el primer caso. Una condición sin prueba queda pendiente. La expansión recorre a lo sumo `maxDepth` y `maxEdges`, detecta ciclos por ruta y suma una línea una sola vez por clave de dependencia. La salida retiene rutas y fuentes; una interfaz `DraftCandidate` queda disponible para AT-240.

La fixture contiene solo tipos genéricos sintéticos. El seed Relate usa IDs con espacio de nombres AT-247 y `MERGE`, sin borrar datos. La prueba usa un archivo temporal y verifica recarga y consulta real. La evaluación de EMT medida sigue perteneciendo a AT-238; un adaptador invoca su `evaluate_route` sólo cuando la evidencia de la ruta coincide con el hecho confirmado.
