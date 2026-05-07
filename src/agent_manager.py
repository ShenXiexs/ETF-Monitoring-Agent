from __future__ import annotations

try:
    from .prd_engine import PRDDeliveryEngine
except ImportError:
    from prd_engine import PRDDeliveryEngine


MODULES = [
    {
        "key": "doc_as_ide_editor",
        "label": "doc-as-IDE Editor",
        "summary": "doc-as-IDE surface for Tab completion, style rephrase, review, reminder, and delivery planning.",
    }
]


class PRDWorkbenchManager(PRDDeliveryEngine):
    """Compatibility wrapper for older manager-style imports."""


__all__ = ["MODULES", "PRDWorkbenchManager", "PRDDeliveryEngine"]
