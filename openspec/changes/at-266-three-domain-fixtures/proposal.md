# Proposal

## Context

AT-264 aporta el documento universal, AT-265 el registro de cobertura y AT-240 el servicio de descubrimiento. Los casos reproducibles verifican la conexión entre ellos sin atribuir al registro capacidad de descubrimiento.

## Change

Añadir tres casos ficticios de cámaras, pintura y evento audiovisual con cantidades declaradas, referencias exactas a paquetes versionados y un contrato tipado de entrada para pruebas. Un recorrido genérico de dependencias en el arnés de tests demuestra partidas omitidas y cambios de cantidad; las pruebas comparan estos resultados con el servicio real AT-240.

## Scope

Incluye fixtures, pruebas de aislamiento, comparación con `evaluate_scope` y `revalidate`, y evidencia local. Excluye reglas profesionales, normas, precios, aprobación técnica, API o persistencia.
