"""Map AT-265 catalog coverage to one AT-240 pattern package, fail closed."""

from __future__ import annotations

from dataclasses import dataclass

from estimate_api.contracts.universal_v1 import Scope
from estimate_api.knowledge.registry_v1 import (
    CoverageResult,
    resolve_coverage,
    validate_registry,
)

from .models import KnowledgePackage, ProjectIntake


@dataclass(frozen=True)
class RegistryContext:
    project: object
    registry: object
    category: str
    scope: Scope


def resolve_pattern_coverage(
    intake: ProjectIntake,
    package: KnowledgePackage | None,
    context: RegistryContext | None,
) -> CoverageResult:
    """Reuse registry policy; only add project/package identity checks at this boundary."""
    if context is None or package is None or package.registry_package_id is None:
        return CoverageResult("pending_specialist", (), (), ("registry_mapping_missing",))
    if (
        not isinstance(context.project, dict)
        or context.project.get("projectId") != intake.project_id
    ):
        return CoverageResult("pending_specialist", (), (), ("project_mismatch",))
    result = resolve_coverage(
        context.project,
        context.registry,
        jurisdiction=intake.jurisdiction,
        category=context.category,
        scope=context.scope,
    )
    if result.status != "cataloged":
        return result
    registry = validate_registry(context.registry).registry
    if registry is None:
        return CoverageResult("pending_specialist", (), (), ("invalid_registry",))
    matched = next(
        (item for item in registry["packages"] if item["id"] == package.registry_package_id),
        None,
    )
    if (
        result.package_ids != (package.registry_package_id,)
        or matched is None
        or (matched["version"] != package.version)
    ):
        return CoverageResult(
            "pending_specialist",
            result.package_ids,
            result.conflicts,
            ("pattern_package_mismatch",),
        )
    catalog_refs = {
        (item["id"], item["category"], item["ref"]) for item in matched["installationPatterns"]
    }
    if not set(package.pattern_refs) <= catalog_refs:
        return CoverageResult(
            "pending_specialist",
            result.package_ids,
            result.conflicts,
            ("pattern_reference_missing",),
        )
    return result
