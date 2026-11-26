# AT-279 — prueba CI del paquete privado

Este workflow no despliega. Reconstruye los commits API `dac8c64c314bb362c6254825c65640ba732ca168` y app `d8a6d359bf909872ebfe48d52dfe5d8980c2c68b`, comprueba los 321 hashes y el SHA256 `18fda4a6fdd3a167d7c95b76d6b3cb3c83fc06c593c58d3cc91425f2b4484e67` de la copia privada. El paquete público de CI conserva sólo configuración, manifiesto y runtime sintético; las fuentes se obtienen de repos públicos en el runner y las imágenes quedan locales. No requiere secretos, no sube artefactos ni hace push a registros.

Comprobaciones: Compose publica sólo web en `127.0.0.1:8080`, API/seed permanecen sin puertos publicados, red `backplane` interna, store montado en sólo lectura por API, Angular `/demo` y cinco respuestas de Relate reales por mismo origen, seed reutilizado sin cambio de hash y reinicio de API. La limpieza limitada a `at279-final-preview` se ejecuta incluso al fallar.

El [README del paquete](package/README.md) ofrece el arranque local y el fallback Python/Node. La propuesta Coolify se documenta en [coolify-manual-proposal.md](coolify-manual-proposal.md); no hay workflow de despliegue en este PR.
