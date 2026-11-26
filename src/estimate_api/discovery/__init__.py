"""Domain-neutral, evidence-backed scope discovery (AT-240)."""

from .engine import discover, revalidate, review
from .models import KnowledgePackage, ProjectIntake, ReviewAction

__all__ = ["KnowledgePackage", "ProjectIntake", "ReviewAction", "discover", "review", "revalidate"]
