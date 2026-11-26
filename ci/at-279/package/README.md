# Estimate Agent — candidato privado para el 1 de diciembre

Este paquete portátil y **sólo de prueba local** combina fuentes públicas integradas y datos ficticios. No requiere proveedor de IA, clave, cuenta ni base de producción. `SOURCE-SHAS.txt` fija los commits exactos de `develop` de `oicrruf/estimate-api` y `oicrruf/estimate-app`; los árboles `sources/` son exportaciones sin `.git` ni `.env*`.

## Iniciar y comprobar

Requisitos: Docker Engine con BuildKit, Docker Compose v2 y Python 3 para el verificador. Necesita acceso de lectura a los registros oficiales y a PyPI/npm en la primera construcción. Desde la raíz del paquete:

```sh
docker compose config --quiet
python3 runtime/verify_compose.py
docker compose up --build -d
python3 runtime/smoke.py
```

Abra **http://127.0.0.1:8080/demo**. Compose publica sólo `127.0.0.1:8080`, no el puerto de la API. Nginx entrega Angular y reenvía únicamente `GET /v1/demo/evaluate` al servicio `api` en la red Docker `backplane` interna. `seed` crea una vez el store sintético en el volumen nombrado `synthetic_store`; `api` lo monta en lectura y lo reabre en otro proceso. El servidor de contenedor requiere `AT279_INTERNAL_CONTAINER_MODE=1`; la entrada de API de desarrollo en `sources/api/demo/preview_api.py` conserva su bind a `127.0.0.1`.

| Prueba | Petición | Resultado esperado |
| --- | --- | --- |
| Switch, 8 PoE | `?scenario=switch` | `SW-16` compatible; `SW-8` rechazado por puertos totales |
| Switch, 12 PoE | `?scenario=switch&poe_ports_min=12` | Sin selección compatible |
| Cámara, 4 unidades | `?scenario=camera&quantity=4` | Stock insuficiente: pool compartido de 2 |
| Cámara, 2 unidades | `?scenario=camera&quantity=2` | `CAM-POE` compatible |
| UPS | `?scenario=ups` | Viable técnicamente, sin oferta |

Ejemplo: `curl -sS 'http://127.0.0.1:8080/v1/demo/evaluate?scenario=switch'`. `runtime/smoke.py` comprueba además `/demo`, los cinco casos, rutas no permitidas (404), parámetros inválidos (422), POST (403) y ausencia de CORS y `storePath`.

Para comprobar persistencia sin crear un segundo contenedor, vuelva a iniciar **el contenedor seed detenido** y reinicie API:

```sh
docker start -a at279-final-preview-seed-1
docker compose restart api
python3 runtime/smoke.py
```

El resultado del segundo seed debe incluir `"store":"reused"`. Si el nombre fue modificado por Compose, consúltelo con `docker compose ps -a`. Retire **sólo estos recursos sintéticos** cuando termine: `docker compose down -v --remove-orphans`; el volumen se elimina. Las imágenes locales pueden borrarse expresamente con `docker image rm at279-final-api:local at279-final-web:local`.

### CA de construcción opcional

La construcción ordinaria usa el almacén TLS del builder. Sólo si su proxy requiere un CA adicional **aprobado**, indique la ruta explícitamente; el helper no consulta variables de entorno. El certificado se monta como secreto temporal de BuildKit, no se copia a las imágenes ni se incluye en este paquete. No desactive TLS.

```sh
sh runtime/prepare_build_ca.sh /ruta/al/ca-bundle-aprobado.pem
docker compose -f compose.yaml -f compose.tls-ca.yaml up --build -d
python3 runtime/smoke.py
rm runtime/build-ca.pem
```

### Alternativa sin Docker (Python/Node, también en macOS)

Requisitos: Python 3.12, `uv` 0.7.6, Node 24 y npm 11. Use dos terminales. En la primera:

```sh
cd sources/api
uv run --frozen --extra demo python -m demo.agent.cli seed --store ./estimate-demo.rl
uv run --frozen --extra demo python -m demo.preview_api --store ./estimate-demo.rl --port 8001
```

En la segunda:

```sh
cd sources/app
npm ci --ignore-scripts --no-audit --no-fund
npm run demo:local
```

Abra la URL local que indique Angular, ruta `/demo`. El proxy de desarrollo del repositorio conecta `/v1/demo` con `127.0.0.1:8001`. Si sólo dispone de Python, use `curl` a `http://127.0.0.1:8001/v1/demo/evaluate?scenario=switch` y las otras consultas de la tabla. El modo local también mantiene el store explícito y separado del servicio productivo. El archivo `estimate-demo.rl` es desechable y contiene únicamente la fixture ficticia.

## Límite para un eventual Coolify privado

**No use este Compose como despliegue público tal cual.** El puerto web está fijado a loopback y no hay autenticación en Angular/API. Para una preparación posterior, se necesita un recurso temporal separado, control de acceso restrictivo externo, TLS en el proxy, arquitectura y espacio del servidor confirmados, y revisión del Compose generado antes de iniciar. Exponer únicamente la web hacia el proxy de Coolify en su puerto interno 8080; no asignar dominio ni `ports:` a `api` o `seed`. Comprobar que Coolify conserve la red interna, el volumen dedicado, `restart: "no"` en seed y el modo de seed de una sola ejecución. Probar acceso, arranque, reinicio y retirada con datos sintéticos. No se han inspeccionado el panel, host ni DNS.

La [documentación oficial de Docker Compose de Coolify](https://coolify.io/docs/applications/builds/docker-compose) indica que Coolify puede añadir redes, etiquetas y rutas al Compose de despliegue, que los dominios apuntan al servicio y puerto interno y que `ports:` publica directamente en la interfaz del servidor. La [documentación de servicios Compose](https://coolify.io/docs/services/configuration/docker-compose) distingue el Compose fuente del generado. Por ello la definición final y el dominio deben revisarse en Coolify antes de una activación privada.
