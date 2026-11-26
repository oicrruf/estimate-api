"""AT-264 project contract v1. Domain facts belong in separate packages."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Literal, NotRequired, TypedDict, TypeVar, cast

from jsonschema import Draft202012Validator

SCHEMA_VERSION = "1.0.0"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "project-document.v1.schema.json"

type EntityKind = Literal[
    "ProjectGoal",
    "Requirement",
    "Capability",
    "Resource",
    "Task",
    "Deliverable",
    "Constraint",
    "SiteCondition",
    "Evidence",
    "Dependency",
    "BOMLine",
    "Rule",
    "Approval",
]
type KnowledgeState = Literal["known", "assumed", "unknown", "conflicted"]
type OriginKind = Literal["user", "document", "agent", "system"]
type ScopeKind = Literal["project", "site", "area", "workstream"]


class Origin(TypedDict):
    kind: OriginKind
    ref: str


class Scope(TypedDict):
    kind: ScopeKind
    id: str


class Relation(TypedDict):
    predicate: str
    targetId: str


KindT = TypeVar("KindT", bound=str)


class CoreEntity(TypedDict, Generic[KindT]):
    id: str
    kind: KindT
    label: str
    origin: Origin
    scope: Scope
    revision: int
    knowledgeState: KnowledgeState
    relations: NotRequired[list[Relation]]


type ProjectGoal = CoreEntity[Literal["ProjectGoal"]]
type Requirement = CoreEntity[Literal["Requirement"]]
type Capability = CoreEntity[Literal["Capability"]]
type Resource = CoreEntity[Literal["Resource"]]
type Task = CoreEntity[Literal["Task"]]
type Deliverable = CoreEntity[Literal["Deliverable"]]
type Constraint = CoreEntity[Literal["Constraint"]]
type SiteCondition = CoreEntity[Literal["SiteCondition"]]
type Evidence = CoreEntity[Literal["Evidence"]]
type Dependency = CoreEntity[Literal["Dependency"]]
type BOMLine = CoreEntity[Literal["BOMLine"]]
type Rule = CoreEntity[Literal["Rule"]]
type Approval = CoreEntity[Literal["Approval"]]
type Entity = (
    ProjectGoal
    | Requirement
    | Capability
    | Resource
    | Task
    | Deliverable
    | Constraint
    | SiteCondition
    | Evidence
    | Dependency
    | BOMLine
    | Rule
    | Approval
)
type JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class DomainPackage(TypedDict):
    id: str
    namespace: str
    version: str
    subjectId: str
    facts: dict[str, JsonValue]


class ProjectDocument(TypedDict):
    schemaVersion: Literal["1.0.0"]
    projectId: str
    entities: list[Entity]
    packages: list[DomainPackage]


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    document: ProjectDocument | None
    issues: tuple[ValidationIssue, ...]


with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
    _schema = json.load(schema_file)
Draft202012Validator.check_schema(_schema)
_validator = Draft202012Validator(_schema)


def _pointer(parts: Iterable[object]) -> str:
    """Return a JSON Pointer for a jsonschema path."""
    tokens = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(tokens) if tokens else "/"


def validate_project_document(value: object) -> ValidationResult:
    """Validate transport shape, stable ID uniqueness, and local references."""
    schema_issues = tuple(
        ValidationIssue(_pointer(error.absolute_path), error.message)
        for error in sorted(
            _validator.iter_errors(value), key=lambda error: tuple(map(str, error.absolute_path))
        )
    )
    if schema_issues:
        return ValidationResult(False, None, schema_issues)

    document = cast(ProjectDocument, value)
    issues: list[ValidationIssue] = []
    ids: set[str] = set()
    for index, entity in enumerate(document["entities"]):
        if entity["id"] in ids:
            issues.append(ValidationIssue(f"/entities/{index}/id", "duplicate id"))
        ids.add(entity["id"])
    for index, package in enumerate(document["packages"]):
        if package["id"] in ids:
            issues.append(ValidationIssue(f"/packages/{index}/id", "duplicate id"))
        ids.add(package["id"])

    entity_ids = {entity["id"] for entity in document["entities"]}
    if not any(
        entity["id"] == document["projectId"] and entity["kind"] == "ProjectGoal"
        for entity in document["entities"]
    ):
        issues.append(ValidationIssue("/projectId", "must reference a ProjectGoal"))
    for index, entity in enumerate(document["entities"]):
        for relation_index, relation in enumerate(entity.get("relations", [])):
            if relation["targetId"] not in entity_ids:
                issues.append(
                    ValidationIssue(
                        f"/entities/{index}/relations/{relation_index}/targetId",
                        "unknown entity id",
                    )
                )
    for index, package in enumerate(document["packages"]):
        if package["subjectId"] not in entity_ids:
            issues.append(ValidationIssue(f"/packages/{index}/subjectId", "unknown entity id"))
    if issues:
        return ValidationResult(False, None, tuple(issues))
    return ValidationResult(True, document, ())
