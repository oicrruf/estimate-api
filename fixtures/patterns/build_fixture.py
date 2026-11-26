"""Genera una fixture sintética estable; nunca lee datos de proyecto."""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
SOURCE = "synthetic://at-247/patterns/1.0.0"


def dependency(name, origin, target, condition=None, quantity_fact=None):
    return {
        "id": f"at247:edge:{name}",
        "fromId": f"at247:item:{origin}",
        "toId": f"at247:item:{target}",
        "ruleId": f"AT247-{name.upper().replace('-', '_')}",
        "sourceRef": SOURCE,
        "condition": condition,
        "quantityFact": quantity_fact,
    }


def pattern(name, category, edges):
    return {
        "id": f"at247:pattern:{name}",
        "version": "1.0.0",
        "category": category,
        "rootId": f"at247:item:{name}",
        "sourceRef": SOURCE,
        "maxDepth": 6,
        "maxEdges": 64,
        "dependencies": edges,
    }


patterns = [
    pattern(
        "poe-camera",
        "fictional-camera",
        [
            dependency("camera-utp", "poe-camera", "utp", {"fact": "wired_run", "equals": True}),
            dependency(
                "camera-mount",
                "poe-camera",
                "camera-mount",
                {"fact": "mount_required", "equals": True},
            ),
            dependency(
                "camera-poe", "poe-camera", "poe-power", {"fact": "poe_source", "equals": True}
            ),
            dependency("camera-link-test", "utp", "link-test"),
            dependency("camera-ends", "utp", "utp-connector", quantity_fact="utp_ends"),
        ],
    ),
    pattern(
        "mesh",
        "fictional-mesh",
        [
            dependency("mesh-wired", "mesh", "utp", {"fact": "backhaul", "equals": "wired"}),
            dependency(
                "mesh-wireless",
                "mesh",
                "wireless-survey",
                {"fact": "backhaul", "equals": "wireless"},
            ),
            dependency(
                "mesh-mount", "mesh", "mesh-mount", {"fact": "mount_required", "equals": True}
            ),
            dependency(
                "mesh-power", "mesh", "power-source", {"fact": "power_required", "equals": True}
            ),
            dependency("mesh-ends", "utp", "utp-connector", quantity_fact="utp_ends"),
            dependency("mesh-link-test", "utp", "link-test"),
            dependency("mesh-wireless-test", "wireless-survey", "wireless-test"),
        ],
    ),
    pattern(
        "emt-route",
        "fictional-route",
        [
            dependency(
                "emt-measured",
                "emt-route",
                "at238-route-evaluation",
                {"fact": "route_measured", "equals": True},
            ),
            dependency(
                "emt-lb", "emt-route", "lb", {"fact": "lb_required", "equals": True}, "lb_points"
            ),
        ],
    ),
    pattern(
        "enclosure",
        "fictional-enclosure",
        [
            dependency(
                "enclosure-mount",
                "enclosure",
                "enclosure-mount",
                {"fact": "mount_required", "equals": True},
            ),
            dependency(
                "enclosure-outlet",
                "enclosure",
                "interior-outlet",
                {"fact": "interior_outlet_required", "equals": True},
                "outlet_points",
            ),
            dependency(
                "enclosure-power",
                "enclosure",
                "power-source",
                {"fact": "power_required", "equals": True},
            ),
        ],
    ),
    pattern(
        "power",
        "fictional-power",
        [
            dependency(
                "power-source", "power", "power-source", {"fact": "power_required", "equals": True}
            ),
            dependency(
                "power-test",
                "power-source",
                "power-test",
                {"fact": "test_required", "equals": True},
            ),
        ],
    ),
]

(BASE / "patterns.v1.json").write_text(
    json.dumps({"schemaVersion": "1.0.0", "sourceRef": SOURCE, "patterns": patterns}, indent=2)
    + "\n",
    encoding="utf-8",
)
