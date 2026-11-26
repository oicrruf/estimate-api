# AT-247 — patrones sintéticos de instalación

`fixtures/patterns/patterns.v1.json` contiene cinco patrones `1.0.0`: cámara PoE, mesh, EMT, gabinete y energía. Sus reglas y referencias de fuente son ficticias. `registry_reference` produce el formato `installationPatterns` de AT-265. `DraftCandidate` conserva cantidad, reglas, fuentes, evidencia y rutas para la propuesta futura AT-240; no selecciona productos ni genera una BOM definitiva.

`expand` exige `application` confirmada con evidencia. Las condiciones `assumed` o `unknown` quedan pendientes. Mesh separa backhaul cableado e inalámbrico; UTP, conectores y prueba de enlace siguen la rama cableada. LB y toma interior exigen condición y cantidad confirmadas. Los límites `maxDepth` y `maxEdges` detienen la expansión; los ciclos se informan y los nodos repetidos se deduplican. Un límite alcanzado o cantidades contradictorias suprimen todos los candidatos de esa evaluación y quedan pendientes.

Para EMT, `evaluate_emt_with_at238` llama al evaluador AT-238 con el catálogo y ruta ficticios de su fixture sólo si la evidencia de medición coincide. AT-238 mantiene su propio cálculo de piezas comerciales, uniones, conectores y soportes. La salida del patrón y la de AT-238 siguen separadas.

Reproducción local:

```sh
python fixtures/patterns/build_fixture.py
UV_CACHE_DIR=/tmp/at247-uv-cache uv sync --frozen --extra dev
UV_CACHE_DIR=/tmp/at247-uv-cache uv run --no-sync pytest -q tests/at247
OPENSPEC_TELEMETRY=0 ci/at-206-docs/node_modules/.bin/openspec validate --specs --strict
OPENSPEC_TELEMETRY=0 ci/at-206-docs/node_modules/.bin/openspec validate --archived --strict
```

La prueba de Relate carga dos veces en un archivo temporal y consulta la ruta patrón→regla→fuente; no requiere servicio. Los resultados son candidatos para revisión profesional. No validan protección eléctrica, montaje físico, normativa local ni disponibilidad comercial.
