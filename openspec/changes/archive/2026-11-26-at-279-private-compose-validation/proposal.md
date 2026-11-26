# AT-279 — Validación aislada del paquete privado

## Why

El paquete sintético del 1 de diciembre combina API y app integradas, pero el runner local quedó sin espacio durante el build Docker. Se requiere una prueba real en CI estándar que compruebe exactamente los bytes guardados en Library, sin credenciales ni despliegue.

## What Changes

- Reconstruir desde los commits públicos fijos las fuentes del paquete privado, comprobar su manifiesto y SHA256, y ejecutar Compose en runner GitHub efímero.
- Verificar red interna, ausencia de puertos de API/seed, Angular por loopback y API de mismo origen con el grafo Relate real.
- Verificar seed único, archivo de volumen montado en lectura en API, reapertura y persistencia tras reinicio.
- Documentar una propuesta separada para un futuro disparo manual seguro en Coolify; no instalarlo.

## Out of Scope

No se modifican API, app o datos productivos; no se usa host Coolify, DNS, secretos, tokens, registro, GitHub Environment ni despliegue. El paquete sigue siendo privado, sintético y local.
