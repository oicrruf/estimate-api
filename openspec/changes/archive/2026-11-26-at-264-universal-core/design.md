# Design

## Context

AT-206 (`a70ffefc`) y el bootstrap Python/FastAPI de AT-207 (`6ecc9a9`) están integrados en `develop`. Véanse `proposal.md` y `specs/universal-project-model/spec.md` para la motivación y el comportamiento requerido. AT-246 define el contrato específico de levantamiento técnico.

## Goals / Non-Goals

**Goals:**

- Crear un contrato transportable que pueda integrarse después sin depender de un framework HTTP.
- Mantener verificables la identidad, la procedencia y las relaciones entre entidades.

**Non-Goals:**

- Persistencia, autorización de usuarios, ejecución de reglas y cálculo de presupuestos.
- Consulta de proveedores o servicios reales.

## Decisions

1. **Un sobre único y una lista cerrada de tipos.** Cada entidad lleva `kind`, `id`, `origin`, `scope`, `revision`, `knowledgeState`, `label` y relaciones opcionales. Los hechos del dominio viven en paquetes separados. La alternativa de variantes por dominio acoplaría el núcleo a los primeros tres casos.
2. **JSON Schema 2020-12 como contrato de intercambio.** El esquema se distribuye dentro del paquete Python, fija los campos de transporte y prohíbe campos adicionales del núcleo. `TypedDict` y alias `Literal` reflejan el contrato en Python 3.12. La alternativa de variantes por dominio obligaría a cambiar el núcleo en cada rubro.
3. **Validador de dos etapas.** `jsonschema` 4.26.0 comprueba el esquema; una pasada Python verifica unicidad y referencias internas, que JSON Schema no expresa con claridad. La alternativa de incluir referencias remotas ampliaría el alcance y exigiría acceso a servicios.
4. **Paquetes versionados por nombre.** Cada paquete declara `namespace`, `version`, `subjectId` y `facts` (objeto JSON); así los dominios pueden publicar esquemas propios en otra entrega. El validador común sólo verifica el sobre y la existencia del sujeto.

## Risks / Trade-offs

- [Los hechos de paquetes no tienen semántica universal] → Documentar la frontera y limitar la validación común al sobre; cada integración de dominio validará su propio esquema.
- [Una revisión numérica local no coordina cambios distribuidos] → Definirla como revisión del documento fuente, sin prometer resolución de conflictos.

## Migration Plan

No hay datos ni API existente que migrar. Se incorporan `jsonschema` y sus tipos a `pyproject.toml`/`uv.lock` del backend ya integrado; el contrato queda dentro del wheel. AT-246 puede mapear sus datos de levantamiento a entidades y paquetes, pero conserva sus propias validaciones y archivos.
