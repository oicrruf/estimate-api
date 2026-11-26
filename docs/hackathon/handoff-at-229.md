# AT-229: entrega de la demo Relate

## Alcance

Esta entrega contiene únicamente OpenSpec, fixtures y documentación de AT-229. El dataset y los precios son ficticios. El ejemplo `planned-evidence-api.yaml` es una propuesta de demo; AT-227 implementará el contrato de ejecución. AT-206 ya está integrado en la base `develop` de esta rama. AT-207 y AT-215 siguen separados.

## Reproducción local sin servicio ni credenciales

Desde la raíz de `estimate-api` con Python 3.12 y `uv`:

```sh
UV_CACHE_DIR=/tmp/at229-uv-cache uv venv /tmp/at229-relate
UV_CACHE_DIR=/tmp/at229-uv-cache uv pip install --python /tmp/at229-relate/bin/python 'relate-db==1.3.0'
python3 demo/fixtures/build_seed.py
/tmp/at229-relate/bin/python demo/fixtures/verify_relate.py
```

Resultado observado: Q1–Q9 `OK`; 60 nodos y 61 relaciones; seed cargado dos veces; base cerrada y reabierta dos veces sin cambiar conteos. El SHA-256 de `seed.cypher` generado permaneció en `b64ae48df3cf6763963513bebc90dc015f5978e38abb5baf7609c5ea64750a40`.

Para OpenSpec, el CLI fijado en `ci/at-206-docs` se puede instalar con:

```sh
npm_config_cache=/tmp/at229-npm-cache npm ci --ignore-scripts --no-audit --no-fund --prefix ci/at-206-docs
OPENSPEC_TELEMETRY=0 ci/at-206-docs/node_modules/.bin/openspec validate --specs --strict
OPENSPEC_TELEMETRY=0 ci/at-206-docs/node_modules/.bin/openspec validate --archived --strict
```

La implementación real debe mapear los IDs y relaciones devueltos por Cypher a las rutas tipadas del ejemplo API, confirmar el pool en SQL transaccional y probar el endpoint desde su entrada de usuario. Este PR no implementa ni prueba ese endpoint.
