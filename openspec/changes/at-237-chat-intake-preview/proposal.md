# Propuesta: vista previa de captura desde chat (AT-237)

## Why

El chat necesita una entrada de servicio verificable antes de conectar descubrimiento BOM, A2UI y persistencia. El contrato AT-246 ya distingue hechos, inferencias y preguntas.

## What Changes

- Exponer una operación HTTP de vista previa estructurada para un proyecto nuevo.
- Reutilizar el constructor AT-246 mediante una dependencia inyectable.
- Devolver el borrador, preguntas y una frontera explícita de revisión sin escritura.

## Impact

La operación sirve a clientes HTTP y futuras acciones A2UI. No interpreta texto libre con LLM, no crea historial ni proyecto, no calcula BOM y no confirma alcance. Es una fase activa de AT-237; AT-240, AT-248, AT-208/209 y AT-254 completarán las demás fases.
