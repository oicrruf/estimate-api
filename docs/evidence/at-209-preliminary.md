# AT-209 local authentication and project-read proof

Reconciliation base: `estimate-api/develop` `248ca4b69eb135ebff0b80fa61fb55598ba0bbb6`. This draft remains separate from the integrated deterministic `POST /v1/chat/intake-preview` route. No hosted Supabase, real GitHub OAuth, paid provider, deployment or real commercial data is used.

## Implemented boundary

- `GET /projects` and `GET /projects/{project_id}` accept Supabase Auth Bearer JWTs signed with allowlisted RS256 or ES256 keys. Verification checks `kid`, configured issuer/audience, expiry, issued-at, `authenticated` role and UUID subject; anonymous claims are rejected. Client metadata and client-supplied UUIDs never become the actor.
- The list is paginated (`limit` 1–100, default 20) in UUID order with an exclusive cursor. A missing or foreign project returns 404. JWKS caching is 600 seconds, with a 30-second cooldown for unknown key IDs; unavailable key service fails closed.
- Interactive admission uses backend-only `ESTIMATE_INTERACTIVE_ALLOWED_SUBJECTS`. A valid JWT without admission returns 403. Missing admission denies by default; invalid configuration returns 503. Admission supplements current project membership and RLS.
- Each read opens a dedicated connection, rejects a superuser, inheriting or BYPASSRLS login, and uses `SET LOCAL ROLE authenticated` plus the verified subject in a read-only `READ COMMITTED` transaction. AT-208 RLS and an explicit project filter prevent cross-project reads. Revocation takes effect with the same still-valid token. No `service_role` or AT-208 mutation path is used.
- Errors do not return tokens or DSNs. The project scope review preview is disabled in the product app without a deliberately injected extractor.

## Reproducible local checks

Run `uv sync --frozen --extra dev --extra demo --extra private-ai` and `npm ci --ignore-scripts --no-audit --no-fund --prefix ci/at-206-docs` when dependencies are not installed. Then:

```text
uv run --no-sync pytest -q
bash tests/at209/run_preliminary_read.sh
bash tests/at209/run_official_auth.sh
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy src scripts tests
uv run --no-sync python scripts/openapi.py --check
uv run --no-sync python scripts/check_secrets.py
ci/at-206-docs/node_modules/.bin/openspec validate at-209-auth-project-read --strict
```

On this isolated worktree, the commands used `PYTHONPATH=/workspace/scratch/at-209-reconciled/src` and `UV_PROJECT_ENVIRONMENT=/workspace/scratch/at-209-current/.venv` so the reused environment loaded the reconciled source. Results: **337 passed, 1 skipped, 73 warnings** in the full suite; **2 passed** in the preliminary HTTP test; the official disposable GoTrue → FastAPI preview HTTP → AT-208 RLS script passed. Ruff, formatting, mypy (94 source files), generated OpenAPI check and strict OpenSpec validation passed. The preliminary script exercises owner/editor/viewer/outsider reads, pagination and revocation against disposable PostgreSQL and then synthetic RS256 JWT HTTP tests. It also rejects an unsafe superuser DSN and anonymous claims.

The official script uses Supabase CLI **3.4.0** only to create an ephemeral ES256 signing key, official GoTrue **v2.198.0** (`ghcr.io/supabase/gotrue@sha256:ba8c0c82c574756c835c696df2a2c698020cc408a42034013d3712e34de7964d`) and PostgreSQL **17-alpine** (`postgres@sha256:f9cf3e1f0066f0eb0c48707d864f0ac5941e9ff454a072077d97a4d278d07d73`). The fixture provisions isolated roles and grants to install AT-208; GoTrue owns `auth.users`. Synthetic `.invalid` users receive real local GoTrue tokens. FastAPI verifies JWKS and uses RLS. The script checks 401/403/404/200, admission and membership changes, Uvicorn over loopback HTTP, and the project preview quota and receipt cases. Temporary keys, containers and network are removed on exit; no token or key is printed. It requires loopback port 55424 to be free. Install the pinned CLI with `npm install --prefix /tmp/at209-supabase-cli supabase@3.4.0` if absent.

A previous full `supabase start` attempt was blocked by insufficient Docker overlay space during the database image download. The independent GoTrue/PostgreSQL proof covers JWT/JWKS/HTTP/RLS but does not establish full Supabase CLI stack, GitHub OAuth, pooler or hosted-role compatibility.

## Contract coordination with estimate-app

The reconciled API OpenAPI artifact includes `GET /health`, deterministic `POST /v1/chat/intake-preview`, authenticated project list/detail, and the disabled-by-default project preview POST. Its verified SHA-256 is `0f13af69dfac409072b66a3d75e940c9bc7ea9970ac5788c0fbf1cc1edd8bcf9`. The independently checked app `develop` `a2eb13a75e79f2ea10d46167573157ef85193677` pins API `248ca4b69eb135ebff0b80fa61fb55598ba0bbb6` and the two-route artifact hash `86b72b468097253a178c8cf33d09f6ef2b10196943b46a623fca2eea0436ac06`. Its generators intentionally reject additional unreviewed routes. AT-209 cannot be integrated until the app pin and typed projections are deliberately coordinated; no app update is included here.

The proposed future GitHub OAuth path uses Supabase Auth with PKCE, exact redirect allowlisting and profile/email scopes only. Angular would exchange the code once and send the resulting Supabase access token to FastAPI. No callback or provider configuration is implemented in this draft.

## Local preview proof and limits

The synthetic `POST /v1/projects/{projectId}/scope-review-preview` requires a 1–4000-character brief and an `Idempotency-Key`. Normal HTTP tests cover missing/invalid tokens (401), unadmitted or viewer roles (403), revoked/foreign projects (404), invalid brief or blank key (422), authorized owner/editor (200), identical replay (200), changed brief under the same key (409), pending/failed receipts (409), actor/project/global quota (429), and missing storage (503). Two connections degrade or revoke a member before the transactional authorization point; both requests leave zero reservations and zero extractor calls. A failed stub or final receipt write consumes a slot and prevents another call. The private fixture stores no raw brief; its SHA-256-derived receipt UUID is a binding check, not a privacy guarantee.

No database lock stays open during extraction. Revocation after the authorization read may still precede an external call; a paid service needs a coordinated protocol. This draft has no real provider or hosted migration and does not make an estimate commercially ready.

## Remaining gates

AT-209 still requires the broader CRUD, idempotency, audit and OpenAPI scope in Linear before Done. Independent final review, exact CI, app contract coordination, real GitHub OAuth and hosted role/pooler verification remain outstanding. Keep the PR draft and do not treat this local proof as a deployment gate.

Sources: [GitHub sign-in](https://supabase.com/docs/guides/auth/social-sign-in/auth-github), [PKCE](https://supabase.com/docs/guides/auth/sessions/pkce-flow), [redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls), [Supabase changelog](https://supabase.com/changelog.md), [JWT/JWKS](https://supabase.com/docs/guides/auth/jwts), [signing keys](https://supabase.com/docs/guides/auth/signing-keys), [local development](https://supabase.com/docs/guides/local-development), [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security), [official Compose](https://github.com/supabase/supabase/blob/master/docker/docker-compose.yml).
