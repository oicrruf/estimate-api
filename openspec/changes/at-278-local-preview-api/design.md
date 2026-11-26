# Diseño

`python -m demo.preview_api` arranca Uvicorn en loopback con ruta de store obligatoria y fija para el proceso. La siembra usa `python -m demo.agent.cli seed` como paso separado e idempotente. `GET /v1/demo/evaluate` recibe `scenario`, `poe_ports_min` para switch y `quantity` para camera, valida claves duplicadas/ajenas y rangos, y llama a `evaluate_offline` de AT-227. La herramienta Relate existente abre el store en modo de sólo lectura. La respuesta conserva el JSON del motor, excepto `storePath` que sólo agrega la CLI para diagnóstico local y no debe exponerse al navegador.

El contrato Pydantic discrimina switch, camera y UPS con medidas y rutas de evidencia tipadas. No se introduce motor de decisión nuevo. El frontend debe usar un proxy de desarrollo del mismo origen hacia `127.0.0.1:8001`; el servidor no habilita CORS. Error de store ausente o corrupto se devuelve sin detalles internos de rutas. El servidor no escribe ni inicia la siembra.
