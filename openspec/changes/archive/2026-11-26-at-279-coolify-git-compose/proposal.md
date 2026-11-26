# AT-279 — Compose reproducible desde Git para Coolify

## Why

El paquete privado probado requiere Dockerfiles y archivos auxiliares de contexto. Docker Compose Empty almacena sólo el YAML y no hace checkout del repositorio; el YAML del paquete no puede construirse allí sin reescribirlo con Dockerfiles y scripts inline o publicar imágenes. Se necesita una definición Git que descargue únicamente los dos commits públicos aprobados.

## What Changes

- Definir Compose desde Git sin puertos host, imágenes publicadas, credenciales ni servicios externos de runtime.
- Construir API y web desde commits públicos fijos, con imágenes base fijadas por digest, dependencias lock y fuentes verificadas por Git SHA.
- Probar el build, la red privada, la persistencia y las respuestas reales en CI efímero.
- Documentar ruta, ref y ajustes de UI, indicando qué comportamiento de proxy y volumen requiere inspección en Coolify.

## Out of Scope

No se instala un recurso, despliega, modifica DNS, panel, secretos, Environment o producción. No se publica una imagen ni se cambia la aplicación integrada.
