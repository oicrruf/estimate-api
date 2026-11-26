# AT-265 — registro de paquetes de conocimiento

`src/estimate_api/knowledge/schemas/knowledge-registry.v1.schema.json` define el contrato de intercambio `1.0.0`; `registry_v1.py` aporta tipos, `validate_registry` y `resolve_coverage`. El catálogo queda separado del documento de proyecto AT-264. Un paquete del proyecto lo referencia por `namespace` y `version` exactos.

Cada entrada declara taxonomía, especificaciones de categoría, patrones de instalación, conjuntos de reglas, fuente y versión, jurisdicciones, categorías y ámbitos aplicables, límites y revisor requerido. `review.state=verified` exige referencia de revisor y evidencia, pero es un dato declarado: el módulo no valida identidad ni competencia profesional. `ruleSets` contiene declaraciones opacas `topic`/`choice` para detectar diferencias explícitas; no evalúa reglas.

`resolve_coverage` devuelve `cataloged` solo cuando existe exactamente un paquete aplicable con revisión declarada como verificada. Esto significa cobertura del catálogo, **no cumplimiento técnico ni normativo**. Un paquete no verificado, un solape, declaraciones incompatibles o entradas inválidas producen `pending_specialist`. Si falta cobertura por versión, categoría, jurisdicción o ámbito, devuelve `unsupported`. Los conflictos y los ID de paquetes se ordenan de manera estable. La jurisdicción usa coincidencia literal; no se infiere una jerarquía territorial.

`fixtures/knowledge/registry-synthetic.json` usa solo jurisdicción y fuentes ficticias. Para reproducir:

```sh
uv sync --frozen --extra dev
uv run --no-sync pytest -q tests/at265
uv run --no-sync mypy src scripts tests
```

AT-267 podrá consumir metadatos de cobertura en el futuro; esta entrega no implementa motor de validación ni afirmaciones profesionales.
