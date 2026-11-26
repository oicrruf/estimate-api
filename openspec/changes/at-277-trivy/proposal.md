# AT-277 — Gate defensivo Trivy para API

## Why

La CI actual verifica código y secretos, pero no evalúa vulnerabilidades de dependencias, configuración o imagen construida con un escáner dedicado.

## What Changes

Agregar un check aislado de Trivy para filesystem e imagen API construida en CI. Bloquear hallazgos HIGH/CRITICAL y secretos; resumir MEDIUM sin exponer contenido. El fallo del escáner, la descarga de DB o el parser debe fallar cerrado. No cambiar reglas de protección ni despliegue.

## Fuera de alcance

No escanear hosts, bases, registros privados ni infraestructura real. No activar SARIF, notificaciones externas o excepciones sin permiso del propietario.
