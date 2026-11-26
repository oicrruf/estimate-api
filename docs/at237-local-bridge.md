# AT-237 local intake to scope review (synthetic)

This internal adapter is not mounted in the FastAPI app. It accepts typed
`NetworkIntake` values, preserves the AT-246 draft questions and calls AT-240
for a review proposal. It never persists, approves, buys, or calls a model.

From the repository root with the existing `dev` dependencies:

```bash
python -m pytest -q tests/at237/test_scope_review_bridge.py
python scripts/openapi.py --check
git diff --exit-code origin/develop -- src/estimate_api/app.py contracts/openapi.json
```

The tests use the checked-in AT-267 fictional constraint fixture. Eight PoE
cameras plus one distinct uplink exceed an eight-port total switch even though
eight PoE ports suffice. The reviewed AT-240 camera package derives candidate
dependencies, while absent evidence keeps `commercialReady=false`. The AT-246
draft also retains unanswered site questions. Changing the camera count creates
AT-240 change records and requires a new constraint document; the old fixture
is never silently reused.

`ConstraintSnapshot` accepts only the pinned AT-267 synthetic fixture and its
matching 8+1 counts; altered or stale same-need documents fail closed. It is
not a verified production evidence source. AT-248 must own freshness and
provenance, AT-209 must own project authorization and
storage, and AT-254 must own a user confirmation step. AT-280 must approve any
future public route and canonical OpenAPI update. No professional or commercial
approval is implied by this demonstration.
