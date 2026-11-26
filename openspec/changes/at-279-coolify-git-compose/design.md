# Diseño

La aplicación de Coolify usa Build strategy Docker Compose desde el repositorio público `oicrruf/estimate-api`, con Base Directory `/ci/at-279/package/runtime` y Docker Compose Location `/coolify-compose.yaml` (ruta relativa a ese Base Directory). El servicio Empty no dispone de contexto Git para `COPY container_api.py`, `container_seed.py` o `nginx.conf`; una adaptación inline alteraría el paquete probado y multiplicaría el código pegado al panel.

Dos Dockerfiles en esa carpeta obtienen los commits públicos `dac8c64c314bb362c6254825c65640ba732ca168` y `d8a6d359bf909872ebfe48d52dfe5d8980c2c68b`. Cada build compara `FETCH_HEAD` con el SHA literal antes de copiar fuentes. `uv sync --frozen` y `npm ci` consumen locks de esos commits. Las imágenes base usan digests. Compose construye localmente, sin registry de aplicación.

El proxy de Coolify apunta sólo al servicio `web` en el puerto interno 8080. Compose no publica puertos host; `api` y `seed` sólo usan `backplane` interna. La semilla escribe el volumen gestionado y la API lo monta en lectura. CI verifica la definición original; Coolify puede transformarla para añadir proxy/red/labels, por lo que el dueño debe revisar el Compose generado y las rutas reales antes de abrir el dominio.
