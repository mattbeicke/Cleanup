"""Combine local evidence into a clear removal recommendation."""

from __future__ import annotations

from .explainer import explain
from .models import ItemInfo
from .scanner import is_protected


def removal_assessment(item: ItemInfo) -> dict[str, str]:
    """Produce an honest local assessment without pretending to use an AI service."""
    explanation = explain(item)
    if is_protected(item.path):
        recommendation = "Do not remove"
        reason = "This is a protected system, source-control, IDE, or environment folder."
    elif any(word in explanation.lower() for word in ("regenerated", "cache", "temporary", "build output")):
        recommendation = "Likely removable"
        reason = "It appears to be generated or temporary data. Close any related application first."
    elif item.path.suffix.lower() in {".tmp", ".log"}:
        recommendation = "Likely removable"
        reason = "This file type is commonly temporary or diagnostic data."
    else:
        recommendation = "Review before removing"
        reason = "The local name and contents do not establish that it is disposable."
    return {
        "summary": explanation,
        "recommendation": recommendation,
        "reason": reason,
        "source": "Local rules (offline)",
    }
