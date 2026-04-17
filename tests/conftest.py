from __future__ import annotations

import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from src.app import create_app


def write_fixture_data(directory: Path) -> None:
    snapshot = {
        "2026-01-05": {
            "products": [
                {
                    "code": "560001.SH",
                    "name": "示例产品A",
                    "setup_date": "2024-01-05",
                    "list_date": "2024-01-12",
                    "scale": 18.5,
                    "volume": 6.2,
                    "inflow": 1.8,
                    "index_code": "000001.SH",
                },
                {
                    "code": "560002.SH",
                    "name": "示例产品B",
                    "setup_date": "2024-06-18",
                    "list_date": "2024-06-25",
                    "scale": 22.1,
                    "volume": 8.4,
                    "inflow": 2.6,
                    "index_code": "399001.SZ",
                },
            ],
            "indices": {
                "000001.SH": {
                    "name": "示例指数一号",
                    "prev_close": 3200.0,
                    "open": 3220.0,
                    "change": 1.8,
                    "volume": 986.4,
                },
                "399001.SZ": {
                    "name": "示例指数二号",
                    "prev_close": 2400.0,
                    "open": 2370.0,
                    "change": -1.6,
                    "volume": 624.2,
                },
            },
        },
        "2026-01-06": {
            "products": [
                {
                    "code": "560001.SH",
                    "name": "示例产品A",
                    "setup_date": "2024-01-05",
                    "list_date": "2024-01-12",
                    "scale": 19.0,
                    "volume": 6.5,
                    "inflow": 1.1,
                    "index_code": "000001.SH",
                },
                {
                    "code": "560002.SH",
                    "name": "示例产品B",
                    "setup_date": "2024-06-18",
                    "list_date": "2024-06-25",
                    "scale": 22.8,
                    "volume": 8.0,
                    "inflow": 2.2,
                    "index_code": "399001.SZ",
                },
            ],
            "indices": {
                "000001.SH": {
                    "name": "示例指数一号",
                    "prev_close": 3220.0,
                    "open": 3235.0,
                    "change": 1.3,
                    "volume": 1020.0,
                }
            },
        },
    }
    (directory / "market_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["公告日期", "标题", "法律位阶", "来源"])
    sheet.append(["2026-01-05", "关于示例披露流程的通知", "行业规定", "https://example.com/policy"])
    workbook.save(directory / "policy_catalog.xlsx")


@pytest.fixture
def empty_app():
    app = create_app({"TESTING": True, "DATA_SOURCE_DIR": None})
    yield app


@pytest.fixture
def app_with_data(tmp_path):
    write_fixture_data(tmp_path)
    app = create_app({"TESTING": True, "DATA_SOURCE_DIR": str(tmp_path)})
    yield app


@pytest.fixture
def empty_client(empty_app):
    return empty_app.test_client()


@pytest.fixture
def client_with_data(app_with_data):
    return app_with_data.test_client()

