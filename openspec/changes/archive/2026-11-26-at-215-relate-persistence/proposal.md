# AT-215 — Persistencia local de Relate

## Contexto

AT-206 elige SQL como fuente de verdad y exige que Relate sea reconstruible. Este cambio entrega una prueba sintética ejecutable del runtime Python y del contenedor local. No conecta servicios ni modifica datos reales.

## Objetivo

Demostrar Cypher sobre archivo `.rl`, cierre/apertura desde otro proceso y otro contenedor, exclusión de un segundo escritor, aislamiento de candidatos por proyecto, historial de evidencia y restauración de una copia cerrada.

## Fuera de alcance

La sincronización SQL, permisos de API, despliegue Dokploy, backup externo, recuperación de host y carga real requieren contratos y entorno aprobados. AT-207 trabaja en el bootstrap; este cambio usa rutas propias.
