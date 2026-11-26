# Diseño

Cada job ejecuta un grupo de comandos ya presente en el `verify` original. Los jobs Python instalan las dependencias fijadas con `uv sync --frozen --extra dev`. OpenSpec instala el paquete Node fijado y conserva la comprobación de evidencia AT-206. El contenedor ejecuta el mismo build y health smoke. El job de seguridad siempre analiza secretos; únicamente el paso de metadatos PR usa la condición de evento.

El job `verify` tiene `needs` explícitos sobre las seis fases e `if: ${{ always() }}`. Exporta los resultados `needs.<job>.result` al mismo script que prueba la suite sintética. El script sólo devuelve cero cuando los seis valores son `success`; fallo, omisión, cancelación o variable ausente devuelven estado distinto de cero. Una cancelación del workflow tampoco puede producir un `verify` verde.

Se preserva el contexto protegido `verify` como nombre de job y check, sin cambiar triggers, ramas, permisos `contents: read`, versiones de actions ni políticas de metadata. AT-277 conserva Trivy y el diseño de triggers de seguridad especializado fuera de este cambio.
