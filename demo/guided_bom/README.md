# BOM guiada: preview local y exclusivamente sintético

Este corte no cambia la demo publicada. Usa **Relate 1.3.0 real** y ADK 1.20.0
(`InMemoryRunner` y `FunctionTool`) sin modelo ni credenciales. El proceso
servidor escucha solo `127.0.0.1:8002`; no se monta en la FastAPI productiva,
no hace fetch de URLs de entrada y solo abre un store local fijado al arrancar.
El escenario no contiene datos de clientes, ofertas reales ni precios.
**No es asesoría de instalación ni una cotización.**

Desde la raíz de `estimate-api` con Python 3.12 y `uv`:

```sh
uv sync --frozen --extra dev --extra demo
mkdir -p /tmp/estimate-guided-bom
uv run --frozen --extra demo python -m demo.guided_bom.cli seed --store /tmp/estimate-guided-bom/graph.rl
uv run --frozen --extra demo python -m demo.guided_bom.http --store /tmp/estimate-guided-bom/graph.rl --port 8002
```

En otra terminal:

```sh
curl -sS 'http://127.0.0.1:8002/v1/demo/guided-bom?cable_count=3&cable_variant=thick'
curl -sS 'http://127.0.0.1:8002/v1/demo/guided-bom?cable_count=6&cable_variant=thick'
curl -sS 'http://127.0.0.1:8002/v1/demo/guided-bom?cable_count=6&cable_variant=slim'
curl -sS 'http://127.0.0.1:8002/v1/demo/guided-bom?cable_count=6&cable_variant=unknown'
curl -sS 'http://127.0.0.1:8002/v1/demo/guided-bom?cable_count=6&cable_variant=thick&route_length=unknown'
```

La misma evaluación se ejecuta por CLI con `evaluate --store ...
--cable-count 6 --cable-variant thick`. Los flags anteriores
`--utp-count` y `--cable-od-mm 5|6` siguen disponibles para el prototipo
local previo. La app nueva debe usar únicamente `cable_count=3|6`,
`cable_variant=thick|slim|unknown`, y opcionalmente
`route_length=known|unknown` (por defecto `known`). Faltantes, duplicados,
valores fuera de enum y parámetros desconocidos devuelven HTTP 422.
Un proxy de desarrollo mismo origen puede dirigir `/v1/demo/guided-bom`
a `http://127.0.0.1:8002`; no hay CORS abierto.

`guided-bom.v1.example.json` es el wire completo de `6/thick`, generado desde
el GET/CLI real: `assumptions`, `requirements`, `bom`, `candidates`, `evidence`
y `status` más `wireVersion` y `scenarioId` fijos. `bom` es borrador, no compra.
`candidates.emt[].fill` contiene factores de área, porcentaje mostrado a un
decimal y estado. La comparación interna con `Decimal` ocurre **antes** de
redondear. Con `cable_variant=unknown`, el OD y la compatibilidad quedan
pendientes, `selectedDemoEmtId` es `null` y `bom` está vacío. Con
`route_length=unknown`, el diámetro preliminar sigue visible, pero cantidades
de EMT/accesorios y precio quedan pendientes y `bom` está vacío.

## Dimensiones de la fixture y límite de uso

Las fichas primarias publican OD nominal de cable: [Belden 10GXS32,
0.278 in](https://www.belden.com/products/cable/ethernet-cable/category-6a-cable/10gxs32)
y [Belden 2412, 0.224 in](https://www.belden.com/products/cable/ethernet-cable/category-6-cable/2412).
La [tabla de EMT de Steel Tube Institute](https://steeltubeinstitute.org/steel-conduit/electrical-metallic-tubing/)
publica OD y espesor nominales. La fixture deriva ID como `OD − 2 × espesor`:
0.824, 1.049 y 1.380 in para 3/4, 1 y 1¼. No se consultan esas URLs durante
la ejecución ni se afirma que el sitio use esos productos. El umbral de área
del 40 % es **solo una elección ilustrativa de esta fixture**, no una norma
universal ni una validación técnica del sitio.

| Requisito de prueba | 3/4 | 1 | 1¼ | Preliminar |
| --- | ---: | ---: | ---: | --- |
| 3 × 0.278 in | 34.1 % | 21.1 % | 12.2 % | 3/4 |
| 6 × 0.278 in | 68.3 % | 42.1 % | 24.3 % | 1¼ |
| 6 × 0.224 in | 44.3 % | 27.4 % | 15.8 % | 1 |

El grafo real de AT-238 aporta `REQUIRES`, `FITS_DIAMETER` y
`SUPPORTED_BY`; 1¼ y sus accesorios son tipos ficticios añadidos solo al
store de esta demo. AT-238 deriva cantidades únicamente cuando el tramo tiene
longitud confirmada; AT-239 muestra que tres cámaras Wi-Fi no requieren
automáticamente enlaces Ethernet directos. AT-246 conserva preguntas de
alcance y AT-247 propone comprobaciones de red inalámbrica. Los UTP del tramo
son una **opción de infraestructura independiente de las cámaras**. Starlink
figura como alternativa conceptual sin confirmar cobertura, energía, servicio,
compatibilidad o precio. Switch y gabinete permanecen vacíos sin justificación.

Pruebas: `uv run --frozen --extra dev --extra demo pytest -q
tests/test_guided_bom.py`. El test siembra el archivo en un proceso, abre
otro proceso HTTP y compara dos respuestas GET completas con la CLI, además de
rechazar parámetros extra, duplicados o inválidos.

## Extracción privada opcional AT-211

La [guía del CLI privado](PRIVATE_AI.md) documenta el comando con `gpt-6-luna`,
los límites de entrada, el store sintético y una prueba offline sin proveedor.
Este modo no se monta en el servidor HTTP de la demo. Requiere autorización y
configuración local de OpenAI para ejecutar el comando del modelo; la preview
determinista anterior no necesita cuenta ni credenciales.
