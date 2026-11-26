# Diseño

`demo.private_model.OpenAIJsonExtractor` concentra la única petición a Responses.
El modelo predeterminado es `gpt-6-luna`, con `reasoning.effort=none`, esquema
estricto, sin herramientas remotas, `store=false`, 500 tokens de salida,
15 segundos y cero reintentos. La opción `--model` exige selección explícita;
una falla del modelo elegido no invoca otro. El SDK devuelve objeto HTTP
tipado; se inspecciona `status_code`, luego `parse()`, y se emiten sólo
estado y contadores de tokens. Ningún cuerpo o excepción remota se imprime.

Los agentes ADK locales usan `FunctionTool` con consultas Relate fijas. En
cámaras, Python primero valida que 2 o 4 estén respaldados inequívocamente en
el texto; si no hay cantidad, devuelve una pregunta sin abrir el store. Si la
hay, Relate devuelve caminos con `EV-CAM-POE` y `EV-POOL-CAM` y la evaluación
offline existente calcula compatibilidad y capacidad de pool. No se reutiliza
el valor por defecto de cuatro cámaras de `EvaluationRequest` cuando falta la
cantidad en el texto.

El GET `/v1/demo/guided-bom` continúa separado y determinista. Ambos CLI
privados reciben sólo fixture sintético; no se monta una ruta HTTP paga.
Pruebas offline usan respuestas SDK simuladas y store Relate real. La ejecución
OpenAI real desde esta rama queda como gate separado.
