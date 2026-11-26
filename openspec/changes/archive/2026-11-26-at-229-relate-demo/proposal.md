# AT-229: demo reproducible de evidencia técnica

## Why

La demo necesita explicar con rutas de evidencia por qué una oferta satisface o falla una necesidad. El conjunto debe ser público, ficticio y ejecutable en Relate sin proveedor ni credenciales externas.

## What Changes

- Tres necesidades de red/cámaras y un control acotado de UPS.
- Diez productos, cuatro ofertas, evidencia técnica y un accesorio obligatorio, todos ficticios.
- Seed Cypher idempotente, nueve consultas y verificador de persistencia en `relate-db==1.3.0`.
- Storyboard y ejemplo **planificado** de respuesta API con rutas tipadas; el endpoint real corresponde a AT-227.

## Out of Scope

No se implementan endpoint, inventario de producción, sincronización SQL, motor de compras general ni cambios de AT-207/AT-215. No se despliega ni se usan datos privados.
