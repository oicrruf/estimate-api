# AT-278 — API local para la vista Angular

**Contrato:** `GET /v1/demo/evaluate`, servidor separado de `estimate_api.app`, sólo `127.0.0.1:8001`. Datos, precios y ofertas son ficticios. No hay LLM, cuentas ni proveedor externo en ejecución. Requisitos: Python 3.12, `uv` 0.7.6; la primera instalación de dependencias fijadas requiere PyPI.

Desde el checkout de `estimate-api`, en dos terminales:

```sh
uv run --frozen --extra demo python -m demo.agent.cli seed --store /tmp/estimate-at278.rl
uv run --frozen --extra demo python -m demo.preview_api --store /tmp/estimate-at278.rl --port 8001
```

La siembra es idempotente y es el único paso que escribe el grafo. El servidor exige un archivo ya sembrado y lo abre de sólo lectura. El archivo persiste y se reabre entre procesos.

```sh
curl -sS 'http://127.0.0.1:8001/v1/demo/evaluate?scenario=switch'
curl -sS 'http://127.0.0.1:8001/v1/demo/evaluate?scenario=switch&poe_ports_min=12'
curl -sS 'http://127.0.0.1:8001/v1/demo/evaluate?scenario=camera&quantity=4'
curl -sS 'http://127.0.0.1:8001/v1/demo/evaluate?scenario=camera&quantity=2'
curl -sS 'http://127.0.0.1:8001/v1/demo/evaluate?scenario=ups'
```

`scenario` es obligatorio. `poe_ports_min` es opcional sólo para switch (por defecto 8; 1..16); `quantity` sólo para camera (por defecto 4; 1..16). Otros parámetros, duplicados o mal formados devuelven HTTP 422. `/openapi.json` publica el contrato tipado local (`evaluateDemoV1`). La respuesta conserva el JSON de `evaluate_offline` AT-227: `scenario`, `requirementId`, `engine`, `tool`, `selectedProductId`, `candidates` con `productId`, `offerIds`, `status`, `reasonCodes`, `measured`, `evidencePaths`; switch incluye `requested` y `fictitiousPriceUsd`, camera incluye `requestedQuantity` y `availableQuantity`. Las rutas contienen nodos con `id`, `type` y `source` para evidencias, más `relations`. Se omite el campo de diagnóstico CLI `storePath` para no revelar rutas del host.

Resultado esperado: switch SW-8 incompatible porque ocho puertos totales no cubren ocho PoE más un uplink; SW-16 elegible. Con doce PoE, ningún switch es elegible. Camera con cuatro unidades sólo dispone de dos en el pool compartido; con dos es elegible. UPS cumple técnicamente y no tiene oferta, por lo que `selectedProductId` es `null`. `selectedProductId: null` no es una aprobación ni una selección comercial.

Para Angular local, configure el servidor de desarrollo como proxy del mismo origen: `/v1/demo` → `http://127.0.0.1:8001`. El servidor no habilita CORS; la UI debe llamar a `/v1/demo/evaluate` sin URL absoluta. Este PR sólo entrega el lado API; no monta una ruta pública, no despliega y no sustituye el contrato productivo `contracts/openapi.json`. Fallback: la CLI AT-227 documentada en `demo/agent/README.md`.

Pruebas: `uv run --frozen --extra dev --extra demo pytest -q tests/at278`.
