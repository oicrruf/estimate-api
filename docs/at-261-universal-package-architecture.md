# AT-261 — entrega de arquitectura universal y paquetes por especialidad

## Contratos que existen hoy

| Responsabilidad | Módulo integrado | Invariante comprobable |
| --- | --- | --- |
| Documento neutral de proyecto | `contracts/universal_v1.py` y su JSON Schema | Valida versión `1.0.0`, clases de entidad, sobre común, ID únicos, `ProjectGoal` y referencias locales. Los hechos especializados viven en `packages[].facts`, vinculados por `subjectId`. |
| Catálogo de conocimiento | `knowledge/registry_v1.py` y su JSON Schema | Valida namespace y versión, fuente, jurisdicción, categorías, ámbitos, límites, declaración de revisión y referencias de patrones. Rechaza identidades duplicadas y revisión `verified` sin referencia de revisor y evidencia declarada. |
| Aplicabilidad | `knowledge/registry_v1.resolve_coverage` | Compara namespace y versión referenciados por el proyecto, categoría, jurisdicción literal y ámbito. Un paquete sin revisión declarada, solapes, contradicciones o entrada inválida producen `pending_specialist`; ausencia de paquete aplicable produce `unsupported`. `cataloged` sólo significa cobertura de metadata. |
| Checks globales declarados | `constraints/evaluate.py` | Evalúa cardinalidad, capacidad, compatibilidad y cobertura con fuente, revisión y entidades `Evidence` conocidas. Una fuente supuesta, stale o rota produce `pending` bloqueante; `pass` sólo satisface el check suministrado. |
| Ejemplo de patrón especializado | `patterns/v1.py` y `patterns/relate_seed.py` | Expande dependencias sintéticas condicionadas con evidencia y límites; conserva candidatos, no una BOM aprobada. El seed usa Relate local. Los evaluadores de hardware y Ethernet son otros módulos de dominio. |

Estos módulos son bibliotecas puras o demostraciones locales. No hay un motor de aprobación profesional universal. `origin.ref`, `reviewerRef` y `evidenceRefs` son referencias declaradas: los validadores no autentican su emisor ni verifican la competencia del revisor. Una declaración sintética `verified` en el smoke sólo demuestra la rama determinista `cataloged`.

## Incorporar un rubro

1. Modelar metas, requisitos, recursos, tareas, restricciones, evidencia y líneas como entidades del mismo `ProjectDocument`. Colocar hechos propios en un paquete con namespace y versión de dominio, sujeto existente y esquema especializado fuera del núcleo.
2. Agregar una entrada versionada al registro con categorías, ámbitos, jurisdicciones literales, fuente, límites, esquema y revisor requerido. El proyecto referencia exactamente `namespace` y `version`; `resolve_coverage` decide si ese catálogo aplica.
3. Implementar validación o derivación especializada en un módulo del rubro. Puede aportar patrones y checks declarativos al contrato común sin agregar ramas como `if camera` en `universal_v1.py`, `registry_v1.py` o `constraints/evaluate.py`.
4. Conservar en cada resultado IDs de regla, versión, fuente, revisión y evidencia. Si falta cobertura o evidencia, mantener `unsupported`, `pending_specialist` o un hallazgo `pending` según el límite que falló. La decisión técnica exige el flujo de revisión propio del rubro; el núcleo no la inventa.

El proyecto de pintura y el de evento muestran dos namespaces no cámara. No incluyen esquemas de hechos especializados implementados; el núcleo valida únicamente el sobre `facts`, como indica AT-264. Los patrones de instalaciones AT-247 son un ejemplo concreto, no un requisito para todos los rubros.

## Frontera de confianza y aislamiento

Los `projectId` y `scope.id` locales permiten integridad y aplicabilidad; **no** autorizan acceso. En una futura frontera de servicio confiable, FastAPI deberá autenticar JWT (firma, emisor, audiencia y caducidad), derivar actor de ese token, comprobar membresía y permiso sobre el proyecto solicitado antes de cargar documentos o resolver cobertura, y aplicar RLS por proyecto a las tablas expuestas. La autorización debe repetirse en operaciones API/MCP y Storage. Estas decisiones están en ADR 0001 y quedan para sus issues de implementación; este handoff no prueba aislamiento entre usuarios ni modifica Auth, SQL o RLS.

AT-240 y AT-266 siguen en borrador. `DraftCandidate` de AT-247 es una interfaz para propuesta futura, no un flujo de propuesta ni una selección comercial. No se consume código de esas ramas ni se afirma que el workflow completo esté listo.

## Prueba reproducible

```sh
UV_CACHE_DIR=/tmp/at261-uv-cache uv sync --frozen --extra dev
UV_CACHE_DIR=/tmp/at261-uv-cache uv run --no-sync python demo/architecture/smoke.py
UV_CACHE_DIR=/tmp/at261-uv-cache uv run --no-sync pytest -q tests/at261
```

El script usa `fixtures/valid/painting.json`, `fixtures/valid/event.json` y `fixtures/knowledge/handoff-synthetic.json`. Para cada rubro exige `pending_specialist` sin revisión declarada, `cataloged` sólo tras agregar una declaración de revisión ficticia, y `unsupported` con jurisdicción, categoría o versión distinta. En el evento, una fuente supuesta y una cadena de evidencia rota producen `pending` bloqueante; una cadena sintética completa produce `pass` para ese check. No lee proyectos reales, no toca servicios ni valida normas.
