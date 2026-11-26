"""Provisional AT-246 scope capture boundary, independent of core schema."""

from .adapter import ScopeAdapterError, attach_scope_draft
from .contract import (
    CONTRACT_VERSION,
    AssetAvailability,
    AssetValidation,
    BlockingQuestion,
    Certainty,
    ClientAsset,
    Fact,
    Measurement,
    ScopeDraft,
    ScopeIntake,
    SupplyItem,
    SupplyOwner,
    build_scope_draft,
)

__all__ = [
    "CONTRACT_VERSION",
    "AssetAvailability",
    "AssetValidation",
    "BlockingQuestion",
    "Certainty",
    "ClientAsset",
    "Fact",
    "Measurement",
    "ScopeDraft",
    "ScopeIntake",
    "SupplyItem",
    "SupplyOwner",
    "build_scope_draft",
    "ScopeAdapterError",
    "attach_scope_draft",
]
