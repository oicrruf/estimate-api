# Diseño

## Datos y proyección

`demo/fixtures/evidence-graph.json` es la fuente sintética. `build_seed.py` genera un seed Cypher determinista con `MERGE` por ID y constraints de unicidad. El grafo contiene `REQUIREMENT`, `PRODUCT`, `CAPABILITY`, `OFFER`, `EVIDENCE` y `ACCESSORY`, con relaciones `REQUIRES`, `SUPPORTS`, `REQUIRES_ACCESSORY`, `SUPPORTED_BY`, `INCOMPATIBLE_WITH` y `SELLS`.

El catálogo y las ofertas reales permanecen en SQL según el ADR. En esta demo el grafo copia sólo los atributos necesarios para mostrar rutas. La capacidad de `POOL-CAM-POE` es dos aunque dos ofertas publiquen dos unidades cada una. La disponibilidad se evalúa separada de la compatibilidad técnica.

## Evaluación

Ocho puertos PoE más un uplink distinto exigen al menos nueve puertos totales. La cámara de 12 V exige un adaptador sin oferta; una alternativa PoE de 4 MP es viable técnicamente pero tampoco tiene oferta. La ausencia de `drawW` produce `UNKNOWN`. La prueba de UPS confirma la forma de la ruta fuera de cámaras sin ampliar el alcance.

## Reproducibilidad

`verify_relate.py` crea una base temporal local, carga el seed, cierra y reabre, lo carga otra vez y verifica conteos y las nueve consultas contra `expected.json`. No requiere servicio, credenciales ni proveedor. El archivo OpenAPI de `docs/hackathon` es un ejemplo **planificado de demo**, no la API canónica en ejecución; AT-227 implementará el contrato final.

El workflow exclusivo `.github/workflows/at-229-relate-demo.yml` repite el verificador desde un checkout limpio, instala el wheel oficial de `relate-db==1.3.0` con SHA-256 fijado y falla si la regeneración del seed modifica el archivo versionado. Sólo necesita `contents: read` y no recibe secretos.
