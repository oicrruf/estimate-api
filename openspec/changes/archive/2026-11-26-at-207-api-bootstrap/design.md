# Diseño: AT-207 bootstrap API

## Decisiones
FastAPI expone GET /health y genera OpenAPI 3.1. El exportador ordena claves para que el archivo JSON sea determinista. El endpoint documenta respuesta 200 con `{status: "ok"}`. No requiere configuración externa.

La estructura `domain`, `pricing`, `integrations`, `contracts`, `mcp`, `relate` y `sql` reserva límites de módulos; no promete comportamiento. Variables futuras se documentan como placeholders. Docker Compose inicia solo el servicio API, sin PostgreSQL ni Storage locales.

CI ejecuta las mismas tareas locales y verifica que el JSON exportado corresponda al código. El frontend debe comprobar drift usando el JSON obtenido del `develop` o SHA canónico de `estimate-api`, además de su referencia versionada. Comparar solo con una copia local no detecta cambios remotos.

Reglas de metadatos examinan título de PR y commit final con Conventional Commits y AT-207. Protección efectiva de ramas se propone al propietario; este cambio no cambia settings remotos.

## Riesgos y límites
La salud del proceso no acredita conectividad a Supabase, proveedor de modelo, ADK, MCP o Relate. Esas integraciones tienen issues posteriores. No se crean secretos ni cuentas.
