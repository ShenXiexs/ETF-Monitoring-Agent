from __future__ import annotations

import re
from pathlib import Path

from src.prd_skills import get_skill_cards


ROOT = Path(__file__).resolve().parents[1]


def scan_text_files():
    allowed_suffixes = {".md", ".py", ".html", ".txt", ".ps1", ".sh", ".example", ".json", ".ini"}
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or ".venv" in path.parts or ".pytest_cache" in path.parts or "README_Ref" in path.parts:
            continue
        if path.is_file() and (path.suffix in allowed_suffixes or path.name in {"Dockerfile"}):
            yield path


def test_root_renders_prd_ide(client):
    response = client.get("/")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Flash of Insights：PRD IDE 需求交付引擎" in body
    assert "让PM跟工程师一样用上能够信息补全和自动联想的办公效率产品（跟用 IDE 一样）" in body
    assert "floating-buddy" in body
    assert "Competitive Gap Matrix" in body
    assert "MBTI Persona" in body
    assert "Next Edit Suggestion" in body
    assert "/workspace" in body
    assert "/api/" not in body


def test_healthcheck(client):
    response = client.get("/_internal/health")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["engine"] == "PRDDeliveryEngine"
    assert payload["knowledge_pack"]["template_count"] >= 8


def test_root_security_headers(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"


def test_refresh_payload_contains_challenge_fields(client):
    response = client.post("/workspace", json={"action": "refresh"})
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["workspace"]["slogan"] == "让PM跟工程师一样用上能够信息补全和自动联想的办公效率产品（跟用 IDE 一样）"
    assert payload["agent_mode"] == "reminder"
    assert payload["mascot_state"] == "peek"
    assert len(payload["persona_profiles"]) == 4
    assert payload["challenge_story"]["headline"] == "Flash of Insights：PRD Writing as an IDE"
    assert payload["flash_insight"]["headline"].startswith("Flash of Insight")
    assert len(payload["market_landscape"]) == 4
    assert len(payload["cross_page_assets"]) >= 4
    assert payload["knowledge_pack"]["next_edit_pattern_count"] >= 4
    assert payload["ghost_text"]
    assert payload["suggestion_kind"]
    assert payload["quality_metrics"]
    assert payload["delivery_trace"]


def test_skill_registry_uses_english_internal_names_and_chinese_display_labels(client):
    response = client.post("/workspace", json={"action": "refresh"})
    skills = response.get_json()["skills"]
    skill_names = [item["skill_name"] for item in skills]
    display_labels = [item["display_label"] for item in skills]
    assert "RequirementCompleter" in skill_names
    assert "RewriteEditor" in skill_names
    assert "AcceptanceCriteriaBuilder" in skill_names
    assert "需求补全" in display_labels
    assert "改写编辑" in display_labels
    assert all(item["skill_name"].isascii() for item in skills)


def test_persona_and_mode_keys_are_english_while_ui_copy_is_chinese(client):
    response = client.post("/workspace", json={"action": "refresh"})
    payload = response.get_json()
    persona_keys = [item["key"] for item in payload["persona_profiles"]]
    persona_labels = [item["display_label"] for item in payload["persona_profiles"]]
    mode_keys = [item["key"] for item in payload["agent_modes"]]
    assert persona_keys == ["INTJ_ARCHITECT", "ENTJ_COMMANDER", "INFJ_ADVOCATE", "ENFP_CAMPAIGNER"]
    assert mode_keys == ["REMINDER", "ASSISTANT"]
    assert all(key.isascii() and key.upper() == key for key in persona_keys + mode_keys)
    assert any(not label.isascii() for label in persona_labels)
    assert not payload["agent_modes"][0]["description"].isascii()


def test_direct_skill_cards_are_english_canonical():
    cards = get_skill_cards()
    assert cards[0]["skill_name"] == "StyleProfiler"
    assert "TraceExplainer" in [item["skill_name"] for item in cards]
    assert cards[-1]["skill_name"] == "RollbackManager"
    assert cards[0]["display_label"] == "风格画像"


def test_workspace_rejects_unsupported_action(client):
    response = client.post("/workspace", json={"action": "unknown"})
    payload = response.get_json()
    assert response.status_code == 400
    assert payload["error"] == "Unsupported action"


def test_old_api_routes_return_404(client):
    routes = [
        ("/api/status", "get"),
        ("/api/signals", "get"),
        ("/api/history", "get"),
        ("/api/chat", "post"),
    ]
    for route, method in routes:
        response = getattr(client, method)(route)
        assert response.status_code == 404


def test_load_prd_demo_returns_editor_artifacts(client):
    response = client.post("/workspace", json={"action": "load_prd_demo", "demo_id": "prd_ide"})
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["active_document"]["id"] == "prd_ide"
    assert "PRD IDE" in payload["document_text"]
    assert payload["ghost_text"]
    assert payload["evidence_refs"]
    assert payload["style_match"]["score"] >= 50
    assert payload["artifact_preview"]["readiness"] > 0


def test_inline_suggest_returns_next_missing_section(client):
    draft = "# Demo PRD\n\n## 背景\n新人写 PRD 缺少团队风格。\n\n## 目标\n提升需求交付效率。"
    response = client.post(
        "/workspace",
        json={"action": "inline_suggest", "current_text": draft, "cursor_position": len(draft)},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert "## 用户故事" in payload["ghost_text"]
    assert payload["suggestion_kind"] == "rewrite_then_complete"
    assert payload["inline_diff"]["type"] == "next_edit_rewrite"
    assert payload["cursor_target"]["type"] == "current_block"
    assert payload["evidence_refs"][0]["source_type"] in {"style_fingerprint", "delivery_rule"}
    assert payload["delivery_trace"][1]["skill_name"] == "RequirementCompleter"
    assert any(item["key"] == "acceptance" for item in payload["missing_sections"])


def test_next_edit_suggest_combines_tab_completion_and_rephrase(client):
    draft = "# PRD\n\n## 背景\n我们希望提升 PRD 写作效率"
    response = client.post(
        "/workspace",
        json={"action": "next_edit_suggest", "current_text": draft, "cursor_position": len(draft), "persona": "ENTJ_COMMANDER"},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["suggestion_kind"] == "rewrite_then_complete"
    assert payload["ghost_text"].startswith("\n\n## 目标")
    assert payload["rewrite_hint"]
    assert payload["next_edit_label"] == "先重写当前模糊句，再按 Tab 补下一段"
    assert payload["inline_diff"]["type"] == "next_edit_rewrite"
    assert payload["inline_diff"]["can_rollback"] is True
    assert payload["rollback_token"]
    assert "ENTJ 指挥官" in payload["inline_diff"]["after_text"]
    assert [item["skill_name"] for item in payload["delivery_trace"]][:3] == ["StyleProfiler", "RequirementCompleter", "RewriteEditor"]


def test_rewrite_selection_modes(client):
    selected = "系统需要更好地帮助用户写需求"
    response = client.post(
        "/workspace",
        json={
            "action": "rewrite_selection",
            "selected_text": selected,
            "current_text": f"# PRD\n\n{selected}",
            "mode": "convert to user story",
        },
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["mode"] == "convert_user_story"
    assert "作为目标用户" in payload["replacement_text"]
    assert payload["delivery_trace"][1]["skill_name"] == "RewriteEditor"


def test_review_prd_reports_missing_sections_and_risks(client):
    response = client.post(
        "/workspace",
        json={"action": "review_prd", "current_text": "# PRD\n\n## 背景\n只有一个想法。"},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["review_summary"]
    assert any(item["key"] == "acceptance" for item in payload["missing_sections"])
    assert any(item["title"] == "缺少可验收标准" for item in payload["risk_flags"])
    assert len(payload["quality_metrics"]) == 5


def test_generate_delivery_plan(client):
    response = client.post(
        "/workspace",
        json={"action": "generate_delivery_plan", "current_text": "# PRD\n\n## 背景\n需求评审返工很多。"},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["delivery_plan"]["title"] == "交付计划"
    assert len(payload["delivery_plan"]["phases"]) == 4
    assert payload["delivery_trace"][1]["skill_name"] == "TaskPlanner"


def test_quality_snapshot(client):
    response = client.post(
        "/workspace",
        json={"action": "quality_snapshot", "current_text": "# PRD\n\n## 背景\nA\n\n## 目标\nB"},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["quality_metrics"]
    assert payload["style_match"]["label"] == "团队 PRD 风格匹配"
    assert any(item["key"] == "acceptance" for item in payload["missing_sections"])


def test_switch_agent_mode(client):
    response = client.post("/workspace", json={"action": "switch_agent_mode", "agent_mode": "assistant"})
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["agent_mode"] == "assistant"
    assert payload["mode_key"] == "ASSISTANT"
    assert payload["mascot_state"] == "fly_out"


def test_assistant_command_supports_review_and_mbti(client):
    review = client.post(
        "/workspace",
        json={"action": "assistant_command", "command": "@review 请检查验收标准", "current_text": "# PRD\n\n## 背景\nA"},
    ).get_json()
    assert review["inline_diff"]["type"] == "inline_review"
    assert review["rollback_token"]
    assert review["delivery_trace"][1]["skill_name"] == "RiskReviewer"

    mbti = client.post(
        "/workspace",
        json={
            "action": "assistant_command",
            "command": "@mbti ENFP 帮我改写",
            "persona": "INTJ_ARCHITECT",
            "selected_text": "让新人更快写需求",
            "current_text": "# PRD\n\n让新人更快写需求",
        },
    ).get_json()
    assert mbti["persona_profile"]["key"] == "ENFP_CAMPAIGNER"
    assert "机会点" in mbti["replacement_text"]


def test_apply_persona_rewrite_differs_by_persona(client):
    base = {"action": "apply_persona_rewrite", "selected_text": "提升 PRD 写作效率", "current_text": "# PRD\n\n提升 PRD 写作效率"}
    intj = client.post("/workspace", json={**base, "persona": "INTJ_ARCHITECT"}).get_json()
    enfp = client.post("/workspace", json={**base, "persona": "ENFP_CAMPAIGNER"}).get_json()
    assert intj["persona_profile"]["key"] == "INTJ_ARCHITECT"
    assert enfp["persona_profile"]["key"] == "ENFP_CAMPAIGNER"
    assert intj["replacement_text"] != enfp["replacement_text"]
    assert intj["inline_diff"]["can_rollback"] is True


def test_inline_review_and_rollback(client):
    current_text = "# PRD\n\n## 背景\n只有一个想法。"
    review_response = client.post("/workspace", json={"action": "inline_review", "current_text": current_text})
    review = review_response.get_json()
    assert review_response.status_code == 200
    assert review["inline_diff"]["type"] == "inline_review"
    assert review["rollback_token"]

    rollback_response = client.post(
        "/workspace",
        json={"action": "rollback_suggestion", "rollback_token": review["rollback_token"], "current_text": review["inline_diff"]["after_text"]},
    )
    rollback = rollback_response.get_json()
    assert rollback_response.status_code == 200
    assert rollback["rollback_status"] == "restored"
    assert rollback["restored_text"] == current_text


def test_reminder_snapshot(client):
    response = client.post("/workspace", json={"action": "reminder_snapshot", "current_text": "# PRD", "idle_seconds": 120})
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["agent_mode"] == "reminder"
    assert payload["reminder_cards"]
    assert any(item["trigger"] in {"idle", "missing_acceptance", "empty_page"} for item in payload["reminder_cards"])


def test_ref_assets_route(client):
    response = client.get("/assets/ref/logo2.png")
    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_export_prd_markdown(client):
    response = client.post(
        "/workspace",
        json={
            "action": "export_prd",
            "current_text": "# PRD IDE\n\n## 背景\n团队需要 Cursor 式 PRD 写作体验。",
        },
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.mimetype == "text/markdown"
    assert "AI Work Buddy 评审摘要" in body
    assert "让PM跟工程师一样用上能够信息补全和自动联想的办公效率产品（跟用 IDE 一样）" in body


def test_no_hardcoded_secret_pattern():
    secret_pattern = re.compile("s" + "k-" + r"[A-Za-z0-9]{20,}")
    for path in scan_text_files():
        content = path.read_text(encoding="utf-8")
        assert not secret_pattern.search(content), f"found hardcoded secret pattern in {path}"
