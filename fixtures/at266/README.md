# AT-266 — casos ficticios

`cameras.json`, `painting.json` y `event.json` usan el contrato de prueba `DiscoveryInput` definido en `tests/at266/fixture_harness.py`. Referencian los documentos AT-264 en `fixtures/valid/` y los paquetes AT-265 de `registry.json`. Todo es ficticio. Los factores y cantidades fueron elegidos para comprobar relaciones e impactos; no son metrajes reales, rendimientos recomendados ni estándares.

Ejecutar: `uv run --no-sync pytest -q tests/at266`. El arnés es exclusivo de pruebas y no está conectado con el pipeline AT-240. Sus paquetes no verificados devuelven `pending_specialist`.
