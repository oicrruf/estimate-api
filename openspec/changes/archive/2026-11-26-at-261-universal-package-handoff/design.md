# Diseño

La guía apunta a implementaciones existentes: `validate_project_document` valida forma e integridad local; `validate_registry` y `resolve_coverage` validan el catálogo y su aplicabilidad; `evaluate_global_constraints` evalúa checks globales declarados y evidencia; `patterns.v1` es un ejemplo de paquete de especialidad, no parte de la semántica universal. Ninguno autentica actores ni comprueba competencia real del revisor.

El smoke usa los documentos existentes `painting.json` y `event.json` y un registro ficticio con dos namespaces. Cada documento se valida antes de resolver cobertura. Una declaración de revisión ficticia permite observar `cataloged` sólo como estado de metadata; el registro no verificado produce `pending_specialist` y un rubro o jurisdicción ausente produce `unsupported`. Un check de evento agregado a una copia del fixture recorre la misma ruta de evidencia AT-267; permiso supuesto o evidencia rota queda `pending` y bloqueante. No usa AT-240 ni AT-266.
