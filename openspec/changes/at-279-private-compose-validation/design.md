# Diseño

El workflow de PR usa permisos `contents: read`, checkout de API y `git fetch` público del SHA de app. El ensamblador elimina ejemplos `.env*`, coteja los 321 hashes y reconstruye el tar determinista para exigir el SHA256 de la copia privada. Sólo después construye imágenes locales y levanta el Compose aislado. No sube artefactos ni imágenes.

El smoke accede únicamente a `127.0.0.1:8080`: descarga Angular y consulta `/v1/demo/evaluate` por el mismo origen. Compose define una sola publicación web en loopback y una red `backplane` interna. Un segundo arranque del mismo contenedor seed debe reportar `reused`; el hash de store visto desde API antes y después debe coincidir. Tras reiniciar API se repite el smoke. Una trampa de limpieza retira sólo los recursos de este nombre Compose en el runner efímero.

El diseño Coolify es documentación futura: requiere recurso aislado preconfigurado por el dueño, HTTPS confiable y un token de despliegue mínimo guardado en GitHub Environment protegido. Una propuesta manual desde `develop` validaría origen fijo y UUID fijo, llamaría sólo a `POST /deploy` sin parámetros de reemplazo, luego leería estado por GET sin escribir configuración. No forma parte del workflow actual.
