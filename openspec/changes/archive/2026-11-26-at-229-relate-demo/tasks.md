# Tasks

## 1. Contrato y fixtures

- [x] 1.1 Especificar casos de compatibilidad, disponibilidad, accesorio, dato insuficiente, cambio de requisito y rutas de evidencia.
- [x] 1.2 Incorporar datos sintéticos, seed idempotente y nueve consultas Cypher con resultados esperados.
- [x] 1.3 Documentar storyboard, tradeoffs SQL + grafo y ejemplo planificado de API.

## 2. Verificación

- [x] 2.1 Ejecutar seed dos veces en `relate-db==1.3.0`, con dos cierres/reaperturas y conteos estables.
- [x] 2.2 Comparar nueve consultas y rutas con `expected.json` mediante verificador local sin credenciales.
- [x] 2.3 Validar OpenSpec, sincronizar spec vigente y archivar este cambio.

## Gate de integración posterior

AT-227 debe implementar y probar la API real; este cambio sólo entrega el ejemplo de demo. El PR de AT-229 necesita CI y revisión antes de merge a `develop`.
