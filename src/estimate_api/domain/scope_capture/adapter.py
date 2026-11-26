"""Validated mapping from an AT-246 draft to an AT-264 domain package."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict
from typing import cast

from estimate_api.contracts.universal_v1 import (
    DomainPackage,
    JsonValue,
    ProjectDocument,
    validate_project_document,
)

from .contract import CONTRACT_VERSION, ScopeDraft


class ScopeAdapterError(ValueError):
    """The input or mapped project document failed validation."""


def attach_scope_draft(value: object, draft: ScopeDraft, package_id: str) -> ProjectDocument:
    """Return a new validated document with one scope package; never mutate input."""
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ScopeAdapterError("source document is not strict JSON") from error
    baseline = validate_project_document(value)
    if not baseline.valid or baseline.document is None:
        details = "; ".join(f"{issue.path}: {issue.message}" for issue in baseline.issues)
        raise ScopeAdapterError(f"invalid source document: {details}")
    if draft.contract_version != CONTRACT_VERSION:
        raise ScopeAdapterError("unsupported scope draft version")

    document = deepcopy(baseline.document)
    try:
        facts = cast(dict[str, JsonValue], json.loads(json.dumps(asdict(draft), allow_nan=False)))
    except (TypeError, ValueError) as error:
        raise ScopeAdapterError("scope draft is not strict JSON") from error
    facts["purchaseItems"] = list(draft.purchase_items)
    package: DomainPackage = {
        "id": package_id,
        "namespace": "estimate.scope-capture",
        "version": "1.0.0",
        "subjectId": document["projectId"],
        "facts": facts,
    }
    document["packages"].append(package)
    result = validate_project_document(document)
    if not result.valid or result.document is None:
        details = "; ".join(f"{issue.path}: {issue.message}" for issue in result.issues)
        raise ScopeAdapterError(f"invalid mapped document: {details}")
    return result.document
