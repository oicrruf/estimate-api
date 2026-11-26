# AT-277 — Escaneo defensivo API (borrador)

## Alcance y política

El workflow [AT-277](../../.github/workflows/at-277-trivy.yml) analiza la fuente y el tar de una imagen construida con el [Dockerfile](../../Dockerfile) del servicio. Trivy 0.76.2 proviene de la imagen oficial `docker.io/aquasec/trivy:0.76.2@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb`. Se verificaron dos firmas Cosign del publicador oficial durante la preparación. Véanse la [guía de repositorios](https://trivy.dev/docs/latest/target/repository/) y la [guía de resultados](https://trivy.dev/docs/latest/configuration/reporting/).

Se solicitan vulnerabilidades, configuraciones y secretos con todas las severidades. Se bloquean HIGH, CRITICAL, UNKNOWN y cualquier secreto; MEDIUM se informa. Un error de build, DB, Trivy o parser falla cerrado. La configuración y el ignore vacíos residen fuera del checkout. No hay excepciones, cron, SARIF, avisos, `pull_request_target`, privilegios adicionales ni cambios de reglas. El único artifact nuevo contiene estado y recuentos por superficie, sin rutas, fragmentos, IDs ni JSON Trivy bruto, con retención de siete días.

El workflow tiene solo `contents: read`. Un PR todavía puede modificar el `scan.sh` que determina su propio resultado: este check **no es un gate confiable**. El P2 de seguridad sigue abierto. La verificación puntual desde código externo demuestra el límite de control, pero no es una regla de merge. Anclar invocación y política a una revisión protegida independiente y probar el contexto exacto requiere decisión del propietario antes de cambiar protecciones.

## Integración con la base actual

Esta preparación parte del API `develop` `f0f612eaacbc1f1ea59d463b3ee4ff5234dcfc1b` y app `develop` `d24ca275ce15758ebd687d26f2e87eb5c174798a`, que incluyen las fases visibles AT-281. AT-280 valida el contrato canónico sin ejecutar código API en el runner de app. Los cambios FastAPI/ADK y `uv.lock` de AT-277 se trasladaron sobre esta base; la paridad de OpenAPI y la suite deben pasar de nuevo. El workflow agregado `verify` de API y sus disparos permanecen exactamente como AT-281 los integró. El workflow Trivy es independiente; no se modifican protecciones.

La rama predeterminada de ambos repositorios es ahora `develop`; `main` sigue protegida para releases. Un eventual despacho manual de un verificador confiable se revisaría y promovería a `develop`, no a `main` como requisito de lanzamiento. No se desplegó tal workflow. El escaneo independiente del SHA anterior del PR encontró 0 HIGH/CRITICAL/UNKNOWN y 0 secretos en fuente, 1 MEDIUM y 2 LOW. La construcción local separada de la imagen API falló porque `apk` rechazó la cadena TLS del repositorio Alpine; la comprobación de certificados permaneció activa. El nuevo head reconciliado y la imagen final necesitan sus propias comprobaciones.

## Bases y compatibilidad

FastAPI pasa a 0.165.0 para resolver Starlette 1.10.0 y el extra de demo a ADK 2.15.1 por compatibilidad. Se retira `openapi_version` del constructor de FastAPI sin cambiar el contrato exportado. El Dockerfile de servicio usa dos etapas sobre `python:3.12.16-alpine3.24@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89`, actualiza paquetes y ejecuta el runtime como usuario no root. También se endurece el contenedor sintético de Relate. El escaneo de ese Dockerfile y del runtime final se debe repetir en el head reconciliado; no se infiere su resultado del análisis de fuente.
