from __future__ import annotations

try:
    from .prd_engine import PRDDeliveryEngine
except ImportError:
    from prd_engine import PRDDeliveryEngine


MODULES = [
    {
        "key": "prd_editor",
        "label": "PRD Editor",
        "summary": "Standalone PRD IDE surface for Tab completion, rewrite, review, and delivery planning.",
    }
]


class PRDWorkbenchManager(PRDDeliveryEngine):
    """Compatibility wrapper for older manager-style imports."""


__all__ = ["MODULES", "PRDWorkbenchManager", "PRDDeliveryEngine"]
