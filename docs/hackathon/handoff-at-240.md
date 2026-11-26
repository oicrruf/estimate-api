# AT-240: preparación local de descubrimiento

## Reconciliación con la base integrada

La comprobación descartable de `develop` `3cd1e27cee6f096777848dbcd2b79844032f8f78`
y el head AT-240 anterior produjo el árbol `46fcbe570316a21c409a90f9ddfcc220dc97b05f`
sin conflictos. La rama incorpora ahora esa base; el único cambio posterior es
esta nota de evidencia.
Con los extras `dev` y `demo` fijados por CI tras integrar AT-232, la suite
completa registra 206 pruebas aprobadas; también pasan Ruff, mypy, OpenAPI,
el escaneo de secretos y OpenSpec estricto. Esta comprobación cubre los puntos
de entrada locales `evaluate_scope` y `evaluate_pattern_scope`; no constituye
una prueba del chat/API ni de la aprobación A2UI persistida.

## Revisión de cantidades y procedencia (head de noviembre de 2026)

`tests/test_discovery_review_regressions.py` recorre cuatro correcciones del motor:
al modificar un padre se invalidan transitivamente las cantidades y aprobaciones
descendientes; confirmar una cantidad compartida elimina únicamente su bloqueo
específico; el diff registra cambios de unidad aun con el mismo valor; y una regla
requerida prevalece cuando otra regla opcional apunta al mismo insumo. Redescubrir
vuelve a pedir confirmación de recursos compartidos y no restaura aprobaciones.
Los fixtures de cámaras, pintura y evento corresponden a los blobs de `develop`;
se verificaron también en el árbol de merge de PR #11. La suite del repositorio
y las comprobaciones de formato, tipos, OpenAPI, secretos y OpenSpec se ejecutan
sobre ese mismo árbol. Siguen pendientes el endpoint de revisión y la aprobación
A2UI persistida, por lo que estas regresiones son de dominio y del servicio local.

La revisión posterior también cubre ciclos entre ramas ya descubiertas, bindings
de necesidades distintas que reutilizan un patrón y cantidades no finitas.
`discover` rechaza un arco que cerraría un ciclo en el grafo completo. El ID de
regla conserva su formato anterior para un patrón usado una vez; cuando se
reutiliza, incorpora de forma inequívoca la clave de la necesidad para evitar
colisiones. El intake, las cantidades derivadas y las modificaciones rechazan
NaN, infinito y productos desbordados. `tests/test_discovery_integrated.py`
comprueba el servicio con dos bindings sintéticos del mismo patrón y mantiene
la cantidad compartida pendiente de confirmación.

La ruta AT-239 valida que cada longitud Decimal siga siendo positiva y finita
al representarla como número JSON antes de adjuntarla a una línea. Rechaza
desbordamiento a infinito y subdesbordamiento a cero tanto desde
`evaluate_ethernet_scope` como al recibir un `TopologyScope` directamente.
Las líneas compartidas conservan los arreglos planos del contrato y añaden
`ruleProvenance`, que agrupa por regla y necesidad sus IDs de evidencia,
reglas, fuentes y rutas candidatas. La evidencia faltante de cualquiera de
esas rutas sigue visible y bloquea `commercialReady` después de confirmar
la cantidad. Hardware solo transporta conteos enteros y el adaptador de
restricciones no añade cantidades a las líneas; Ethernet es la conversión
Decimal→float anexa identificada en este paquete.

La base integrada probada es `develop` en `c130fda08dd7ae8b69ea45474925bdc0acc1e67f` (AT-247/239/267/246 más AT-265/238/264/229). El contrato vive en `src/estimate_api/discovery`, sin modificar rutas existentes. El fixture `demo/fixtures/at-240-discovery.json` es enteramente ficticio. `evaluate_scope` y `evaluate_pattern_scope` son entradas de backend locales; `scope-review.v1` es el contrato JSON para la futura API/A2UI/escenarios. Todavía no existe ruta HTTP ni pantalla.

## Recorrido reproducible

Desde la raíz del repositorio:

```sh
UV_CACHE_DIR=/tmp/at240-uv-cache uv sync --frozen --extra dev
UV_CACHE_DIR=/tmp/at240-uv-cache uv run --frozen --extra dev pytest -q
UV_CACHE_DIR=/tmp/at240-uv-cache uv run --frozen --extra dev ruff check .
UV_CACHE_DIR=/tmp/at240-uv-cache uv run --frozen --extra dev mypy src/estimate_api
OPENSPEC_TELEMETRY=0 ci/at-206-docs/node_modules/.bin/openspec validate 2026-11-26-at-240-scope-discovery --strict
UV_CACHE_DIR=/tmp/at240-uv-cache uv run --frozen --extra dev python demo/fixtures/verify_at240_scope.py
UV_CACHE_DIR=/tmp/at240-uv-cache uv run --frozen --extra dev pytest -q tests/test_discovery_integrated.py
```

El harness prueba descubrimiento, cantidades pendientes, rutas de dependencia, rechazo, aprobación, revalidación, límites, contrato de transporte y un segundo rubro sintético. La prueba Relate carga el seed AT-229 en un archivo temporal aislado, ejecuta el adaptador con consultas fijas de solo lectura y verifica que los 60 nodos no cambien. Solo encuentra contexto de capacidad de producto; las reglas de instalación permanecen sin validar. El adaptador tipado AT-238 verifica que la ruta ficticia confirmada conserva EMT, unión y soportes, más conector pendiente; la ruta desconocida no genera cantidades. El registro AT-265 resuelve cobertura con fallo seguro: paquete sin verificar, sin cobertura o desalineado deja `pending_specialist`. El harness recorre entrada→propuesta→revisión→revalidación y conserva todos los insumos requeridos al aumentar cámaras. No prueba una entrada de usuario real porque el API actual solo expone `/health`.

`tests/test_discovery_integrated.py` usa los patrones reales AT-247 y la topología AT-239 integrados. Comprueba candidato UTP y terminaciones con reglas, fuentes y rutas; rechazo de UTP; cambio mesh cableado→inalámbrico solo con hecho confirmado; enlaces exigidos con medidas conocidas o pendientes; cable parcial sin total de compra; rubro sin cobertura sin BOM inventada. Un store Relate temporal carga el seed sintético AT-247/239 y verifica lecturas patrón→regla→fuente y endpoint→enlace→evidencia sin cambiar sus nodos.

El adaptador AT-267 evalúa documentos de proyecto sintéticos con el evaluador integrado y conserva cada check, estado, motivo, revisión y cadena de evidencia en `constraints`. El llamador declara IDs de checks aplicables: documento ausente, check omitido, evidencia obsoleta o contradicción bloquean la revisión y `commercialReady`. Puertos totales, puertos PoE y potencia PoE se prueban por separado. Revalidar sin documento exige de nuevo la evidencia; no hereda un pase anterior.

`src/estimate_api/discovery/data/reviewed-packages.v1.json` contiene únicamente tres paquetes de reglas ficticias y digests de los patrones AT-247 revisados en el repositorio. El formato de reglas y declaraciones corresponde al contrato del borrador AT-266 en PR #12, head `2c92bc1`, sin importar su suite ni exigir fusionar su PR. `evaluate_scope` y `revalidate` resuelven el mismo paquete exacto por ID, versión, jurisdicción, proyecto, reglas y sourceRefs; cuando hay contexto de registro, verifican además categoría, ámbito, revisión de fuente y cada declaración topic/choice/sourceRef. Un paquete o regla no declarados dejan solo las necesidades solicitadas y `pending_specialist`. `evaluate_pattern_scope` reconstruye la expansión desde sus bindings y comprueba el digest del cuerpo versionado AT-247 antes de admitir candidatos. Los sourceRefs de dependencias hijas permanecen distintos de la fuente del patrón. `tests/test_discovery_reviewed.py` verifica líneas y cantidades legítimas de cámaras, pintura y evento a través del servicio y bloquea reglas ajenas en ambos puntos de entrada. Ninguna de estas fixtures es autoridad técnica; la revisión especialista por proyecto sigue pendiente.

## Integración pendiente

- [AT-264](https://linear.app/oicrruf/issue/AT-264) y [AT-246](https://linear.app/oicrruf/issue/AT-246) aportan documento y borrador de levantamiento. Falta su adaptador a `ProjectIntake`: el borrador no enumera necesidades normalizadas y no se deben inferir cantidades.
- AT-265 ya aporta cobertura catalogada; los paquetes AT-266 sintéticos siguen sin verificar y falta revisión técnica de cada paquete y de sus reglas de instalación. `cataloged` no equivale a cumplimiento profesional.
- [AT-238](https://linear.app/oicrruf/issue/AT-238/modelar-dependencias-de-ferreteria-accesorios-y-cantidades-derivadas), [AT-239](https://linear.app/oicrruf/issue/AT-239/dimensionar-cableado-utp-y-componentes-de-enlaces-ethernet-para) y AT-247 están integrados y consumidos como fuentes sintéticas. Aún necesitan validación técnica profesional para cada proyecto y medidas de campo.
- [AT-227](https://linear.app/oicrruf/issue/AT-227/construir-vertical-slice-relate-para-hackathon-con-dataset-demostrable) debe conectar el grafo en la aplicación. El adaptador local lee evidencia AT-229, pero no prueba dependencias de instalación.
- [AT-237](https://linear.app/oicrruf/issue/AT-237/incorporar-chat-contextual-para-crear-y-modificar-proyectos-con) debe conectar ingreso conversacional y mutaciones de proyecto; [AT-248](https://linear.app/oicrruf/issue/AT-248/construir-revision-a2ui-del-alcance-propuesto-vs-solicitado) debe implementar revisión A2UI y persistencia auditable.
- [AT-234](https://linear.app/oicrruf/issue/AT-234/generar-y-comparar-escenarios-recomendado-economico-y-personalizado) debe comprobar que los tres escenarios conservan el alcance aprobado. Este paquete solo entrega `commercial_ready`; no crea escenarios ni precios.

## Puertas de aceptación

El **contrato de dominio** queda listo para revisión en este PR: expansión acotada, cobertura AT-265, cantidades AT-238, candidatos AT-247, topología AT-239, evidencia de capacidad AT-229 y rutas Relate sintéticas de solo lectura, revisión y diff/revalidación deterministas. El paquete sigue siendo sintético; ningún resultado afirma cumplimiento técnico o normativo.

La **demostración de extremo a extremo** sigue pendiente: entrada real de chat/API, revisión A2UI persistida, validación técnica profesional de los patrones y del diseño, y revalidación de escenarios/cotización. AT-249/250 pueden consumir el contrato de dominio sin esperar que esas capas downstream estén completas; sus pruebas visuales no son precondición circular para este slice.

No se debe declarar AT-240 completo con este harness. `commercialReady` exige cobertura catalogada, validación técnica externa, aprobación y evidencia suficiente. La ruta de capacidad AT-229 nunca se presenta como prueba de un patrón físico.
