# Estimate API

Estimate Agent API bootstrap (AT-207), based on [ADR 0001](docs/adr/0001-arquitectura-inicial.md).

## Contract

`contracts/openapi.json` is the canonical deterministic OpenAPI 3.1 artifact, version `0.1.0`. The only application operation is `GET /health` (`operationId: health`), returning HTTP 200 JSON `{"status":"ok"}`. `/openapi.json` and FastAPI documentation routes are framework documentation. Health reports process liveness only.

The `estimate-app` repository must pin this file from a known API commit or `develop` and generate its TypeScript client from it. Its CI should fetch the canonical API artifact live, compare it to the tracked frontend reference, regenerate TypeScript, and fail on either drift. Comparing a digest of only the local copy cannot detect upstream API changes. If a pinned commit is used, update it deliberately in a coordinated PR. No other domain endpoints are specified here.

## Local development

Requires Python 3.12.14, uv 0.7.6, Node 24.22.3. No external account or production secret is needed.

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

To update the contract after an intentional API change, run `uv run --no-sync python scripts/openapi.py` and review the diff. Start locally with `uv run --no-sync uvicorn estimate_api.app:app --reload` or `docker compose up --build`. Docker Compose binds port 8000 on loopback and runs no database or object store.

## Environments and future modules

`.env.example` lists future backend-only settings as placeholders. Do not copy secret values into Git or a frontend bundle. ADK, MCP, Relate, SQL, domain, pricing, integrations, migration, and Supabase integration are reserved module boundaries and are not active in this bootstrap. The existing Supabase project is not modified here. Connection, Auth, Storage, schema, and environment segregation gates remain deferred to their implementation issues. Local tests use synthetic data and need no real account. Supabase Free quotas and inactivity behavior must be rechecked before deployment, as described in ADR 0001.

## Git and OpenSpec

Follow [AGENTS.md](AGENTS.md). OpenSpec uses `spec-driven` in `openspec/config.yaml`; archived AT-206 and AT-207 changes and current specs are validated in CI. `develop` integrates issue PRs via Squash & Merge; `main` receives approved fast-forward releases preserving issue commit SHAs. Branch protection, merge method settings and release promotion require separate authorized configuration; this PR only supplies checks and policy documentation. AT-226 tests release promotion and rollback. AT-277 adds Trivy after AT-207 merges.

## AT-246 scope capture

`src/estimate_api/domain/scope_capture` contains a versioned scope-draft contract and an adapter to the universal project document. It uses synthetic examples and has no persistence or external service access. See `openspec/changes/archive/2026-11-26-at-246-scope-capture/` for the specification.

## AT-227 demo local

Con Python 3.12 y `uv` 0.7.6, la entrada ADK + Relate usa únicamente datos ficticios y un store local explícito. El primer comando descarga dependencias fijadas en `uv.lock`; la evaluación no llama a un proveedor de modelo:

```sh
uv run --frozen --extra demo python -m demo.agent.cli demo --store /tmp/estimate-at227.demo.rl
```

Véanse [prerequisitos, modo de almacenamiento, ayuda y límites](demo/agent/README.md). La [API local de vista previa AT-278](demo/PREVIEW_HTTP.md) se ejecuta en loopback y no está montada en la API productiva. La pantalla Angular se integra por separado.
