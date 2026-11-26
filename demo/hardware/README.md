# Ferretería sintética AT-238

La fixture representa una ruta ficticia de dos secciones medidas (2,0 m y 1,5 m) con EMT de 1 pulgada, una unión, dos entradas a caja y tres puntos de soporte **confirmados como datos de entrada**. Cada sección requiere una pieza comercial de 3 m. El conector no está seleccionado y aparece como faltante; LB y tomacorriente interior no se agregan sin condición confirmada. Los tipos genéricos de 3/4 de pulgada permanecen en el catálogo para el cambio de diámetro.

El evaluador está en `src/estimate_api/hardware/evaluate.py`; no calcula costos ni genera diseños eléctricos. Las cantidades, alternativas y bloqueos llevan IDs de regla y evidencia sintética. `professionalValidationRequired` permanece verdadero para llenado/capacidad, ambiente, fijación, tierra, protección y normativa local.

Con Python 3.12 y las dependencias de desarrollo del proyecto y `relate-db==1.3.0`:

```sh
python demo/hardware/build_seed.py
PYTHONPATH=src pytest -q tests/test_hardware.py
```

`seed.cypher` se puede cargar en un archivo Relate temporal; la prueba ejecuta consultas Cypher reales e inserta dos veces para verificar idempotencia. El paquete es un arnés sintético aislado: aún no hay endpoint, selección de escenarios, catálogo SQL ni enlace al flujo de propuesta.

## Contrato de integración previsto

- AT-264: un adaptador futuro deberá recibir un `ProjectDocument` validado y leer hechos de instalación desde un paquete de dominio versionado; este paquete no modifica el esquema universal. Los IDs de ruta y evidencia se trasladarán como referencias de origen, sin convertir `assumed` o `unknown` en mediciones confirmadas.
- AT-246: el levantamiento deberá aportar longitudes por sección y conteos observados, junto con su procedencia y estado de confirmación. Si faltan, `evaluate_route` devuelve `PENDING`.
- AT-240/AT-265: una propuesta futura podrá consumir líneas, faltantes y alternativas como candidatos para revisión. La selección de escenarios y el costo pertenecen a sus servicios; las alternativas del catálogo no son una compra ni una BOM seleccionada automáticamente.

`relate-db` se agrega sólo al extra `dev` para que la suite ejecute la consulta real en CI. El evaluador de producción no importa Relate.
