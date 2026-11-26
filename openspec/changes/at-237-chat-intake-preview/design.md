# Diseño

`POST /v1/chat/intake-preview` recibe un `ScopeIntake` AT-246 en JSON validado y llama a `build_scope_draft` por un puerto inyectable. La respuesta incluye el borrador fiel, preguntas y `review_required`; carece de identificador persistido y de cualquier comando de confirmación. Un adaptador de descubrimiento AT-240 podrá sustituir el puerto cuando su contrato esté integrado. Una acción de aceptación futura deberá pasar por SQL/RBAC AT-208/209 y control de concurrencia AT-254. La representación A2UI AT-248 consumirá la respuesta, no define reglas de negocio nuevas.

La entrada acepta exclusivamente campos estructurados. La descripción es texto de contexto, no fuente de hechos inferidos por este endpoint. `confirmed` exige evidencia, y el endpoint rechaza entradas inválidas antes de evaluar. No hay estado, red, proveedor de modelo ni mutación.
