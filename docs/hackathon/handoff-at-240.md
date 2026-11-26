# AT-240: preparación local de descubrimiento

La base es `develop` en `f0b0e55fc0940734f48da036d1cabab00e1fe155` (AT-265, AT-238, AT-264 y AT-229 integrados). El contrato vive en `src/estimate_api/discovery`, sin modificar rutas existentes. El fixture `demo/fixtures/at-240-discovery.json` es enteramente ficticio. `evaluate_scope` es la entrada de backend local; su `scope-review.v1` tiene esquema JSON para la futura API/A2UI. Todavía no existe ruta HTTP ni pantalla.

## Recorrido reproducible

Desde la raíz del repositorio:

```sh
UV_CACHE_DIR=/tmp/at240-uv-cache uv sync --frozen --extra dev
UV_CACHE_DIR=/tmp/at240-uv-cache uv run --frozen --extra dev pytest -q
UV_CACHE_DIR=/tmp/at240-uv-cache uv run --frozen --extra dev ruff check .
UV_CACHE_DIR=/tmp/at240-uv-cache uv run --frozen --extra dev mypy src/estimate_api
OPENSPEC_TELEMETRY=0 ci/at-206-docs/node_modules/.bin/openspec validate 2026-11-26-at-240-scope-discovery --strict
UV_CACHE_DIR=/tmp/at240-uv-cache uv run --frozen --extra dev python demo/fixtures/verify_at240_scope.py
```

El harness prueba descubrimiento, cantidades pendientes, rutas de dependencia, rechazo, aprobación, revalidación, límites, contrato de transporte y un segundo rubro sintético. La prueba Relate carga el seed AT-229 en un archivo temporal aislado, ejecuta el adaptador con consultas fijas de solo lectura y verifica que los 60 nodos no cambien. Solo encuentra contexto de capacidad de producto; las reglas de instalación permanecen sin validar. El adaptador tipado AT-238 verifica que la ruta ficticia confirmada conserva EMT, unión y soportes, más conector pendiente; la ruta desconocida no genera cantidades. El registro AT-265 resuelve cobertura con fallo seguro: paquete sin verificar, sin cobertura o desalineado deja `pending_specialist`. El harness recorre entrada→propuesta→revisión→revalidación y conserva todos los insumos requeridos al aumentar cámaras. No prueba una entrada de usuario real porque el API actual solo expone `/health`.

## Integración pendiente

- [AT-264](https://linear.app/oicrruf/issue/AT-264) ya aporta el documento universal v1. Sigue pendiente mapear el levantamiento [AT-246](https://linear.app/oicrruf/issue/AT-246) a `ProjectIntake` sin duplicar su contrato ni inferir cantidades.
- AT-265 ya aporta cobertura catalogada; aún falta revisión técnica de cada paquete y de sus reglas de instalación. `cataloged` no equivale a cumplimiento profesional.
- [AT-238](https://linear.app/oicrruf/issue/AT-238/modelar-dependencias-de-ferreteria-accesorios-y-cantidades-derivadas) está integrado; su fixture sigue siendo sintética y exige validación profesional. [AT-239](https://linear.app/oicrruf/issue/AT-239/dimensionar-cableado-utp-y-componentes-de-enlaces-ethernet-para) debe aportar el patrón de enlaces validado, con cantidades dependientes de mediciones reales.
- [AT-227](https://linear.app/oicrruf/issue/AT-227/construir-vertical-slice-relate-para-hackathon-con-dataset-demostrable) debe conectar el grafo en la aplicación. El adaptador local lee evidencia AT-229, pero no prueba dependencias de instalación.
- [AT-237](https://linear.app/oicrruf/issue/AT-237/incorporar-chat-contextual-para-crear-y-modificar-proyectos-con) debe conectar ingreso conversacional y mutaciones de proyecto; [AT-248](https://linear.app/oicrruf/issue/AT-248/construir-revision-a2ui-del-alcance-propuesto-vs-solicitado) debe implementar revisión A2UI y persistencia auditable.
- [AT-234](https://linear.app/oicrruf/issue/AT-234/generar-y-comparar-escenarios-recomendado-economico-y-personalizado) debe comprobar que los tres escenarios conservan el alcance aprobado. Este paquete solo entrega `commercial_ready`; no crea escenarios ni precios.

## Puertas de aceptación

El **contrato de dominio** queda listo para revisión en este PR: expansión acotada, cobertura AT-265, cantidades AT-238, evidencia de capacidad AT-229, revisión y diff/revalidación deterministas. El paquete sigue siendo sintético; ningún resultado afirma cumplimiento técnico o normativo.

La **demostración de extremo a extremo** sigue pendiente: entrada real de chat/API, revisión A2UI persistida, paquete de enlaces AT-239 validado, relaciones Relate de instalación y revalidación de escenarios/cotización. AT-249/250 pueden consumir el contrato de dominio sin esperar que esas capas downstream estén completas; sus pruebas visuales no son precondición circular para este slice.

No se debe declarar AT-240 completo con este harness. `commercialReady` exige cobertura catalogada, validación técnica externa, aprobación y evidencia suficiente. La ruta de capacidad AT-229 nunca se presenta como prueba de un patrón físico.
