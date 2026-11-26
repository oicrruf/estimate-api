# Proposal

## Why

Estimate Agent necesita representar encargos de dominios distintos con la misma API antes de conectar la arquitectura de AT-206. Un contrato común explícito evita incorporar detalles de cámaras, inmuebles o eventos al núcleo.

## What Changes

- Introducir un contrato versionado para trece tipos de entidad, con identidad, origen, ámbito, revisión y estado de conocimiento compartidos.
- Validar documentos y referencias con JSON Schema y un validador tipado.
- Incluir paquetes de hechos por dominio y fixtures sintéticos para cámaras, pintura y montaje de eventos, además de casos inválidos.

## Capabilities

### New Capabilities

- `universal-project-model`: Representación y validación de proyectos de cualquier dominio mediante entidades genéricas y paquetes de hechos externos al núcleo.

### Modified Capabilities

Ninguna.

## Impact

Se añaden contratos, validador, fixtures y pruebas locales. No cambia una API desplegada ni se integra con servicios externos en esta preparación.
