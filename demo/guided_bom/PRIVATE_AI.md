# Corte privado ADK → OpenAI → Relate

**No altera `/v1/demo/guided-bom` ni el pin del VPS.** Este CLI acepta sólo
descripciones ficticias. El modelo `gpt-6-luna` extrae hechos preliminares;
un `BaseAgent` ADK llama después a `FunctionTool(graph_evidence)` sobre Relate
local real. El modelo no recibe herramientas, Cypher, URLs ni rutas. Python
verifica respaldo literal y calcula la BOM exclusivamente con el fixture
`guided-bom.v1`. El resultado lleva `PENDING_REVIEW`; no es una cotización ni
asesoría de instalación.
La extracción exige cantidades UTP y OD con números completos y unidades
explícitas; sólo 0.278 o 0.224 **pulgadas** permiten la evaluación. Los tramos
de 2 y 1.5 m deben estar declarados completos para obtener cantidades. Un
`12 m`/`11.5 m`, OD en `mm` o datos contradictorios fallan antes de abrir
Relate. Cantidad u OD ausentes devuelven `NEEDS_INPUT`, pregunta y cero
consultas; longitud ausente permite sólo selección preliminar, sin BOM.
Alternativas como `tres o seis UTP`, `OD 0.278 o 0.224 in`, `2 m o 1.5 m`,
rangos, cantidades aproximadas y conteos fraccionarios fallan antes del grafo.
En cámaras, `2.4` o `2,4` no se interpreta
como cuatro; `dos cámaras o seis cámaras` deja la cantidad pendiente o falla
cerrado. También se rechazan compuestos no soportados como `twenty two cameras`
o `twenty six UTP`. Un conteo independiente de UTP no cambia el de cámaras.

Con Python 3.12, desde la raíz del repo:

```sh
uv sync --frozen --extra demo --extra private-ai --extra dev
mkdir -p /tmp/estimate-guided-bom
uv run --frozen --extra demo python -m demo.guided_bom.cli seed --store /tmp/estimate-guided-bom/graph.rl
uv run --frozen --extra demo --extra private-ai python -m demo.guided_bom.private_ai \
  --store /tmp/estimate-guided-bom/graph.rl \
  --description 'Seis UTP de OD 0.278 in; tres cámaras Wi-Fi sin red. Faltan longitudes.'
```

La última línea exige `OPENAI_API_KEY` **en el proceso local**; nunca se pasa
como argumento ni se imprime. Ejecutar sólo en un entorno privado autorizado.
La API se invoca una vez por corrida, `store=False`, máximo 500 tokens de
salida, `reasoning.effort=none`, timeout de 15 s y cero reintentos. `--model`
permite una alternativa explícita para evaluación privada; no hay fallback.
La entrada completa (prompt fijo,
esquema y descripción de hasta 700 caracteres) está por debajo de unos 4000
tokens; no se inicia conversación ni bucle. `usage` se muestra sólo si OpenAI
lo devuelve. No se incluye la descripción en la salida ni en errores.

Este corte sólo se verificó aquí con extractores simulados y Relate real; no
se hizo una consulta OpenAI ni se inspeccionaron credenciales en esta iteración.
El comando de prueba sin proveedor es:

```sh
uv run --frozen --extra demo --extra dev --extra private-ai pytest -q tests/test_private_guided_ai.py tests/test_guided_bom.py
```

La integración oficial de ADK con OpenAI usa LiteLLM, pero la [documentación
actual de ADK](https://adk.dev/agents/models/litellm/) advierte sobre
versiones comprometidas de LiteLLM. Este corte conserva el agente ADK local y
usa directamente el SDK [OpenAI Responses con salida
estructurada](https://developers.openai.com/api/docs/guides/structured-outputs)
para una sola extracción controlada. No se incorpora LiteLLM.

## Cámaras y pool compartido

El modo privado independiente `demo.agent.private_camera` usa el mismo modelo
por defecto. Con el store sintético de `demo.agent.cli seed`, una descripción
explícita de dos o cuatro cámaras invoca una sola consulta Relate fija para
`CAM-POE`; el código calcula disponibilidad del pool común. Una cantidad
ausente o ambigua devuelve pregunta y **cero consultas al grafo**. Ejemplo
de comandos privados, únicamente donde ya esté autorizada la API key:

```sh
mkdir -p /tmp/estimate-camera-demo
uv run --frozen --extra demo python -m demo.agent.cli seed \
  --store /tmp/estimate-camera-demo/graph.rl
uv run --frozen --extra demo --extra private-ai python -m demo.agent.private_camera \
  --store /tmp/estimate-camera-demo/graph.rl \
  --description 'Solicito cuatro cámaras PoE ficticias.'
```

Los tests offline (`tests/test_private_model.py`, `tests/test_private_camera_ai.py`)
simulan la respuesta SDK, incluso el estado HTTP y usage; el SDK se consume
mediante `with_raw_response.create(...).parse()` y no se lee cuerpo crudo.
No se añade ruta HTTP paga ni se altera el endpoint guiado determinista.
