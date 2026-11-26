# AT-259: plantillas tipadas de servicios

## Why

El alcance de un servicio necesita representar trabajos, materiales, activos existentes y pruebas sin convertir incertidumbre en una compra o un precio final. La contingencia interna debe aplicarse una sola vez mediante el motor de precios integrado.

## What Changes

- Contrato inmutable para complejidad, trabajo incluido/excluido, cantidades de materiales, propiedad de activos, trabajos existentes y verificaciones.
- Evaluación pura que utiliza el borrador de alcance AT-246 y la cotización Decimal AT-224.
- Proyección para el cliente sin componentes internos; estado pendiente cuando falta evidencia, aplicabilidad de contingencia, impuesto o precio de material.
- Pruebas sintéticas de resultados positivos y fallos cerrados.

## Impact

Nuevo módulo `estimate_api.services`, documentación y pruebas. Sin persistencia, compras, proveedores, tarifas legales, red, interfaz ni cambios de permisos.
