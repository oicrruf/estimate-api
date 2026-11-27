# Estimate API

Estimate Agent's backend, contracts, and local evidence demos. This repository contains a
minimal HTTP API and separate domain modules. The demos and test data are synthetic.
The [initial architecture ADR](docs/adr/0001-arquitectura-inicial.md) gives the broader
context; the linked guides below explain each capability and its limits.

## Try what works today

You need Python 3.12.14 and `uv` 0.7.6. From the repository root, start the canonical
API locally:

```sh
uv sync --frozen --extra dev
uv run --no-sync uvicorn estimate_api.app:app --host 127.0.0.1 --port 8000
```

In another terminal, run `curl http://127.0.0.1:8000/health`. The expected response is
`{"status":"ok"}`. **`GET /health` is the only application operation in the canonical
HTTP API.** It shows that the process responds, not that a database, model, or other
service is ready. FastAPI also serves its generated `/openapi.json` and documentation
routes.

For a local, deterministic ADK + Relate demonstration, run:

```sh
uv run --frozen --extra demo python -m demo.agent.cli demo --store /tmp/estimate-at227.demo.rl
```

The CLI uses a synthetic graph and fixed Cypher queries. It does not call an LLM or a
remote service. See the [demo guide](demo/agent/README.md) for its scenarios and local
store behavior. A [separate HTTP preview](demo/PREVIEW_HTTP.md) offers
`GET /v1/demo/evaluate` on loopback for local UI testing; it is not mounted on the
canonical API and is not a hosted demo. Do not connect these examples to real data.

To try the [synthetic guided BOM](demo/guided_bom/README.md), seed its separate local
Relate store and start the loopback server from the repository root:

```sh
uv run --frozen --extra demo python -m demo.guided_bom.cli seed --store /tmp/estimate-guided-bom.rl
uv run --frozen --extra demo python -m demo.guided_bom.http --store /tmp/estimate-guided-bom.rl --port 8002
```

In another terminal, run
`curl -sS 'http://127.0.0.1:8002/v1/demo/guided-bom?cable_count=6&cable_variant=thick'`.
The JSON includes `wireVersion: guided-bom.v1`, candidates, evidence, and a draft BOM.
This route is separate from the canonical API; it uses fictional data and no model key.

The optional [private Luna CLI (AT-211)](demo/guided_bom/PRIVATE_AI.md) uses the
same synthetic store. It is a local command, **not a public or hosted HTTP endpoint**.
Run it only in an authorized private environment with `OPENAI_API_KEY` available to
that process. The coding checks below do not need a key.

```sh
uv sync --frozen --extra dev --extra demo --extra private-ai
uv run --frozen --extra demo --extra private-ai python -m demo.guided_bom.private_ai \
  --store /tmp/estimate-guided-bom.rl \
  --description 'Seis UTP de OD 0.278 in; tramos de 2 m y 1.5 m.'
```

This mode defaults to `gpt-6-luna`; a model change requires an explicit `--model`.
It accepts at most 700 description characters, makes one bounded extraction request
with at most 500 output tokens, a 15-second timeout, no retries, and `store=false`.
Python checks complete measurements and units against the fixture before ADK queries
Relate. Missing UTP count or cable diameter returns questions without a graph call;
alternative, approximate, fractional, or conflicting item counts fail closed before
stock or BOM evaluation. Independent camera and UTP counts stay separate;
any preview remains pending review. For an offline test without a provider, run
`uv run --frozen --extra dev --extra demo --extra private-ai pytest -q tests/test_private_guided_ai.py tests/test_private_model.py tests/test_private_camera_ai.py`.

## What is in this repository

| Area | Current state and boundary |
| --- | --- |
| [Canonical OpenAPI](contracts/openapi.json) | OpenAPI 3.1, version `0.1.0`; its only application operation is `GET /health`. `estimate-app` should pin a known revision, compare it with the upstream artifact, and regenerate its client when it changes. CLI and preview changes do not automatically extend this contract. |
| [Local ADK + Relate CLI](demo/agent/README.md) | Reproducible evaluations with fictional product, offer, and inventory evidence; no model provider or production data. |
| [Local HTTP preview](demo/PREVIEW_HTTP.md) | A separate server, defaulting to `127.0.0.1:8001`, for synthetic demo evaluations. It is not an authenticated or public API. |
| [Synthetic guided BOM (AT-232)](demo/guided_bom/README.md) | Separate loopback server at `127.0.0.1:8002` with a read-only, fixed-scenario GET; local ADK and Relate, no model call or installation advice. |
| [Private Luna CLI (AT-211)](demo/guided_bom/PRIVATE_AI.md) | Optional bounded structured extraction over synthetic text; requires an authorized private OpenAI key and exposes no HTTP endpoint. |
| [AT-208 SQL migration and evidence](docs/evidence/at-208.md) | Domain schema and RLS tested with disposable local PostgreSQL and an official Supabase PostgreSQL image. The migration has not been applied to a hosted project, and there is no authenticated domain HTTP route. |
| [AT-279 local Compose candidates](ci/at-279/README.md) | Portable and [Git-based handoff](ci/at-279/coolify-git-setup.md) candidates with synthetic CI checks. Neither is verified on Coolify or a VPS. |

## Local checks

Node 24.22.3 is also required for the pinned OpenSpec CLI. The first dependency install
needs package registry access. Local checks need no external account or production secret.

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

To regenerate the contract after an intentional canonical HTTP API change, run
`uv run --no-sync python scripts/openapi.py` and review the diff. Alternatively,
`docker compose up --build` starts the canonical health API on loopback port 8000;
this Compose file starts no database or object store. The [preview guide](demo/PREVIEW_HTTP.md)
has its own seed, server, and query commands.

## Capability guides

- [Specialty routing (AT-261)](docs/at-261-specialty-routing.md): local evidence
  assignments and questions across Cameras, Networks, and Raceway.

- [Universal project contract (AT-264)](docs/at-264-contract.md) and
  [knowledge registry (AT-265)](docs/at-265-knowledge-registry.md): versioned schemas,
  declared coverage, and validation limits.
- [Scope capture (AT-246)](openspec/specs/scope-capture/spec.md) and
  [global consistency checks (AT-267)](openspec/specs/global-solution-consistency/spec.md):
  local contracts and checks that keep unknown facts pending.
- [Scope discovery and review (AT-240)](docs/hackathon/handoff-at-240.md): local
  service entry points, synthetic rules, provenance, and revalidation; there is
  no review HTTP endpoint or persisted approval yet.
- [Local intake-to-review bridge (AT-237)](docs/at237-local-bridge.md): typed
  synthetic intake passed to AT-240 with a pinned constraint fixture, pending
  review, and no mounted HTTP route or persistence.
- [Three-domain discovery fixtures (AT-266)](docs/evidence/at-266.md): synthetic
  camera, painting, and event cases exercised through the local service.
- [Installation patterns (AT-247)](docs/at-247-installation-patterns.md),
  [service templates (AT-259)](docs/at-259-service-templates.md), and
  [synthetic Ethernet links (AT-239)](demo/ethernet/README.md): local technical
  derivations with evidence and pending checks; they do not certify an installation.
- [Pricing engine (AT-224)](docs/at-224-pricing.md) and
  [reservation boundary (AT-233)](docs/at-233-reservation-adapter.md): deterministic
  calculations or evaluations on supplied inputs, with no purchase or real reservation.
- [Relate evidence (AT-215)](docs/evidence/at-215.md),
  [local vertical demo (AT-227)](docs/evidence/at-227.md), and
  [SQL evidence (AT-208)](docs/evidence/at-208.md): reproducible commands, tests,
  and explicit limits.

[`.env.example`](.env.example) contains placeholders for future integrations, not
credentials. The unauthenticated preview and AT-279 package are not public services.
Auth/JWT integration, hosted connections, deployment checks, and professional approvals
require separate work and evidence.

## Keeping documentation current

Follow [AGENTS.md](AGENTS.md) and the [PR template](.github/PULL_REQUEST_TEMPLATE.md).
A PR that changes visible behavior, commands, configuration or environment variables,
contracts, tests, or deployment updates this README or a guide linked from it in the
same PR. If documentation does not apply, the PR explains why. Capability-specific
details belong in their guides; this README remains the English entry point for judges.
