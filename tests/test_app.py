from __future__ import annotations

import io
import json
from pathlib import Path

from openpyxl import Workbook
from pypdf import PdfWriter

from src.app import create_app


ROOT = Path(__file__).resolve().parents[1]


def create_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.read()


def scan_text_files():
    allowed_suffixes = {".md", ".py", ".html", ".txt", ".ps1", ".sh", ".example", ".json"}
    for path in ROOT.glob("*.md"):
        if path.is_file():
            yield path

    patterns = ["Dockerfile", "start_server.ps1", "start_server.sh", ".env.example"]
    for pattern in patterns:
        path = ROOT / pattern
        if path.exists():
            yield path

    for directory in ("src", "templates", "docs", "data", "config"):
        for path in (ROOT / directory).rglob("*"):
            if path.is_file() and path.suffix in allowed_suffixes:
                yield path


def test_root_renders_without_data(empty_client):
    response = empty_client.get("/")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "资管产品洞察协作台" in body
    assert "Asset Intel Workbench" in body
    assert "预置 Demo Case" in body
    assert "/api/" not in body
    assert "/workspace" in body


def test_healthcheck(empty_client):
    response = empty_client.get("/_internal/health")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["status"] == "ok"


def test_root_security_headers(empty_client):
    response = empty_client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"


def test_old_api_routes_return_404(client_with_data):
    routes = [
        ("/api/status", "get"),
        ("/api/signals", "get"),
        ("/api/history", "get"),
        ("/api/all_history", "get"),
        ("/api/spectrum", "get"),
        ("/api/toggle_simulation", "post"),
        ("/api/daily_report", "get"),
        ("/api/products", "get"),
        ("/api/analyze", "post"),
        ("/api/chat", "post"),
    ]
    for route, method in routes:
        response = getattr(client_with_data, method)(route)
        assert response.status_code == 404


def test_refresh_toggle_and_daily_report(client_with_data):
    refresh = client_with_data.post("/workspace", json={"action": "refresh"})
    refresh_payload = refresh.get_json()
    assert refresh.status_code == 200
    assert refresh_payload["has_data"] is True
    assert refresh_payload["summary"]["product_count"] == 2
    assert "competition_story" in refresh_payload
    assert "demo_cases" in refresh_payload
    assert "quality_metrics" in refresh_payload
    policy_module = next(item for item in refresh_payload["modules"] if item["key"] == "policy_analysis")
    policy_skill_labels = [item["label"] for item in policy_module["skills"]]
    assert "政策解读" in policy_skill_labels
    assert "风险与合规" in policy_skill_labels

    toggle = client_with_data.post("/workspace", json={"action": "toggle_simulation"})
    toggle_payload = toggle.get_json()
    assert toggle.status_code == 200
    assert toggle_payload["simulation"]["is_running"] is False

    report = client_with_data.post("/workspace", json={"action": "daily_report"})
    report_payload = report.get_json()
    assert report.status_code == 200
    assert report_payload["available"] is True
    assert report_payload["date"] == "2026-01-05"


def test_workspace_rejects_unsupported_action(client_with_data):
    response = client_with_data.post("/workspace", json={"action": "unknown"})
    payload = response.get_json()
    assert response.status_code == 400
    assert payload["error"] == "Unsupported action"


def test_chat_stream_works_with_fixture_data(client_with_data):
    response = client_with_data.post(
        "/workspace",
        data={
            "action": "chat",
            "message": "请提供产品快照：560001.SH",
            "active_module": "product_research",
        },
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert "产品快照" in body


def test_generate_report_from_uploaded_pdf(client_with_data):
    pdf_bytes = create_pdf_bytes()
    response = client_with_data.post(
        "/workspace",
        data={
            "action": "generate_report",
            "pdf_file": (io.BytesIO(pdf_bytes), "sample.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_demo_mode_bootstrap_and_load_case(demo_client):
    refresh = demo_client.post("/workspace", json={"action": "refresh"})
    payload = refresh.get_json()
    assert refresh.status_code == 200
    assert payload["mode"] == "demo"
    assert len(payload["demo_cases"]) == 3

    load_case = demo_client.post("/workspace", json={"action": "load_demo_case", "case_id": "policy_shock"})
    case_payload = load_case.get_json()
    assert load_case.status_code == 200
    assert case_payload["report_ready"] is True
    assert case_payload["outline_ready"] is True
    assert case_payload["active_module"] == "policy_analysis"
    assert "assistant_message" in case_payload
    assert case_payload["quality_metrics"]
    assert case_payload["trace_summary"]["skills"]


def test_trace_quality_and_outline_actions(demo_client):
    load_case = demo_client.post("/workspace", json={"action": "load_demo_case", "case_id": "market_volatility"})
    payload = load_case.get_json()
    session_id = payload["session_id"]

    trace = demo_client.post("/workspace", json={"action": "report_trace", "session_id": session_id})
    trace_payload = trace.get_json()
    assert trace.status_code == 200
    assert trace_payload["report_sections"]

    quality = demo_client.post("/workspace", json={"action": "quality_snapshot", "session_id": session_id})
    quality_payload = quality.get_json()
    assert quality.status_code == 200
    assert len(quality_payload) == 4

    outline = demo_client.post("/workspace", data={"action": "export_outline", "session_id": session_id})
    assert outline.status_code == 200
    assert outline.mimetype.startswith("text/markdown")


def test_invalid_upload_rejected(client_with_data):
    response = client_with_data.post(
        "/workspace",
        data={
            "action": "generate_report",
            "pdf_file": (io.BytesIO(b"hello"), "sample.txt"),
        },
        content_type="multipart/form-data",
    )
    payload = response.get_json()
    assert response.status_code == 400
    assert payload["error"] == "仅支持 PDF 文件。"


def test_policy_module_prompt_contains_skillbook(app_with_data):
    manager = app_with_data.config["MANAGER"]
    prompt = manager.build_system_prompt("policy_analysis")
    assert "政策解读" in prompt
    assert "风险与合规" in prompt
    assert "报告编审" in prompt


def test_custom_profile_supports_custom_labels_and_files(tmp_path):
    snapshot = [
        {
            "snapshot_date": "2026-02-03",
            "records": [
                {
                    "record_id": "EVT-001",
                    "record_name": "样例事件",
                    "created_on": "2025-09-01",
                    "listed_on": "2025-09-02",
                    "score": 10.5,
                    "activity": 7.2,
                    "delta": 1.3,
                    "benchmark_ref": "B-1",
                }
            ],
            "benchmarks": [
                {
                    "benchmark_id": "B-1",
                    "benchmark_name": "样例基准",
                    "baseline": 100.0,
                    "opening": 101.0,
                    "swing": 1.8,
                    "turnover": 88.0,
                }
            ],
        }
    ]
    (tmp_path / "events.json").write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["发布日期", "文档标题", "分类", "链接"])
    sheet.append(["2026-02-03", "关于样例事件的说明", "制度更新", "https://example.com/event"])
    workbook.save(tmp_path / "docs.xlsx")

    profile = {
        "workspace": {
            "app_name": "通用事件研判台",
            "panel_titles": {"catalog": "事件目录"},
            "module_overrides": {
                "product_research": {
                    "label": "事件研究",
                    "summary": "解释事件记录和基础事实。",
                    "prompt": "你是事件研究模块，负责解释记录事实。",
                }
            },
        },
        "files": {
            "market_snapshot": "events.json",
            "policy_catalog": "docs.xlsx",
        },
        "snapshot": {
            "date_field": "snapshot_date",
            "products_field": "records",
            "indices_field": "benchmarks",
            "product_fields": {
                "code": "record_id",
                "name": "record_name",
                "setup_date": "created_on",
                "list_date": "listed_on",
                "scale": "score",
                "volume": "activity",
                "inflow": "delta",
                "index_code": "benchmark_ref",
            },
            "index_fields": {
                "code": "benchmark_id",
                "name": "benchmark_name",
                "prev_close": "baseline",
                "open": "opening",
                "change": "swing",
                "volume": "turnover",
            },
        },
        "policy": {
            "columns": {
                "date": ["发布日期"],
                "title": ["文档标题"],
                "rank": ["分类"],
                "source": ["链接"],
            }
        },
    }
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")

    app = create_app(
        {
            "TESTING": True,
            "DATA_SOURCE_DIR": str(tmp_path),
            "DATA_PROFILE_PATH": str(profile_path),
        }
    )
    client = app.test_client()
    response = client.post("/workspace", json={"action": "refresh"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["app_name"] == "通用事件研判台"
    assert payload["workspace"]["panel_titles"]["catalog"] == "事件目录"
    assert payload["summary"]["product_count"] == 1
    assert payload["products"][0]["name"] == "样例事件"
    assert payload["modules"][0]["label"] == "事件研究"


def test_banned_source_terms_absent():
    banned = ["efund", "易方达", "小易", "智库", "promotionagent", "Rayne-X", "Antigravity"]
    for path in scan_text_files():
        content = path.read_text(encoding="utf-8")
        lowered = content.lower()
        for term in banned:
            assert term.lower() not in lowered, f"found banned term {term} in {path}"


def test_no_hardcoded_secret_pattern():
    for path in scan_text_files():
        content = path.read_text(encoding="utf-8")
        assert "sk-" not in content, f"found hardcoded secret pattern in {path}"
