"""Versioned, domain-specific knowledge catalog boundary."""

from .registry_v1 import resolve_coverage, validate_registry

__all__ = ["resolve_coverage", "validate_registry"]
