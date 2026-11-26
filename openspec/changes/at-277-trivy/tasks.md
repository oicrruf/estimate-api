# Tareas AT-277 API

- [x] Definir contrato y política de severidades.
- [x] Fijar y verificar versión/digest del escáner.
- [x] Probar parser con fixtures sintéticas y fallos.
- [x] Implementar escaneo de filesystem e imagen construida en CI; registrar el límite TLS local.
- [x] Validar OpenSpec y pruebas locales; documentar bloqueos pendientes del check nuevo.
- [x] Separar hallazgos de fuente e imagen, actualizar dependencias corregidas y probar paridad OpenAPI.
- [x] Cubrir deduplicación y códigos distintos para fallo de política y de parser.

- [x] Publicar resumen JSON depurado y de retención breve, con prueba sintética.

- [x] Fijar configuración/secretos fuera del checkout y probar HIGH sintético con Trivy real.
- [ ] Ejecutar invocación y política desde una revisión protegida independiente del PR; verificar el contexto antes de exigirlo como check.
- [ ] Repetir CI y escaneo de la imagen final con el head reconciliado.
