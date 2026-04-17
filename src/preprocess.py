from __future__ import annotations

import argparse
import json
from pathlib import Path

from openpyxl import load_workbook


def validate_snapshot(data_dir: Path) -> dict:
    snapshot_path = data_dir / "market_snapshot.json"
    policy_path = data_dir / "policy_catalog.xlsx"

    report = {
        "snapshot_exists": snapshot_path.exists(),
        "policy_exists": policy_path.exists(),
        "dates": 0,
        "products": 0,
        "indices": 0,
        "policy_rows": 0,
    }

    if snapshot_path.exists():
        raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            report["dates"] = len(raw)
            for payload in raw.values():
                if not isinstance(payload, dict):
                    continue
                report["products"] += len(payload.get("products", []))
                indices = payload.get("indices", {})
                if isinstance(indices, dict):
                    report["indices"] += len(indices)
                elif isinstance(indices, list):
                    report["indices"] += len(indices)

    if policy_path.exists():
        workbook = load_workbook(policy_path, data_only=True, read_only=True)
        sheet = workbook.active
        report["policy_rows"] = max(0, sheet.max_row - 1)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an external data directory.")
    parser.add_argument("data_dir", type=Path, help="Directory containing market_snapshot.json and policy_catalog.xlsx")
    args = parser.parse_args()
    report = validate_snapshot(args.data_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

