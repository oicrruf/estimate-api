# Local specialist handoff (AT-211)

`preview_specialist_handoff` takes an existing AT-246 `ScopeIntake` and typed
AT-261 `RoutingRequest`. It calls the established scope draft builder and pure
specialist router, returning assignments, questions, and their evidence reason
keys. It performs no agent, provider, HTTP, database, or pricing call.

The caller supplies `LocalEvidenceBinding` values tied to the project, exact
field, typed value, and current evidence revision. A confirmed `Fact` without a
matching binding is rejected; one ID cannot certify two incompatible fields.
Inferred facts remain unknown to the router. This local match does not
authenticate the caller, establish source provenance, or prove that a revision
is truly current. A trusted caller must bind records from a verified evidence
service before this seam could serve a real workflow. Never populate bindings
from model output or use this preview to approve a BOM.

AT-246 also carries validated client assets, evidence-backed absence of assets
or supplies, and purchase flags outside `Fact`. The local handoff rejects those
assertions until they have their own value/project/revision binding. Its
`medium`, `linked_to_camera`, and `explicit_specialties` values are typed
routing directives from the trusted local caller; they do not prove equipment
compatibility, route ownership, or site conditions. Evidence revisions must be
nonnegative integers, with booleans and floats rejected.

PoE camera work requests switch model, power, and port evidence; confirmed
analog DVR uplink avoids PoE assignments; Wi-Fi camera work requests existing
wireless capacity review. Unknown capacity stays a question. None of these
paths validates equipment compatibility, coverage, cabling, or installation.

Run `uv run --no-sync pytest -q tests/at211 tests/at261 tests/at237` with the
repository's dev, demo, and private-ai extras. Hosted ADK, chat/A2UI,
persisted approval, and professional review remain separate gates.
