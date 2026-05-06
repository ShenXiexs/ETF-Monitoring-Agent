from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List


REQUIRED_TOP_LEVEL_KEYS = [
    "workspace",
    "challenge_story",
    "flash_insight",
    "market_landscape",
    "style_fingerprints",
    "glossary",
    "delivery_rules",
    "section_templates",
    "demo_documents",
    "rewrite_modes",
    "next_edit_patterns",
    "cross_page_assets",
    "writing_journey_states",
    "agent_modes",
    "persona_profiles",
    "mascot_assets",
    "assistant_commands",
    "reminder_rules",
    "pet_state_catalog",
    "writing_radar_rules",
    "pet_design_refs",
    "rollback_policy",
]


REQUIRED_SECTION_KEYS = [
    "background",
    "goal",
    "user_story",
    "scope",
    "non_goals",
    "flow",
    "requirements",
    "acceptance",
    "metrics",
    "risks",
    "rollout",
]


def validate_knowledge_pack(path: Path) -> dict:
    report = {
        "path": str(path),
        "exists": path.exists(),
        "ready": False,
        "missing_top_level_keys": [],
        "missing_section_templates": [],
        "duplicate_evidence_ids": [],
        "demo_count": 0,
        "rule_count": 0,
    }
    if not path.exists():
        return report

    payload = json.loads(path.read_text(encoding="utf-8"))
    report["missing_top_level_keys"] = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in payload]
    templates = payload.get("section_templates", {})
    report["missing_section_templates"] = [key for key in REQUIRED_SECTION_KEYS if key not in templates]
    evidence_ids: List[str] = []
    for section in ("style_fingerprints", "glossary", "delivery_rules"):
        for item in payload.get(section, []):
            item_id = item.get("id")
            if item_id:
                evidence_ids.append(item_id)
    report["duplicate_evidence_ids"] = sorted({item for item in evidence_ids if evidence_ids.count(item) > 1})
    report["demo_count"] = len(payload.get("demo_documents", []))
    report["rule_count"] = len(payload.get("delivery_rules", []))
    report["ready"] = (
        not report["missing_top_level_keys"]
        and not report["missing_section_templates"]
        and not report["duplicate_evidence_ids"]
        and report["demo_count"] > 0
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a PRD IDE knowledge pack JSON file.")
    parser.add_argument("path", type=Path, help="Path to prd_knowledge_pack.json")
    args = parser.parse_args()
    print(json.dumps(validate_knowledge_pack(args.path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
