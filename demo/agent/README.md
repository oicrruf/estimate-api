# AT-227 — demo local ADK + Relate

Datos, precios, proveedores e inventario son **ficticios**. Esta CLI usa Google ADK Python como runner de un agente determinista sin LLM. Las herramientas ejecutan únicamente consultas Cypher fijas sobre la fixture AT-229; no hay claves, llamadas a modelos ni conexión de producción.

## Reproducir

Requisitos: Python 3.12, `uv` 0.7.6 y acceso a PyPI para instalar las dependencias fijadas en `uv.lock` la primera vez. Desde la raíz de un checkout público limpio:

```sh
uv run --frozen --extra demo python -m demo.agent.cli demo --store /tmp/estimate-at227.demo.rl
```

El comando siembra el archivo local, cierra Relate y ejecuta cinco evaluaciones en procesos Python nuevos. Muestra SW-8 rechazado por ocho puertos totales frente a nueve requeridos, SW-16 seleccionable con ocho PoE, SW-16 rechazado al pedir doce PoE, cuatro cámaras con sólo dos unidades en el pool, control positivo de dos cámaras y UPS técnicamente compatible sin oferta. Cada afirmación técnica incluye rutas a evidencia ficticia. La salida es JSON; `selectedProductId: null` significa que no hay producto adquirible elegible.

El archivo `.rl` persiste después de la ejecución. `seed` es idempotente y rechaza un archivo existente poblado que no tenga el marcador del dataset ficticio; `evaluate` exige un archivo existente y lo abre en modo `read_only=True`. Use una ruta local dedicada a la demo. Las sesiones ADK sólo viven en memoria; no son el store de Relate.

Comandos individuales y ayuda:

```sh
uv run --frozen --extra demo python -m demo.agent.cli --help
uv run --frozen --extra demo python -m demo.agent.cli seed --store /tmp/estimate-at227.demo.rl
uv run --frozen --extra demo python -m demo.agent.cli evaluate --store /tmp/estimate-at227.demo.rl --scenario switch --poe-ports-min 12
```

Para los tests: `uv run --frozen --extra dev --extra demo pytest -q tests/at227`. ADK 1.20.0 es la versión fijada compatible con FastAPI 0.115.12 de este repositorio; versiones 2.x requieren actualizar la pila web en otro cambio. El endpoint de FastAPI y la UI no forman parte de esta demo. `docs/hackathon/planned-evidence-api.yaml` sigue siendo un ejemplo planificado, no el OpenAPI canónico.
