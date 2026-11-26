# AT-215 — prueba local de Relate

Este directorio contiene solo datos sintéticos. La [especificación](../../openspec/specs/technical-graph/spec.md) define identidades estables, contexto por proyecto, consultas Cypher y restauración local. SQL permanece como fuente de verdad según [ADR 0001](../../docs/adr/0001-arquitectura-inicial.md).

## Reproducir desde checkout limpio

Requisitos: Python 3.12, Docker Engine rootless o runner de confianza con Compose v2, arquitectura Linux x86-64 y acceso HTTPS confiable a PyPI para descargar la wheel. Desde la raíz:

```sh
bash ci/at-215-relate/run.sh
```

El script instala `relate-db==1.3.0` con hash obligatorio en un venv temporal; ejecuta Cypher contra un `.rl` temporal; descarga y verifica la wheel oficial; construye la imagen fijada a Python 3.12.14 y hace tres ejecuciones de contenedor (`seed`, `verify`, `restore`) sin red de ejecución. Limpia sus volúmenes, imagen, wheel y venv al salir. La construcción de la imagen instala desde la wheel verificada usando `--no-index`, preservando la verificación TLS de la descarga normal.

`seed` genera el grafo en `graph_data` y copia el archivo cerrado a `graph_backup`. `verify` lee desde un nuevo contenedor, comprueba igualdad del snapshot y que un segundo proceso escritor recibe bloqueo. `restore` copia el backup a `graph_restored` y vuelve a comparar el snapshot. No hay bind mount del host, credenciales ni conexión SQL.

La prueba no representa reinicio del host, backup fuera de host, Dokploy, carga de producción ni sincronización SQL. Véanse [evidencia](../../docs/evidence/at-215.md) y [ADR local](../../docs/adr/0015-relate-runtime-local.md).
