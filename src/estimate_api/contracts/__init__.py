"""Versioned domain-neutral project contracts."""

from .universal_v1 import (
    ProjectDocument,
    ValidationIssue,
    ValidationResult,
    validate_project_document,
)

__all__ = ["ProjectDocument", "ValidationIssue", "ValidationResult", "validate_project_document"]
