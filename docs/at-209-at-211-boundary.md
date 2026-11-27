# AT-209 to AT-211 interactive execution boundary

Status: local contract proposal on API `develop` `248ca4b69eb135ebff0b80fa61fb55598ba0bbb6`. No paid route is deployed. AT-211 provides a pure local `preview_specialist_handoff` function; it does not authenticate a caller or establish evidence provenance. Do not connect it to a paid provider through a public endpoint without a separate reviewed service boundary.

## Available HTTP entry point

- `GET /projects` and `GET /projects/{project_id}` require a Supabase Auth Bearer access token. `get_actor` validates JWKS signature, issuer, audience, time claims, role and UUID subject. `get_interactive_actor` then checks a backend-only UUID admission list. `require_project_access` reads current ownership or membership under AT-208 RLS and returns `ProjectView(id, name, revision, access_role)` or 404.
- A future `POST /projects/{project_id}/agent/runs` must resolve the path project, evidence, budget and knowledge package from trusted records. AT-211 has not approved a paid-run role policy, so that route must remain unavailable. A ChatGPT/MCP session or GitHub token cannot replace the Supabase Auth access token.

```python
from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException
from estimate_api.authorization import get_interactive_actor
from estimate_api.projects import ProjectView, require_project_access

# Integration sketch for AT-211; this route is not installed.
def start_agent_run(
    project_id: UUID,
    actor: Annotated[UUID, Depends(get_interactive_actor)],
    project: Annotated[ProjectView, Depends(require_project_access)],
):
    raise HTTPException(403, "Agent run role policy pending")
```

The HTTP dependency is an early filter, not irrevocable permission to spend. A mutable service must recheck the actor, admission, membership, approved role, canonical project revision and idempotency key in its own transaction before reserving budget or invoking a provider. It must bind usage and results to the project and record an audit trail. A JWT can remain valid after membership is revoked. Never trust client-supplied commercial facts or evidence as canonical records.

## Disposable authorization proof

`bash tests/at209/run_official_auth.sh` uses pinned GoTrue and PostgreSQL images with ephemeral synthetic users and keys. It tests missing or invalid Bearer tokens (401), valid but unadmitted identity (403), missing or revoked membership (404), and authorized owner/member reads (200). Uvicorn is exercised over a normal loopback HTTP socket. No model, charge, real GitHub OAuth or hosted service is involved.

## Local project scope review preview

`POST /v1/projects/{projectId}/scope-review-preview` accepts JSON `{ "brief": "..." }` (1–4000 characters) and an `Idempotency-Key` header (1–100 characters). The product app has no extractor installed and stays unavailable by default. Only `tests.at209.preview_server` injects a synthetic extractor in the disposable test server. Its `scope-review-preview.v1` response has `state=pending_review`, `reviewRequired=true`, `persisted=false` and `commercialReady=false`. The four-camera, two-in-stock example is a fixture, not commercial evidence.

`tests/at209/local_preview_reservations.sql` creates a private table only in disposable PostgreSQL. It stores no raw brief or token. The reservation login has no superuser, BYPASSRLS or inherited rights; it can SELECT/INSERT and update receipt fields only. The reservation transaction temporarily assumes `authenticated` and rechecks owner/editor under RLS. A transaction-scoped advisory lock serializes the one-hour trial limits of 2 per actor, 4 per project and 8 globally. A completed key replays its saved response without another extractor call; pending or failed receipts return 409. Quota exhaustion returns 429 and storage failure returns 503.

A receipt binds the exact UTF-8 brief to actor, project and key through a versioned SHA-256-derived internal UUID. A different brief with the same completed key returns 409 without replaying the old answer or consuming another slot. A whitespace-only key returns 422 before reservation. The digest is a request-binding check, not a confidentiality control. This disposable proof does not change the hosted schema or enable a provider.

The optional local ADK/Relate camera adapter projects only a pending draft with a fixed question, requested quantity, synthetic evidence IDs and shared stock availability. It requires one fixed read-only graph query and coherent evidence; prices, offers, model text and usage metrics stay out of the API response. Unit tests inject a fake model and seed a disposable synthetic store. The product still has no installed extractor and is unavailable by default.

The private demo runner accepts at most 700 characters, while the existing HTTP request schema accepts 4000. A selected synthetic test store may declare that 700-character capability. It checks owner/editor inside the reservation transaction before returning a non-echoing 422 for a longer brief, before receipt or quota work. Viewers and revoked members receive their usual 403/404 without adapter details. The ordinary product store does not declare an adapter limit. Do not truncate input or raise the runner limit without a reviewed provider and cost policy. Real provider selection and post-reservation revocation remain open.

The reservation is a trial quota, not money or authorization to call a model. It commits before the synthetic extractor; the receipt becomes `complete` or `failed` in a later transaction. A failed extractor or receipt write leaves the slot consumed and prevents a second call. No database transaction or lock is held during extraction. The authorization point is the role read immediately before reservation: a revocation committed afterward can still precede an external call. A paid service requires a coordinated authorization/cancellation protocol to close that remaining race.

For Angular, `200` is a human-review proposal that is not saved. `401` requires a session; `403` means no admission or edit role; `404` hides missing or revoked projects; `422` means invalid input or header; `409` means key mismatch or a pending/failed receipt that must not be retried automatically; `429` means trial quota exhausted; and `503` means disabled service or internal failure. A completed key with the same brief returns the same `200`. This description does not install the route in Angular or grant commercial readiness.
