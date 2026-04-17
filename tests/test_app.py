from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfWriter


ROOT = Path(__file__).resolve().parents[1]


def create_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.read()


def scan_text_files():
    allowed_suffixes = {".md", ".py", ".html", ".txt", ".ps1", ".example"}
    patterns = ["README.md", "Dockerfile", "start_server.ps1", ".env.example"]
    for pattern in patterns:
        path = ROOT / pattern
        if path.exists():
            yield path

    for directory in ("src", "templates", "docs", "data"):
        for path in (ROOT / directory).rglob("*"):
            if path.is_file() and path.suffix in allowed_suffixes:
                yield path


def test_root_renders_without_data(empty_client):
    response = empty_client.get("/")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "资管产品洞察协作台" in body
    assert "政策解读" in body
    assert "/api/" not in body
    assert "/workspace" in body


def test_healthcheck(empty_client):
    response = empty_client.get("/_internal/health")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["status"] == "ok"


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


def test_policy_module_prompt_contains_skillbook(app_with_data):
    manager = app_with_data.config["MANAGER"]
    prompt = manager.build_system_prompt("policy_analysis")
    assert "政策解读" in prompt
    assert "风险与合规" in prompt
    assert "报告编审" in prompt


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
