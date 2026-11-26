# AT-281: fases visibles del CI de API

## Why

El job único `verify` oculta qué etapa falla. La separación debe conservar el contexto protegido sin perder una condición de aprobación.

## What Changes

- Separar calidad Python, pytest, OpenAPI, OpenSpec/evidencia, secretos/metadatos y contenedor en jobs visibles.
- Mantener `verify` como agregador que requiere éxito de todos los jobs, incluso cuando uno falle, se omita o se cancele.
- Probar el agregador con estados sintéticos y conservar todos los comandos, triggers, permisos y versiones fijadas.

## Impact

Sólo el workflow principal de API, un script de agregación y pruebas/contrato OpenSpec. Los workflows especializados Relate y demo permanecen intactos. No hay despliegue ni reglas nuevas.
