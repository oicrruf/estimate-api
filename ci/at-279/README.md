# AT-279 — prueba CI del paquete privado

Este workflow no despliega. Reconstruye los commits API `dac8c64c314bb362c6254825c65640ba732ca168` y app `d8a6d359bf909872ebfe48d52dfe5d8980c2c68b`, comprueba los 321 hashes y el SHA256 de `ARCHIVE-SHA256.txt` contra la copia privada. El paquete público de CI conserva sólo configuración, manifiesto y runtime sintético; las fuentes se obtienen de repos públicos en el runner y las imágenes quedan locales. No requiere secretos, no sube artefactos ni hace push a registros.

Comprobaciones: Compose publica sólo web en `127.0.0.1:8080`, API/seed permanecen sin puertos publicados, red `backplane` interna, store montado en sólo lectura por API, Angular `/demo` y cinco respuestas de Relate reales por mismo origen, seed reutilizado sin cambio de hash y reinicio de API. ChromeDriver del runner pulsa los cinco escenarios en la pantalla y comprueba que el navegador llama a la API por el mismo origen. La limpieza limitada a `at279-final-preview` se ejecuta incluso al fallar.

El [README del paquete](package/README.md) ofrece el arranque local y el fallback Python/Node. La propuesta Coolify se documenta en [coolify-manual-proposal.md](coolify-manual-proposal.md), con una plantilla YAML [no instalada](coolify-deploy-proposal.yml) y un cliente que falla cerrado hasta que el dueño apruebe HTTPS, el recurso y la política de rama del Environment `coolify`. No hay workflow de despliegue en este PR.

El [candidato Coolify desde Git](coolify-git-setup.md) usa [Compose sin puertos host](coolify-compose.yaml), construye las imágenes a partir de los dos commits públicos fijos y expone sólo `web:8080` al proxy. La UI real de Coolify y su Compose transformado siguen pendientes de inspección del dueño.
