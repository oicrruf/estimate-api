"""Generic, evidence-gated solution consistency checks (AT-267)."""

from .evaluate import Finding, SourceRef, evaluate_global_constraints

__all__ = ["Finding", "SourceRef", "evaluate_global_constraints"]
