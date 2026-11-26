# Design

`NetworkIntake` holds the AT-246 `ScopeIntake` plus confirmed or inferred
camera and uplink counts. The bridge never parses description text. Confirmed
whole counts become AT-240 `Need` values; inferred and missing counts remain
pending. AT-240's reviewed synthetic camera package, constraint evaluation and
proposal diff own all dependency, status and change rules.

`ConstraintSnapshot` is a local caller-attested fixture binding, not a trusted
production check. On a subsequent preview the bridge discards that document,
retains required check IDs and marks them pending. AT-248 must supply a trusted
fresh snapshot before a real confirmation path. The response keeps
`scope_review_pending`, `review_required=true` and `persisted=false` regardless
of AT-240 status. No HTTP route, approval action, database write or paid model
call exists in this change.

AT-280 compares canonical OpenAPI bytes; this branch leaves `app.py` and
`contracts/openapi.json` untouched. AT-209 owns project authorization and
durable revisions. AT-254 owns explicit confirmation. A future adapter should
reuse this internal typed boundary after those dependencies land.
