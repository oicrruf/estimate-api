"""AT-265 catalog validation and deterministic coverage resolution.

This module never evaluates a rule or issues a technical conclusion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NotRequired, TypedDict, cast

from jsonschema import Draft202012Validator

from estimate_api.contracts.universal_v1 import ProjectDocument, Scope, validate_project_document

REGISTRY_VERSION = "1.0.0"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "knowledge-registry.v1.schema.json"


class Source(TypedDict):
    ref: str
    version: str


class Review(TypedDict):
    state: Literal["unverified", "verified"]
    requiredReviewer: str
    reviewerRef: NotRequired[str]
    evidenceRefs: list[str]


class Applicability(TypedDict):
    jurisdictions: list[str]
    categories: list[str]
    scopes: list[Scope]


class CategorySpec(TypedDict):
    category: str
    schemaRef: str


class InstallationPattern(TypedDict):
    id: str
    category: str
    ref: str


class RuleDeclaration(TypedDict):
    topic: str
    choice: str
    sourceRef: str


class RuleSet(TypedDict):
    id: str
    rules: list[RuleDeclaration]


class KnowledgePackage(TypedDict):
    id: str
    namespace: str
    version: str
    taxonomy: str
    source: Source
    applicability: Applicability
    limits: list[str]
    review: Review
    categorySpecs: list[CategorySpec]
    installationPatterns: list[InstallationPattern]
    ruleSets: list[RuleSet]


class Registry(TypedDict):
    schemaVersion: Literal["1.0.0"]
    packages: list[KnowledgePackage]


@dataclass(frozen=True)
class RegistryIssue:
    path: str
    message: str


@dataclass(frozen=True)
class RegistryValidation:
    valid: bool
    registry: Registry | None
    issues: tuple[RegistryIssue, ...]


@dataclass(frozen=True)
class CoverageConflict:
    topic: str
    declarations: tuple[tuple[str, str], ...]  # (package id, choice)


@dataclass(frozen=True)
class CoverageResult:
    status: Literal["cataloged", "unsupported", "pending_specialist"]
    package_ids: tuple[str, ...]
    conflicts: tuple[CoverageConflict, ...]
    reasons: tuple[str, ...]
    # A catalog match is never a claim of technical or normative compliance.


with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
    _schema = json.load(schema_file)
Draft202012Validator.check_schema(_schema)
_validator = Draft202012Validator(_schema)


def validate_registry(value: object) -> RegistryValidation:
    """Validate the catalog envelope and unambiguous local identifiers."""
    errors = sorted(
        _validator.iter_errors(value), key=lambda error: tuple(map(str, error.absolute_path))
    )
    if errors:
        return RegistryValidation(
            False,
            None,
            tuple(
                RegistryIssue("/" + "/".join(map(str, error.absolute_path)), error.message)
                for error in errors
            ),
        )
    registry = cast(Registry, value)
    issues: list[RegistryIssue] = []
    identities: set[tuple[str, str]] = set()
    ids: set[str] = set()
    for index, package in enumerate(registry["packages"]):
        identity = (package["namespace"], package["version"])
        if package["id"] in ids or identity in identities:
            issues.append(RegistryIssue(f"/packages/{index}", "duplicate package identity"))
        ids.add(package["id"])
        identities.add(identity)
        if package["review"]["state"] == "verified" and (
            not package["review"].get("reviewerRef") or not package["review"]["evidenceRefs"]
        ):
            issues.append(
                RegistryIssue(
                    f"/packages/{index}/review", "verified review requires reviewer and evidence"
                )
            )
        categories = set(package["applicability"]["categories"])
        for item_type in ("categorySpecs", "installationPatterns"):
            for item_index, item in enumerate(package[item_type]):
                if item["category"] not in categories:
                    issues.append(
                        RegistryIssue(
                            f"/packages/{index}/{item_type}/{item_index}/category",
                            "category outside applicability",
                        )
                    )
    return RegistryValidation(not issues, registry if not issues else None, tuple(issues))


def _scope_matches(allowed: Scope, requested: Scope, project_scope_id: str) -> bool:
    return (
        allowed["kind"] == "project" and allowed["id"] == project_scope_id
    ) or allowed == requested


def resolve_coverage(
    project_value: object,
    registry_value: object,
    *,
    jurisdiction: str,
    category: str,
    scope: Scope,
) -> CoverageResult:
    """Resolve catalog coverage; fail closed on invalid inputs, gaps and overlaps."""
    project_result = validate_project_document(project_value)
    registry_result = validate_registry(registry_value)
    if not project_result.valid or not registry_result.valid:
        return CoverageResult("pending_specialist", (), (), ("invalid_input",))
    project = cast(ProjectDocument, project_result.document)
    registry = cast(Registry, registry_result.registry)
    project_scope_id = next(
        entity["scope"]["id"]
        for entity in project["entities"]
        if entity["id"] == project["projectId"]
    )
    if (
        not jurisdiction
        or not category
        or not any(entity["scope"] == scope for entity in project["entities"])
    ):
        return CoverageResult("pending_specialist", (), (), ("invalid_request_scope",))

    referenced = {(item["namespace"], item["version"]) for item in project["packages"]}
    matching = sorted(
        (
            package
            for package in registry["packages"]
            if (package["namespace"], package["version"]) in referenced
            and jurisdiction in package["applicability"]["jurisdictions"]
            and category in package["applicability"]["categories"]
            and any(
                _scope_matches(allowed, scope, project_scope_id)
                for allowed in package["applicability"]["scopes"]
            )
        ),
        key=lambda package: package["id"],
    )
    if not matching:
        return CoverageResult("unsupported", (), (), ("no_applicable_package",))

    declarations: dict[str, set[tuple[str, str]]] = {}
    for package in matching:
        for rule_set in package["ruleSets"]:
            for rule in rule_set["rules"]:
                declarations.setdefault(rule["topic"], set()).add((package["id"], rule["choice"]))
    conflicts = tuple(
        CoverageConflict(topic, tuple(sorted(values)))
        for topic, values in sorted(declarations.items())
        if len({choice for _, choice in values}) > 1
    )
    reasons = tuple(
        reason
        for reason, condition in (
            ("unverified_package", any(p["review"]["state"] != "verified" for p in matching)),
            ("overlapping_packages", len(matching) > 1),
            ("contradictory_declarations", bool(conflicts)),
        )
        if condition
    )
    return CoverageResult(
        "pending_specialist" if reasons else "cataloged",
        tuple(package["id"] for package in matching),
        conflicts,
        reasons,
    )
