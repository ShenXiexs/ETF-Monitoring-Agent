from __future__ import annotations

from typing import Dict, Iterable, List


class LocalKnowledgeSearch:
    """Deterministic keyword search over seeded PRD knowledge entries."""

    def __init__(self, entries: Iterable[dict] | None = None) -> None:
        self.entries = list(entries or [])

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        query_terms = self._terms(query)
        ranked = []
        for entry in self.entries:
            text = " ".join(str(value) for value in entry.values())
            score = len(query_terms.intersection(self._terms(text)))
            if score:
                ranked.append((score, entry))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [{**entry, "score": score} for score, entry in ranked[:top_k]]

    def add_entries(self, entries: Iterable[dict]) -> None:
        self.entries.extend(entries)

    def reset(self) -> None:
        self.entries = []

    def _terms(self, text: str) -> set[str]:
        normalized = "".join(char.lower() if char.isalnum() else " " for char in text or "")
        return {item for item in normalized.split() if item}


def build_entries_from_pack(pack: Dict) -> List[dict]:
    entries: List[dict] = []
    for section in ("style_fingerprints", "glossary", "delivery_rules"):
        for item in pack.get(section, []):
            entries.append({"source_type": section, **item})
    for key, item in pack.get("section_templates", {}).items():
        entries.append({"source_type": "section_template", "id": key, **item})
    return entries
