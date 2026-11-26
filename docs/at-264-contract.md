# AT-264 — contrato universal v1

`src/estimate_api/contracts/schemas/project-document.v1.schema.json` es el contrato JSON Schema 2020-12
versionado como `1.0.0`. `src/estimate_api/contracts/universal_v1.py` define
los tipos Python 3.12 y `validate_project_document` comprueba el esquema, ids
duplicados y referencias internas. `projectId` debe apuntar a un `ProjectGoal`.

Todas las entidades usan el mismo sobre: `id`, `kind`, `label`, `origin`,
`scope`, `revision`, `knowledgeState` y relaciones opcionales. `revision` es
un entero positivo de la fuente; `id` permanece estable entre revisiones.
`knowledgeState` admite `known`, `assumed`, `unknown` y `conflicted`.
`origin.ref` identifica la fuente declarada sin afirmar que haya sido
verificada.

Los hechos específicos del dominio van en `packages[]`: `id`, `namespace`,
`version`, `subjectId` y `facts`. El núcleo valida el sobre y la existencia
del sujeto. Un consumidor de dominio debe validar `facts` con su esquema
propio. Los fixtures de `fixtures/valid/` modelan cámaras, pintura y montaje
de evento con datos ficticios. `fixtures/invalid/` documenta rechazos.

**Límite con AT-246:** este contrato no define medidas, croquis, activos del
cliente, quién suministra un recurso, exclusiones, preguntas bloqueantes ni
las reglas que producen un scope draft. AT-246 puede representar resultados
mediante estas entidades y paquetes, manteniendo su contrato y validación de
levantamiento aparte.

Las dependencias están fijadas en `pyproject.toml` y `uv.lock`. Para
reproducir las pruebas con Python 3.12 y uv 0.7.6:

```sh
uv sync --frozen --extra dev
uv run --no-sync pytest -q tests/at264
uv run --no-sync mypy src/estimate_api/contracts
```

El registro de CI y la gestión global de dependencias pertenecen a AT-207.
