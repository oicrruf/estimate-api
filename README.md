# Estimate API

Backend y contratos de Estimate Agent. Este repositorio contiene una API HTTP mínima,
paquetes de dominio y pruebas locales con datos ficticios. El [ADR inicial](docs/adr/0001-arquitectura-inicial.md)
describe la arquitectura; las guías enlazadas abajo detallan cada capacidad y sus límites.

## Qué se puede ejecutar hoy

| Entrada | Alcance |
| --- | --- |
| `estimate_api.app:app` | API HTTP canónica: sólo `GET /health` como operación de aplicación. Responde `{"status":"ok"}` para indicar que el proceso responde; no comprueba dependencias. `/openapi.json` y las rutas de documentación son propias de FastAPI. |
| [CLI ADK + Relate](demo/agent/README.md) | Demo local determinista con consultas Cypher y datos ficticios. No usa LLM ni servicios remotos. |
| [Preview HTTP local](demo/PREVIEW_HTTP.md) | Servidor separado en `127.0.0.1:8001` con `GET /v1/demo/evaluate`; no forma parte del OpenAPI canónico ni está desplegado. |
| [Synthetic guided BOM AT-232](demo/guided_bom/README.md) | Separate loopback server at `127.0.0.1:8002` with `GET /v1/demo/guided-bom`, local ADK and Relate, and no model call or installation advice. |
| [Migración SQL AT-208](docs/evidence/at-208.md) | Esquema de dominio y RLS con pruebas locales descartables y ensayo en imagen oficial de Supabase PostgreSQL. No es una migración aplicada al proyecto alojado ni una ruta HTTP autenticada. |
| [Candidato AT-279](ci/at-279/README.md) | Paquete y pruebas de Compose para una demo privada futura. Es un candidato local/CI, sin despliegue Coolify operativo. |

El contrato HTTP canónico es [contracts/openapi.json](contracts/openapi.json), OpenAPI 3.1,
versión `0.1.0`. `estimate-app` debe fijar una revisión conocida de este artefacto,
compararla con el origen y regenerar su cliente cuando cambie. Un cambio en la CLI
o en la preview local no añade por sí mismo una operación a este contrato.

## Desarrollo local

Requisitos fijados para los checks principales: Python 3.12.14, `uv` 0.7.6 y Node
24.22.3. La primera instalación requiere acceso a los registros de paquetes. No se
necesitan cuentas externas ni secretos de producción.

```sh
uv sync --frozen --extra dev
npm ci --ignore-scripts --no-audit --no-fund --prefix ci/at-206-docs
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy src scripts tests
uv run --no-sync pytest -q
uv run --no-sync python scripts/openapi.py --check
uv run --no-sync python scripts/check_secrets.py
ci/at-206-docs/node_modules/.bin/openspec validate --specs --strict
ci/at-206-docs/node_modules/.bin/openspec validate --archived --strict
```

Para iniciar la API canónica local: `uv run --no-sync uvicorn estimate_api.app:app --reload`.
`docker compose up --build` ofrece el mismo health en el puerto 8000 de loopback,
sin base de datos ni almacén de objetos. Si cambia intencionalmente la API HTTP,
regenere el contrato con `uv run --no-sync python scripts/openapi.py` y revise el diff.

La demo tiene dependencias opcionales:

```sh
uv run --frozen --extra demo python -m demo.agent.cli demo --store /tmp/estimate-at227.demo.rl
```

Su [guía](demo/agent/README.md) documenta los escenarios y el archivo Relate local.
Para la preview HTTP, siga [los dos comandos de arranque y consultas](demo/PREVIEW_HTTP.md).
No conecte estos ejemplos a datos reales.

## Guías por capacidad

- [Contrato universal de proyecto AT-264](docs/at-264-contract.md) y
  [registro de conocimiento AT-265](docs/at-265-knowledge-registry.md): esquemas
  versionados, cobertura declarada y límites de validación.
- [Captura de alcance AT-246](openspec/specs/scope-capture/spec.md) y
  [consistencia global AT-267](openspec/specs/global-solution-consistency/spec.md):
  contratos y checks locales que conservan hechos desconocidos como pendientes.
- [Patrones de instalación AT-247](docs/at-247-installation-patterns.md),
  [plantillas de servicios AT-259](docs/at-259-service-templates.md) y
  [enlaces Ethernet sintéticos AT-239](demo/ethernet/README.md): derivaciones
  técnicas locales con pendientes y evidencia; no certifican instalaciones.
- [Motor de precios AT-224](docs/at-224-pricing.md) y
  [límite de reservas AT-233](docs/at-233-reservation-adapter.md): cálculos o
  evaluación local determinista sobre entradas suministradas, sin compra ni
  reserva real.
- [Evidencia Relate AT-215](docs/evidence/at-215.md),
  [vertical local AT-227](docs/evidence/at-227.md) y
  [SQL AT-208](docs/evidence/at-208.md): comandos reproducibles, pruebas y límites.

`.env.example` contiene marcadores para integraciones futuras; no proporciona
credenciales. Ni la preview sin autenticación ni el paquete AT-279 constituyen un
servicio público. La integración Auth/JWT, las conexiones alojadas, las pruebas de
despliegue y las aprobaciones profesionales requieren sus propios cambios y gates.

## Mantenimiento

Siga [AGENTS.md](AGENTS.md) y la [plantilla de PR](.github/PULL_REQUEST_TEMPLATE.md).
Cada PR que cambie comportamiento visible, comandos, configuración o entorno,
contratos, pruebas o despliegue actualiza este README o una guía enlazada desde él
en el mismo PR. Si no corresponde documentación, el PR explica por qué. Los detalles
de cada capacidad permanecen en su guía; este README conserva las entradas y los
límites vigentes.
