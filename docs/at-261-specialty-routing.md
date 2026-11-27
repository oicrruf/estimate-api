# Specialty routing (AT-261)

`estimate_api.specialties.routing.route_specialties` is a pure, local coordinator
for Cameras, Networks, and Raceway. It accepts explicit typed facts, assigns
evidence work once per specialty and key, and returns questions and evidence
invalidations. It never returns a purchase or proposal line. AT-240 remains the
only scope discovery and review engine.

PoE cameras request a network review of the existing switch model, free PoE
ports, and power budget. Analog coax cameras with an explicitly adequate DVR
uplink do not request PoE Ethernet work. Raceway routes need measured route,
capacity verification, and cable outer diameter. An unknown fact produces a
question. The coordinator does not infer switch adequacy, raceway capacity,
power, distances, product compatibility, or code compliance.

The `previous` argument identifies evidence affected by an edited camera
count or medium, existing switch or uplink facts, route, capacity, or outer diameter.
Removing the camera scope invalidates its linked route evidence. A route must explicitly declare
`linked_to_camera` for count changes to invalidate its link evidence. Consumers
must rerun their own validated specialist checks; this module does not persist
approvals, invoke ADK or providers, or write a BOM. HTTP and A2UI integration,
analog equipment verification, and professional installation review remain open.
The input does not carry per-cable route ownership or proof revision IDs, so it
cannot identify which individual cable in a shared route changed or validate
whether an earlier proof remains current. Those decisions require a richer
specialist contract before connecting this seam to a review UI.

Run `uv run --no-sync pytest -q tests/at261` with the repository's dev extras.
