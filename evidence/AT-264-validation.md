# AT-264 — evidencia de validación

Base: `origin/develop` en `6ecc9a9c5d6ba6355e3332f8b6533c81ed878b74`
(AT-207 backend integrado). Rama: `feature/AT-264-universal-core`.

Python 3.12.14 y uv 0.7.6, 2026-11-26:

```sh
uv sync --frozen --extra dev
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy src scripts tests
uv run --no-sync pytest -q
uv run --no-sync python scripts/openapi.py --check
uv run --no-sync python scripts/check_secrets.py
ci/at-206-docs/node_modules/.bin/openspec validate --specs --strict
ci/at-206-docs/node_modules/.bin/openspec validate --archived --strict
```

Resultados locales: lint y formato correctos; mypy sin problemas en 17 archivos;
14 tests aprobados, 0 fallidos (7 del contrato AT-264); OpenAPI sin deriva;
sin posibles secretos; 5 specs y 3 cambios archivados válidos en modo estricto.
El wheel `estimate_api-0.1.0-py3-none-any.whl` incluye el validador Python y
`project-document.v1.schema.json`.

Las pruebas cubren los trece tipos genéricos, cámaras, pintura y montaje de
evento con datos sintéticos. Los casos negativos comprueban origen ausente,
tipo o versión desconocidos, campo de dominio en el núcleo, id duplicado,
relación rota, sujeto de paquete ausente y referencia de proyecto equivocada.

AT-246 mantiene la semántica de levantamiento técnico; AT-264 aporta sólo el
contrato común. No se usaron servicios de producto ni datos reales. El merge
y cualquier actualización de Linear pertenecen al hilo principal.
