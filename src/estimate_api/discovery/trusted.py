"""Repository-reviewed synthetic rule and pattern boundary.

The manifest is code-reviewed content, not a user-supplied attestation. These
examples establish deterministic behavior; they do not certify installations.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

from estimate_api.knowledge.registry_v1 import validate_registry
from estimate_api.patterns.v1 import Pattern

from .models import KnowledgePackage, ProjectIntake, Rule
from .registry_adapter import RegistryContext

MANIFEST = Path(__file__).parent / "data/reviewed-packages.v1.json"


def _manifest() -> dict[str, Any]:
    value = cast(dict[str, Any], json.loads(MANIFEST.read_text(encoding="utf-8")))
    if value.get("schemaVersion") != "reviewed-packages.v1" or value.get("synthetic") is not True:
        raise ValueError("Unsupported reviewed package manifest")
    return value


def _record(package_id: str) -> dict[str, Any] | None:
    return next((item for item in _manifest()["packages"] if item["id"] == package_id), None)


def reviewed_package(package_id: str) -> KnowledgePackage:
    """Load one exact, versioned synthetic package from the checked-in manifest."""
    item = _record(package_id)
    if item is None:
        raise ValueError("Package is not in the reviewed manifest")
    rules = tuple(
        Rule(
            id=entry["id"],
            source_key=entry["sourceKey"],
            target_key=entry["targetKey"],
            kind=None,
            work_package=item["category"],
            relation="REQUIRES",
            evidence=entry["sourceRef"],
            quantity_mode=entry["quantityMode"],
            factor=entry["factor"],
            unit=entry["unit"],
            source_refs=(entry["sourceRef"],),
        )
        for entry in item["rules"]
    )
    pattern = item["pattern"]
    return KnowledgePackage(
        domain=item["domain"],
        version=item["version"],
        jurisdiction=item["jurisdiction"],
        source=item["source"],
        rules=rules,
        registry_package_id=item["id"],
        pattern_refs=((pattern["id"], pattern["category"], pattern["ref"]),),
    )


def resolve_reviewed_package(
    intake: ProjectIntake,
    supplied: KnowledgePackage | None,
    context: RegistryContext | None,
) -> tuple[KnowledgePackage | None, str | None]:
    """Reject changed rules, foreign domains, versions, or catalog declarations."""
    if supplied is None or supplied.registry_package_id is None:
        return None, "reviewed_package_missing"
    item = _record(supplied.registry_package_id)
    if item is None:
        return None, "reviewed_package_missing"
    if (
        intake.project_id != item["projectId"]
        or intake.domain != item["domain"]
        or intake.jurisdiction != item["jurisdiction"]
        or supplied != reviewed_package(item["id"])
    ):
        return None, "reviewed_package_mismatch"
    if context is not None:
        registry = validate_registry(context.registry).registry
        if (
            registry is None
            or context.category != item["category"]
            or context.scope != item["scope"]
            or not isinstance(context.project, dict)
            or context.project.get("projectId") != intake.project_id
        ):
            return None, "reviewed_catalog_mismatch"
        catalog = next((p for p in registry["packages"] if p["id"] == item["id"]), None)
        if (
            catalog is None
            or catalog["version"] != item["version"]
            or catalog["source"]["ref"] != item["source"]
            or catalog["source"]["version"] != item["version"]
            or item["category"] not in catalog["applicability"]["categories"]
            or item["jurisdiction"] not in catalog["applicability"]["jurisdictions"]
            or item["scope"] not in catalog["applicability"]["scopes"]
        ):
            return None, "reviewed_catalog_mismatch"
        declarations = {
            (rule["topic"], rule["choice"], rule["sourceRef"])
            for group in catalog["ruleSets"]
            for rule in group["rules"]
        }
        expected = {(rule["id"], rule["targetKey"], rule["sourceRef"]) for rule in item["rules"]}
        if not expected <= declarations:
            return None, "reviewed_rule_declaration_missing"
    return supplied, None


def is_reviewed_pattern(pattern: Pattern) -> bool:
    """Match the entire AT-247 pattern body against a checked-in digest."""
    digest = hashlib.sha256(
        json.dumps(pattern, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    return any(
        item["id"] == pattern["id"]
        and item["version"] == pattern["version"]
        and item["category"] == pattern["category"]
        and item["sourceRef"] == pattern["sourceRef"]
        and "".join(item["sha256Parts"]) == digest
        for item in _manifest()["patterns"]
    )
