from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    from .prd_skills import PRD_IDE_WORKFLOW, build_skillbook, get_skill_cards
except ImportError:
    from prd_skills import PRD_IDE_WORKFLOW, build_skillbook, get_skill_cards


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_KNOWLEDGE_PACK = BASE_DIR / "data" / "prd_knowledge_pack.json"


REQUIRED_SECTIONS = [
    ("background", "背景", ["背景", "问题", "现状"]),
    ("goal", "目标", ["目标", "成功标准"]),
    ("user_story", "用户故事", ["用户故事", "用户与场景", "用户场景"]),
    ("scope", "范围", ["范围", "本期范围", "in scope"]),
    ("non_goals", "非目标", ["非目标", "不做", "out of scope"]),
    ("flow", "关键流程", ["关键流程", "流程", "用户路径"]),
    ("requirements", "功能需求", ["功能需求", "需求列表", "能力"]),
    ("acceptance", "验收标准", ["验收标准", "验收", "Given", "When", "Then"]),
    ("metrics", "指标", ["指标", "度量", "北极星", "成功指标"]),
    ("risks", "风险与边界", ["风险", "边界", "依赖"]),
    ("rollout", "发布计划", ["发布计划", "上线计划", "灰度", "rollout"]),
]


REWRITE_ALIASES = {
    "make concise": "make_concise",
    "make_concise": "make_concise",
    "concise": "make_concise",
    "压缩表达": "make_concise",
    "make formal": "make_formal",
    "make_formal": "make_formal",
    "formal": "make_formal",
    "正式化": "make_formal",
    "convert to user story": "convert_user_story",
    "convert_user_story": "convert_user_story",
    "user story": "convert_user_story",
    "转成用户故事": "convert_user_story",
    "add acceptance criteria": "add_acceptance_criteria",
    "add_acceptance_criteria": "add_acceptance_criteria",
    "acceptance": "add_acceptance_criteria",
    "补充验收标准": "add_acceptance_criteria",
    "clarify ambiguity": "clarify_ambiguity",
    "clarify_ambiguity": "clarify_ambiguity",
    "clarify": "clarify_ambiguity",
    "澄清歧义": "clarify_ambiguity",
    "turn into delivery tasks": "turn_into_delivery_tasks",
    "turn_into_delivery_tasks": "turn_into_delivery_tasks",
    "tasks": "turn_into_delivery_tasks",
    "转成交付任务": "turn_into_delivery_tasks",
}


@dataclass(frozen=True)
class SectionState:
    key: str
    label: str
    present: bool


class PRDDeliveryEngine:
    def __init__(self, knowledge_pack_path: Optional[str] = None) -> None:
        configured_path = knowledge_pack_path or os.getenv("PRD_KNOWLEDGE_PACK_PATH", "").strip()
        self.knowledge_pack_path = Path(configured_path).expanduser() if configured_path else DEFAULT_KNOWLEDGE_PACK
        self.base_dir = BASE_DIR
        self.pack = self._load_knowledge_pack()
        self.skills = get_skill_cards(PRD_IDE_WORKFLOW)
        self.rollback_store: Dict[str, dict] = {}

    def _load_knowledge_pack(self) -> dict:
        if self.knowledge_pack_path.exists():
            return json.loads(self.knowledge_pack_path.read_text(encoding="utf-8"))
        return json.loads(DEFAULT_KNOWLEDGE_PACK.read_text(encoding="utf-8"))

    def get_bootstrap_state(self) -> dict:
        demo = self.default_demo_document()
        review = self.review_prd(demo["seed_text"])
        suggestion = self.inline_suggest(demo["seed_text"])
        reminder = self.reminder_snapshot(demo["seed_text"], idle_seconds=0)
        return {
            "app_name": self.pack["workspace"]["app_name"],
            "workspace": self.pack["workspace"],
            "challenge_story": self.pack["challenge_story"],
            "flash_insight": self.pack.get("flash_insight", {}),
            "market_landscape": self.pack.get("market_landscape", []),
            "next_edit_patterns": self.pack.get("next_edit_patterns", []),
            "cross_page_assets": self.pack.get("cross_page_assets", []),
            "writing_journey_states": self.pack.get("writing_journey_states", []),
            "pet_state_catalog": self.pack.get("pet_state_catalog", []),
            "writing_radar_rules": self.pack.get("writing_radar_rules", []),
            "pet_design_refs": self.pack.get("pet_design_refs", []),
            "skills": self.skills,
            "skillbook": build_skillbook(),
            "knowledge_pack": self.knowledge_pack_summary(),
            "demo_documents": self.pack.get("demo_documents", []),
            "rewrite_modes": self.pack.get("rewrite_modes", []),
            "agent_modes": self.pack.get("agent_modes", []),
            "agent_mode": "reminder",
            "mode_key": "REMINDER",
            "mascot_state": "peek",
            "mascot_assets": self.pack.get("mascot_assets", {}),
            "assistant_commands": self.pack.get("assistant_commands", []),
            "persona_profiles": self.pack.get("persona_profiles", []),
            "persona_profile": self.get_persona_profile("INTJ_ARCHITECT"),
            "emotion_state": reminder["emotion_state"],
            "reminder_cards": reminder["reminder_cards"],
            "pet_state": reminder["pet_state"],
            "active_journey_state": reminder["active_journey_state"],
            "pet_profile": reminder["pet_profile"],
            "pet_bubble": reminder["pet_bubble"],
            "radar_cards": reminder["radar_cards"],
            "milestone_cards": reminder["milestone_cards"],
            "active_document": demo,
            "document_text": demo["seed_text"],
            "ghost_text": suggestion["ghost_text"],
            "evidence_refs": suggestion["evidence_refs"],
            "style_match": suggestion["style_match"],
            "quality_metrics": review["quality_metrics"],
            "delivery_trace": suggestion["delivery_trace"],
            "missing_sections": review["missing_sections"],
            "risk_flags": review["risk_flags"],
            "suggestion_kind": suggestion.get("suggestion_kind"),
            "rewrite_hint": suggestion.get("rewrite_hint"),
            "cursor_target": suggestion.get("cursor_target"),
            "next_edit_label": suggestion.get("next_edit_label"),
            "inline_diff": suggestion.get("inline_diff"),
            "rollback_token": suggestion.get("rollback_token"),
            "artifact_preview": self.build_artifact_preview(demo["seed_text"]),
            "timestamp": time.time(),
        }

    def knowledge_pack_summary(self) -> dict:
        return {
            "path": str(self.knowledge_pack_path),
            "style_count": len(self.pack.get("style_fingerprints", [])),
            "glossary_count": len(self.pack.get("glossary", [])),
            "rule_count": len(self.pack.get("delivery_rules", [])),
            "template_count": len(self.pack.get("section_templates", {})),
            "demo_count": len(self.pack.get("demo_documents", [])),
            "persona_count": len(self.pack.get("persona_profiles", [])),
            "reminder_rule_count": len(self.pack.get("reminder_rules", [])),
            "market_category_count": len(self.pack.get("market_landscape", [])),
            "asset_count": len(self.pack.get("cross_page_assets", [])),
            "next_edit_pattern_count": len(self.pack.get("next_edit_patterns", [])),
            "pet_state_count": len(self.pack.get("pet_state_catalog", [])),
            "radar_rule_count": len(self.pack.get("writing_radar_rules", [])),
            "styles": self.pack.get("style_fingerprints", []),
            "glossary": self.pack.get("glossary", []),
            "delivery_rules": self.pack.get("delivery_rules", []),
        }

    def default_demo_document(self) -> dict:
        demos = self.pack.get("demo_documents", [])
        if demos:
            return demos[0]
        return {"id": "empty_prd", "title": "空白 PRD", "category": "Demo", "summary": "从空白开始体验 Tab 联想。", "seed_text": "# 空白 PRD\n\n"}

    def load_prd_demo(self, demo_id: str | None = None) -> dict:
        demos = self.pack.get("demo_documents", [])
        selected = next((item for item in demos if item.get("id") == demo_id), None) or self.default_demo_document()
        review = self.review_prd(selected["seed_text"])
        suggestion = self.inline_suggest(selected["seed_text"])
        reminder = self.reminder_snapshot(selected["seed_text"], idle_seconds=0)
        return {
            "active_document": selected,
            "document_text": selected["seed_text"],
            "ghost_text": suggestion["ghost_text"],
            "evidence_refs": suggestion["evidence_refs"],
            "style_match": suggestion["style_match"],
            "quality_metrics": review["quality_metrics"],
            "delivery_trace": suggestion["delivery_trace"],
            "missing_sections": review["missing_sections"],
            "risk_flags": review["risk_flags"],
            "reminder_cards": reminder["reminder_cards"],
            "mascot_state": reminder["mascot_state"],
            "emotion_state": reminder["emotion_state"],
            "pet_state": reminder["pet_state"],
            "active_journey_state": reminder["active_journey_state"],
            "pet_profile": reminder["pet_profile"],
            "pet_bubble": reminder["pet_bubble"],
            "radar_cards": reminder["radar_cards"],
            "milestone_cards": reminder["milestone_cards"],
            "suggestion_kind": suggestion.get("suggestion_kind"),
            "rewrite_hint": suggestion.get("rewrite_hint"),
            "cursor_target": suggestion.get("cursor_target"),
            "next_edit_label": suggestion.get("next_edit_label"),
            "inline_diff": suggestion.get("inline_diff"),
            "rollback_token": suggestion.get("rollback_token"),
            "artifact_preview": self.build_artifact_preview(selected["seed_text"]),
            "assistant_message": f"已加载《{selected['title']}》。按 Tab 可以接受下一段联想，按 Cmd/Ctrl+K 可以改写选区。",
        }

    def switch_agent_mode(self, agent_mode: str = "reminder") -> dict:
        mode_key = self._normalize_agent_mode(agent_mode)
        pet_state = "FIRST_LINE_NUDGE" if mode_key == "ASSISTANT" else "IDLE_BIRDHOUSE"
        pet_profile = self._pet_profile(pet_state)
        mascot_state = pet_profile.get("mascot_state", "fly_out" if mode_key == "ASSISTANT" else "peek")
        return {
            "agent_mode": mode_key.lower(),
            "mode_key": mode_key,
            "mascot_state": mascot_state,
            "emotion_state": pet_profile.get("emotion_state", "ready" if mode_key == "ASSISTANT" else "calm"),
            "pet_state": pet_state,
            "active_journey_state": self._active_journey_state(pet_state),
            "pet_profile": pet_profile,
            "pet_bubble": pet_profile.get("bubble", ""),
            "assistant_message": "Assistant Mode 已开启，小鸟会主动飞到字里行间帮你补齐、评审和改写。" if mode_key == "ASSISTANT" else "Reminder Mode 已开启，小鸟会停在鸟屋里，只在关键节点轻提醒。",
        }

    def next_edit_suggest(self, current_text: str, cursor_position: Optional[int] = None, persona: str = "INTJ_ARCHITECT") -> dict:
        return self._build_next_edit_suggestion(current_text, cursor_position=cursor_position, persona=persona, action="next_edit_suggest")

    def inline_suggest(self, current_text: str, cursor_position: Optional[int] = None) -> dict:
        return self._build_next_edit_suggestion(current_text, cursor_position=cursor_position, action="inline_suggest")

    def _build_next_edit_suggestion(self, current_text: str, cursor_position: Optional[int] = None, persona: str = "INTJ_ARCHITECT", action: str = "next_edit_suggest") -> dict:
        source_text = current_text[:cursor_position] if isinstance(cursor_position, int) and cursor_position >= 0 else current_text
        section_states = self.section_states(source_text)
        next_missing = next((item for item in section_states if not item.present), None)
        if next_missing:
            template = self.pack.get("section_templates", {}).get(next_missing.key, {})
            ghost_text = template.get("ghost_text", self._fallback_section_text(next_missing.key, next_missing.label))
        else:
            ghost_text = self._polish_next_step_text(source_text)

        last_block = self._extract_last_editable_block(source_text)
        rewrite_text = self._next_edit_rewrite(last_block, persona) if self._needs_process_rewrite(last_block, source_text) else ""
        after_text = self._replace_last_block(current_text, last_block, rewrite_text) if rewrite_text else current_text
        inline_diff = self._build_inline_diff(current_text, after_text, "next_edit_rewrite", "Next Edit Rephrase") if rewrite_text and after_text != current_text else None
        rollback_token = self._store_rollback(current_text, after_text, "next_edit_suggest") if inline_diff else None
        evidence_refs = self._default_evidence_refs(["style-brief-first", "rule-next-edit-before-generation", "rule-reversible-diff", "rule-observable-criteria"])
        suggestion_kind = self._suggestion_kind(next_missing, bool(inline_diff))
        return {
            "ghost_text": self._ensure_leading_blank_line(ghost_text),
            "suggestion_kind": suggestion_kind,
            "next_edit_label": self._next_edit_label(suggestion_kind),
            "rewrite_hint": self._rewrite_hint(last_block, rewrite_text, next_missing),
            "cursor_target": self._cursor_target(source_text, next_missing, bool(inline_diff)),
            "inline_diff": inline_diff,
            "rollback_token": rollback_token,
            "evidence_refs": evidence_refs,
            "style_match": self.style_match(source_text),
            "agent_mode": "assistant",
            "mascot_state": "working",
            "emotion_state": "focused",
            "journey_state": "NEXT_EDIT_WORKING",
            "pet_state": "NEXT_EDIT_WORKING",
            "active_journey_state": "NEXT_EDIT_WORKING",
            "pet_profile": self._pet_profile("NEXT_EDIT_WORKING"),
            "pet_bubble": self._pet_profile("NEXT_EDIT_WORKING").get("bubble", ""),
            "radar_cards": self.writing_radar_cards(source_text),
            "milestone_cards": self._milestone_cards(source_text, 0),
            "delivery_trace": self._next_edit_trace(action, suggestion_kind, bool(inline_diff), evidence_refs),
            "missing_sections": self.missing_sections(source_text),
            "risk_flags": self.risk_flags(source_text),
            "quality_metrics": self.quality_metrics(source_text),
        }

    def rewrite_selection(self, selected_text: str, mode: str = "make_concise", full_text: str = "") -> dict:
        normalized_mode = REWRITE_ALIASES.get((mode or "").strip().lower(), "make_concise")
        source = (selected_text or "").strip() or "当前需求描述需要补充对象、触发条件、边界和验收口径。"
        replacement = self._rewrite_text(source, normalized_mode)
        evidence_refs = self._default_evidence_refs(["style-delivery-ready", "rule-observable-criteria", "rule-risk-boundary"])
        merged_text = full_text.replace(selected_text, replacement, 1) if selected_text and selected_text in full_text else full_text
        evaluated_text = merged_text or replacement
        return {
            "mode": normalized_mode,
            "replacement_text": replacement,
            "evidence_refs": evidence_refs,
            "style_match": self.style_match(evaluated_text),
            "delivery_trace": self.delivery_trace("rewrite_selection", "RewriteEditor", "改写编辑", f"按 {normalized_mode} 模式改写选区，并保留 PRD 交付语境。", evidence_refs),
            "missing_sections": self.missing_sections(evaluated_text),
            "risk_flags": self.risk_flags(evaluated_text),
            "quality_metrics": self.quality_metrics(evaluated_text),
        }

    def apply_persona_rewrite(self, persona: str, selected_text: str, current_text: str = "") -> dict:
        profile = self.get_persona_profile(persona)
        source = (selected_text or "").strip() or self._extract_last_paragraph(current_text) or "当前需求需要补充可交付表达。"
        replacement = self._persona_rewrite_text(source, profile)
        after_text = current_text.replace(selected_text, replacement, 1) if selected_text and selected_text in current_text else (current_text.rstrip() + "\n\n" + replacement).strip()
        token = self._store_rollback(current_text, after_text, "apply_persona_rewrite")
        evidence_refs = self._default_evidence_refs(["style-delivery-ready", "rule-owner-scope"])
        return {
            "persona_profile": profile,
            "replacement_text": replacement,
            "inline_diff": self._build_inline_diff(current_text, after_text, "persona_rewrite", f"{profile['display_label']} 风格改写"),
            "rollback_token": token,
            "agent_mode": "assistant",
            "mascot_state": "working",
            "emotion_state": "focused",
            "pet_state": "NEXT_EDIT_WORKING",
            "active_journey_state": "NEXT_EDIT_WORKING",
            "pet_profile": self._pet_profile("NEXT_EDIT_WORKING"),
            "pet_bubble": f"正在按 {profile['display_label']} 写作人格生成可回滚 diff。",
            "evidence_refs": evidence_refs,
            "delivery_trace": self.delivery_trace("apply_persona_rewrite", "PersonaStylist", "人格风格", f"使用 {profile['key']} 写作人格调整选区语气、结构和风险偏好。", evidence_refs),
            "quality_metrics": self.quality_metrics(after_text),
            "missing_sections": self.missing_sections(after_text),
            "risk_flags": self.risk_flags(after_text),
        }

    def assistant_command(self, command: str, current_text: str = "", selected_text: str = "", persona: str = "INTJ_ARCHITECT") -> dict:
        command_text = (command or "").strip()
        lowered = command_text.lower()
        if "@review" in lowered:
            result = self.inline_review(current_text)
            result["assistant_message"] = "已按 @review 生成 inline review，可接受 diff 或用 token 回滚。"
            return result
        if "@mbti" in lowered:
            persona_key = self._extract_persona_key(command_text) or persona
            result = self.apply_persona_rewrite(persona_key, selected_text, current_text)
            result["assistant_message"] = f"已按 {result['persona_profile']['display_label']} 写作人格改写。"
            return result
        if "@expand" in lowered:
            return self.rewrite_selection(selected_text or self._extract_last_paragraph(current_text), "add_acceptance_criteria", current_text)
        result = self.next_edit_suggest(current_text, persona=persona)
        result.update(self.switch_agent_mode("assistant"))
        result["assistant_message"] = "Assistant 已就绪。你可以输入 @review、@mbti 或直接按 Tab 接受文内补齐。"
        return result

    def inline_review(self, current_text: str) -> dict:
        review = self.review_prd(current_text)
        patch_lines = ["", "## Inline Review 建议"]
        if review["missing_sections"]:
            patch_lines.append("- 建议补齐章节：" + "、".join(item["label"] for item in review["missing_sections"][:5]))
        if review["risk_flags"]:
            patch_lines.extend(f"- {flag['title']}：{flag['detail']}" for flag in review["risk_flags"][:3])
        patch_lines.append("- 回滚策略：接受该 review 后仍可通过 rollback token 恢复当前版本。")
        after_text = (current_text.rstrip() + "\n" + "\n".join(patch_lines)).strip()
        token = self._store_rollback(current_text, after_text, "inline_review")
        evidence_refs = self._default_evidence_refs(["rule-observable-criteria", "rule-risk-boundary", "rule-delivery-checkpoints"])
        pet_state = "REVIEW_WARNING" if review["risk_flags"] else "NEXT_EDIT_WORKING"
        pet_profile = self._pet_profile(pet_state)
        return {
            **review,
            "inline_diff": self._build_inline_diff(current_text, after_text, "inline_review", "Work Buddy Inline Review"),
            "rollback_token": token,
            "agent_mode": "assistant",
            "mascot_state": pet_profile.get("mascot_state", "warning" if review["risk_flags"] else "working"),
            "emotion_state": pet_profile.get("emotion_state", "alert" if review["risk_flags"] else "focused"),
            "pet_state": pet_state,
            "active_journey_state": self._active_journey_state(pet_state),
            "pet_profile": pet_profile,
            "pet_bubble": pet_profile.get("bubble", ""),
            "radar_cards": self.writing_radar_cards(current_text),
            "milestone_cards": self._milestone_cards(current_text, 0),
            "evidence_refs": evidence_refs,
            "delivery_trace": self.delivery_trace("inline_review", "RiskReviewer", "风险评审", "生成可接受、可拒绝、可回滚的 inline review diff。", evidence_refs),
        }

    def rollback_suggestion(self, rollback_token: str, current_text: str = "") -> dict:
        entry = self.rollback_store.get((rollback_token or "").strip())
        if not entry:
            return {
                "restored_text": current_text,
                "rollback_token": rollback_token,
                "rollback_status": "missing",
                "assistant_message": "没有找到可回滚状态，当前内容保持不变。",
                "mascot_state": "warning",
                "emotion_state": "alert",
                "pet_state": "REVIEW_WARNING",
                "active_journey_state": "REVIEW_WARNING",
                "pet_profile": self._pet_profile("REVIEW_WARNING"),
                "pet_bubble": "没有找到可回滚状态，建议先保留当前版本。",
            }
        restored_text = entry["before_text"]
        return {
            "restored_text": restored_text,
            "rollback_token": rollback_token,
            "rollback_status": "restored",
            "assistant_message": "已恢复到接受 AI 建议前的版本。",
            "inline_diff": self._build_inline_diff(current_text, restored_text, "rollback", "Rollback restored previous state"),
            "quality_metrics": self.quality_metrics(restored_text),
            "missing_sections": self.missing_sections(restored_text),
            "risk_flags": self.risk_flags(restored_text),
            "mascot_state": "celebrate",
            "emotion_state": "relieved",
            "pet_state": "RESULT_READY",
            "active_journey_state": "DELIVER_READY",
            "pet_profile": self._pet_profile("RESULT_READY"),
            "pet_bubble": "已经回滚到 AI 建议前版本，当前状态安全。",
        }

    def reminder_snapshot(self, current_text: str, idle_seconds: int | float = 0) -> dict:
        stripped = (current_text or "").strip()
        cards: List[dict] = []
        rules = {item["trigger"]: item for item in self.pack.get("reminder_rules", [])}
        if len(stripped) < int(rules.get("empty_page", {}).get("threshold", 20)):
            cards.append(self._reminder_card(rules.get("empty_page"), "empty_page"))
        if float(idle_seconds or 0) >= float(rules.get("idle", {}).get("threshold", 90)):
            cards.append(self._reminder_card(rules.get("idle"), "idle"))
        if any(item["key"] == "acceptance" for item in self.missing_sections(current_text)):
            cards.append(self._reminder_card(rules.get("missing_acceptance"), "missing_acceptance"))
        if max([len(part) for part in re.split(r"\n\s*\n", current_text or "")] or [0]) >= int(rules.get("long_section", {}).get("threshold", 520)):
            cards.append(self._reminder_card(rules.get("long_section"), "long_section"))
        if not cards and self.build_artifact_preview(current_text)["readiness"] >= 70:
            cards.append(self._reminder_card(rules.get("deadline"), "deadline"))
        cards = cards[:3]
        radar_cards = self.writing_radar_cards(current_text)
        milestone_cards = self._milestone_cards(current_text, idle_seconds)
        pet_state = self._resolve_pet_state(stripped, idle_seconds, cards, radar_cards)
        pet_profile = self._pet_profile(pet_state)
        mascot_state = pet_profile.get("mascot_state") or (self._highest_mascot_state(cards) if cards else "peek")
        pet_bubble = self._pet_bubble(pet_profile, cards, radar_cards, milestone_cards)
        return {
            "reminder_cards": cards,
            "radar_cards": radar_cards,
            "milestone_cards": milestone_cards,
            "agent_mode": "reminder",
            "mascot_state": mascot_state,
            "emotion_state": pet_profile.get("emotion_state", self._emotion_for_mascot(mascot_state)),
            "pet_state": pet_state,
            "active_journey_state": self._active_journey_state(pet_state),
            "pet_profile": pet_profile,
            "pet_bubble": pet_bubble,
            "delivery_trace": self.delivery_trace("reminder_snapshot", "ReminderPlanner", "提醒规划", "根据空白页、停留时间、缺失章节、写作雷达和交付里程碑生成低打扰桌宠提醒。", self._default_evidence_refs(["rule-observable-criteria", "rule-owner-scope"])),
        }

    def review_prd(self, current_text: str) -> dict:
        missing_sections = self.missing_sections(current_text)
        risk_flags = self.risk_flags(current_text)
        quality_metrics = self.quality_metrics(current_text)
        evidence_refs = self._default_evidence_refs(["rule-observable-criteria", "rule-owner-scope", "rule-risk-boundary"])
        return {
            "review_summary": self._review_summary(quality_metrics, missing_sections, risk_flags),
            "quality_metrics": quality_metrics,
            "missing_sections": missing_sections,
            "risk_flags": risk_flags,
            "delivery_trace": self.delivery_trace("review_prd", "RiskReviewer", "风险评审", "检查 PRD 的章节完整度、验收可测试性、指标可度量性和交付风险。", evidence_refs),
            "evidence_refs": evidence_refs,
            "artifact_preview": self.build_artifact_preview(current_text),
        }

    def generate_delivery_plan(self, current_text: str) -> dict:
        review = self.review_prd(current_text)
        evidence_refs = self._default_evidence_refs(["rule-delivery-checkpoints", "rule-owner-scope", "style-delivery-ready"])
        plan = {
            "title": "交付计划",
            "phases": [
                {"name": "需求澄清", "owner": "Product Manager", "tasks": ["补齐缺失章节：" + ("、".join(item["label"] for item in review["missing_sections"][:4]) or "暂无关键缺失"), "确认目标用户、范围、非目标和指标口径。", "把模糊描述改写为可验证需求。"], "checkpoint": "PRD review"},
                {"name": "方案评审", "owner": "Design Lead / Tech Lead", "tasks": ["对关键流程输出原型和状态流转。", "识别权限、数据、模型输出和异常分支。", "确认前后端接口、埋点和灰度策略。"], "checkpoint": "Design and technical review"},
                {"name": "开发测试", "owner": "Engineering / QA", "tasks": ["按验收标准拆分测试用例。", "实现 Tab 联想、选区改写、评审和导出主流程。", "验证离线 fallback，保证比赛现场无模型 key 也可运行。"], "checkpoint": "QA acceptance"},
                {"name": "灰度复盘", "owner": "Product Owner", "tasks": ["收集初稿完成时间、评审返工率和联想接受率。", "复盘 AI 建议误用场景并补充知识包规则。", "决定是否进入真实文档源集成阶段。"], "checkpoint": "Launch review"},
            ],
            "dependencies": ["Seeded PRD Knowledge Pack", "Birdhouse Work Buddy mode state", "Offline deterministic suggestion engine", "Human review before final delivery"],
        }
        return {**review, "delivery_plan": plan, "delivery_trace": self.delivery_trace("generate_delivery_plan", "TaskPlanner", "任务拆解", "把当前 PRD 转换为阶段、任务、负责人角色、依赖和检查点。", evidence_refs), "evidence_refs": evidence_refs}

    def quality_snapshot(self, current_text: str) -> dict:
        return {"quality_metrics": self.quality_metrics(current_text), "missing_sections": self.missing_sections(current_text), "risk_flags": self.risk_flags(current_text), "style_match": self.style_match(current_text)}

    def export_prd_markdown(self, current_text: str) -> bytes:
        review = self.review_prd(current_text)
        plan = self.generate_delivery_plan(current_text)["delivery_plan"]
        lines = [current_text.strip() or "# PRD 草稿", "", "---", "", "## AI Work Buddy 评审摘要", review["review_summary"], "", "## 质量评分"]
        lines.extend(f"- {item['label']}：{item['score']} 分。{item['rationale']}" for item in review["quality_metrics"])
        lines.extend(["", "## 缺失章节"])
        lines.extend(f"- {item['label']}" for item in review["missing_sections"]) if review["missing_sections"] else lines.append("- 暂无关键缺失。")
        lines.extend(["", "## 风险提示"])
        lines.extend(f"- [{item['severity']}] {item['title']}：{item['detail']}" for item in review["risk_flags"]) if review["risk_flags"] else lines.append("- 暂无高优先级风险。")
        lines.extend(["", "## 交付计划"])
        for phase in plan["phases"]:
            lines.append(f"### {phase['name']}（{phase['owner']}）")
            lines.extend(f"- {task}" for task in phase["tasks"])
            lines.append(f"- 检查点：{phase['checkpoint']}")
        lines.extend(["", "## Demo 标语", self.pack["workspace"]["slogan"]])
        return "\n".join(lines).encode("utf-8")

    def build_artifact_preview(self, current_text: str) -> dict:
        states = self.section_states(current_text)
        present_count = sum(1 for item in states if item.present)
        return {"title": self._extract_title(current_text) or "PRD 草稿", "section_count": present_count, "required_section_count": len(REQUIRED_SECTIONS), "readiness": round(present_count / len(REQUIRED_SECTIONS) * 100), "word_count": len(re.findall(r"[\w\u4e00-\u9fff]+", current_text or ""))}

    def section_states(self, current_text: str) -> List[SectionState]:
        lower = (current_text or "").lower()
        return [SectionState(key=key, label=label, present=any(alias.lower() in lower for alias in aliases)) for key, label, aliases in REQUIRED_SECTIONS]

    def missing_sections(self, current_text: str) -> List[dict]:
        return [{"key": item.key, "label": item.label} for item in self.section_states(current_text) if not item.present]

    def quality_metrics(self, current_text: str) -> List[dict]:
        states = self.section_states(current_text)
        present_count = sum(1 for item in states if item.present)
        completeness = round(35 + present_count / len(states) * 60)
        has_acceptance = any(item.key == "acceptance" and item.present for item in states)
        has_risk = any(item.key == "risks" and item.present for item in states)
        given_count = len(re.findall(r"\bGiven\b|当.+时|如果", current_text or "", flags=re.IGNORECASE))
        testability = min(96, 42 + (28 if has_acceptance else 0) + min(20, given_count * 8))
        alignment = min(95, 58 + self._keyword_hits(current_text, ["用户", "目标", "范围", "指标", "交付"]) * 6)
        risk_score = 78 if has_risk else 46
        readiness = round((completeness + testability + alignment + risk_score) / 4)
        metrics = [("section_completeness", "章节完整度", completeness, "核心 PRD 章节覆盖越完整，评审返工风险越低。"), ("acceptance_testability", "验收可测试性", testability, "验收标准需要能被产品、研发和 QA 共同判定。"), ("context_alignment", "知识库贴合度", alignment, "需求表达是否复用了团队 PRD 风格、术语和交付规则。"), ("risk_readiness", "风险边界", risk_score, "是否提前说明非目标、依赖、模型误用和发布边界。"), ("delivery_readiness", "交付就绪度", readiness, "综合章节、验收、指标和风险后的交付可执行程度。")]
        return [{"key": key, "label": label, "score": max(0, min(100, score)), "status": self._score_status(score), "rationale": rationale} for key, label, score, rationale in metrics]

    def risk_flags(self, current_text: str) -> List[dict]:
        missing = {item["key"] for item in self.missing_sections(current_text)}
        flags: List[dict] = []
        if "acceptance" in missing:
            flags.append({"severity": "high", "title": "缺少可验收标准", "detail": "当前需求还不能稳定转成测试用例，建议补充 Given/When/Then 或明确检查项。", "evidence_ref": "rule-observable-criteria"})
        if "non_goals" in missing or "scope" in missing:
            flags.append({"severity": "medium", "title": "范围边界不清", "detail": "缺少范围或非目标会导致评审时不断扩需求。", "evidence_ref": "rule-owner-scope"})
        if "metrics" in missing:
            flags.append({"severity": "medium", "title": "缺少成功指标", "detail": "没有指标时很难判断 AI 写作能力是否真正提升交付效率。", "evidence_ref": "style-delivery-ready"})
        if "risks" in missing:
            flags.append({"severity": "low", "title": "风险边界未前置", "detail": "建议说明 AI 建议误用、知识包过期、权限集成和人工复核边界。", "evidence_ref": "rule-risk-boundary"})
        return flags

    def style_match(self, current_text: str) -> dict:
        text = current_text or ""
        hits = self._keyword_hits(text, ["背景", "目标", "范围", "验收", "指标", "风险", "交付", "用户"])
        score = min(96, 52 + hits * 6 + min(12, len(text) // 280))
        return {"score": score, "label": "团队 PRD 风格匹配", "matched_fingerprints": self.pack.get("style_fingerprints", [])[:2], "summary": "当前草稿已匹配“先摘要后细节”和“交付可执行”两类团队写作风格。" if score >= 70 else "当前草稿仍需要补充结构、指标和验收口径才能更接近团队 PRD 风格。"}

    def get_persona_profile(self, persona: str = "INTJ_ARCHITECT") -> dict:
        wanted = self._normalize_persona_key(persona)
        profiles = self.pack.get("persona_profiles", [])
        return next((item for item in profiles if item.get("key") == wanted), profiles[0] if profiles else {"key": "INTJ_ARCHITECT", "display_label": "INTJ 建筑师", "tone": "concise_strategic", "risk_bias": "high", "rewrite_rules": []})

    def delivery_trace(self, action: str, skill_name: str, display_label: str, detail: str, evidence_refs: List[dict]) -> List[dict]:
        return [{"step": "ContextLoad", "skill_name": "StyleProfiler", "display_label": "风格画像", "detail": "读取 seeded PRD/MRD 样例、术语表、章节模板、MBTI persona 和交付规则。", "evidence_refs": [item["id"] for item in evidence_refs[:1]]}, {"step": action, "skill_name": skill_name, "display_label": display_label, "detail": detail, "evidence_refs": [item["id"] for item in evidence_refs]}, {"step": "Explain", "skill_name": "TraceExplainer", "display_label": "联想解释", "detail": "把建议和来源绑定，避免 AI 联想变成不可解释的黑盒。", "evidence_refs": [item["id"] for item in evidence_refs]}]

    def _next_edit_trace(self, action: str, suggestion_kind: str, has_rewrite: bool, evidence_refs: List[dict]) -> List[dict]:
        trace = [
            {"step": "ContextLoad", "skill_name": "StyleProfiler", "display_label": "风格画像", "detail": "读取 seeded PRD/MRD、MRD 市场判断、复盘结论、术语表和交付规则。", "evidence_refs": [item["id"] for item in evidence_refs[:1]]},
            {"step": action, "skill_name": "RequirementCompleter", "display_label": "需求补全", "detail": f"按 {suggestion_kind} 预测下一段 ghost completion 和下一处编辑位置。", "evidence_refs": [item["id"] for item in evidence_refs]},
        ]
        if has_rewrite:
            trace.append({"step": "Rephrase", "skill_name": "RewriteEditor", "display_label": "改写编辑", "detail": "检测到模糊需求句，生成可接受、可拒绝、可回滚的 rephrase diff。", "evidence_refs": [item["id"] for item in evidence_refs if item["id"] in {"rule-reversible-diff", "rule-observable-criteria"}]})
        trace.append({"step": "Explain", "skill_name": "TraceExplainer", "display_label": "联想解释", "detail": "解释建议来自哪类历史 PRD/MRD、团队规则或验收样例。", "evidence_refs": [item["id"] for item in evidence_refs]})
        return trace

    def _extract_last_editable_block(self, current_text: str) -> str:
        blocks = [item.strip() for item in re.split(r"\n\s*\n", current_text or "") if item.strip()]
        for block in reversed(blocks):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            content_lines = [line for line in lines if not line.startswith("#")]
            if content_lines:
                return "\n".join(content_lines)
        return ""

    def _needs_process_rewrite(self, block: str, current_text: str) -> bool:
        if len((block or "").strip()) < 8:
            return False
        vague_hits = self._keyword_hits(block, ["提升", "优化", "更好", "智能", "自动", "效率", "快速", "帮助", "完善", "重整"])
        concrete_hits = self._keyword_hits(block, ["Given", "When", "Then", "验收", "指标", "范围", "非目标", "owner", "Owner", "触发", "边界"])
        return vague_hits > 0 and concrete_hits < 2

    def _next_edit_rewrite(self, block: str, persona: str = "INTJ_ARCHITECT") -> str:
        compact = self._single_line(block)
        profile = self.get_persona_profile(persona)
        persona_label = profile.get("display_label", "INTJ 建筑师")
        return (
            f"面向正在撰写 PRD/MRD 的 PM/BD，当用户输入“{compact}”这类半成品需求时，"
            f"系统需要基于团队历史 PRD、MRD 和交付规则，同时给出下一段补齐、当前句 rephrase、来源解释和可回滚 diff；"
            f"本次默认采用 {persona_label} 写作人格，输出需包含对象、触发条件、边界和验收口径。"
        )

    def _replace_last_block(self, current_text: str, block: str, replacement: str) -> str:
        if not block or not replacement:
            return current_text
        index = current_text.rfind(block)
        if index < 0:
            return (current_text.rstrip() + "\n\n" + replacement).strip()
        return current_text[:index] + replacement + current_text[index + len(block):]

    def _suggestion_kind(self, next_missing: Optional[SectionState], has_rewrite: bool) -> str:
        if has_rewrite and next_missing:
            return "rewrite_then_complete"
        if has_rewrite:
            return "inline_rephrase"
        if next_missing and next_missing.key == "acceptance":
            return "acceptance_completion"
        if next_missing:
            return "section_completion"
        return "delivery_task_projection"

    def _next_edit_label(self, suggestion_kind: str) -> str:
        labels = {
            "rewrite_then_complete": "先重写当前模糊句，再按 Tab 补下一段",
            "inline_rephrase": "当前句可直接接受 rephrase diff",
            "acceptance_completion": "下一步最该补验收标准",
            "section_completion": "下一步补齐缺失 PRD 章节",
            "delivery_task_projection": "章节齐备，下一步投影成交付任务",
        }
        return labels.get(suggestion_kind, "Next Edit Suggestion")

    def _rewrite_hint(self, last_block: str, rewrite_text: str, next_missing: Optional[SectionState]) -> str:
        if rewrite_text:
            return "检测到当前句偏愿景化，建议先改成包含对象、触发条件、输出、边界和验收口径的 working-doc 表达。"
        if next_missing:
            return f"当前 PRD 下一处最有价值的编辑点是补齐“{next_missing.label}”。"
        return "当前核心章节基本齐备，建议进入 owner、依赖、检查点和灰度计划拆解。"

    def _cursor_target(self, source_text: str, next_missing: Optional[SectionState], has_rewrite: bool) -> dict:
        if has_rewrite:
            return {"type": "current_block", "label": "当前句 rephrase", "instruction": "先查看右侧 diff；接受后再按 Tab 插入下一段。"}
        if next_missing:
            return {"type": "missing_section", "key": next_missing.key, "label": next_missing.label, "instruction": f"按 Tab 在 cursor 位置插入“{next_missing.label}”。"}
        return {"type": "delivery_plan", "label": "交付任务", "instruction": "核心章节齐备，建议生成交付计划。"}

    def _rewrite_text(self, source: str, mode: str) -> str:
        compact = self._single_line(source)
        if mode == "make_concise":
            first = re.split(r"[。；;\n]", compact)[0].strip()
            return first + "。" if first and not first.endswith("。") else first
        if mode == "make_formal":
            return f"为确保需求可评审、可实现、可验收，本文档需要明确说明：{compact}。相关范围、边界和验收口径需在评审前完成确认。"
        if mode == "convert_user_story":
            return f"- 作为目标用户，我希望{compact}，以便在需求写作和交付评审中获得更稳定的结构、表达和验收依据。"
        if mode == "add_acceptance_criteria":
            return f"{compact}\n\n### 验收标准\n- Given 用户正在编辑该需求，When 触发对应功能，Then 系统需要返回可执行、可验证的结果。\n- Given 需求进入评审，When 评审人检查文档，Then 必须能看到对象、范围、边界和验收口径。"
        if mode == "clarify_ambiguity":
            return f"{compact}\n\n澄清后：该需求面向正在撰写 PRD 的产品经理，触发条件为用户输入半成品需求或选中文本，系统输出必须限定在当前知识包和文档上下文内，并提供可验收的补全、改写或风险提示。"
        if mode == "turn_into_delivery_tasks":
            return f"### 交付任务\n- 产品：确认需求意图和业务边界，输入内容为“{compact[:60]}”。\n- 设计：补充关键流程、空态、异常态和交互反馈。\n- 研发：实现联想、改写、评审和导出接口，并保留离线 fallback。\n- 测试：覆盖快捷键、缺失章节识别、改写模式和导出内容。"
        return compact

    def _persona_rewrite_text(self, source: str, profile: dict) -> str:
        compact = self._single_line(source)
        key = profile.get("key", "INTJ_ARCHITECT")
        if key == "ENTJ_COMMANDER":
            return f"目标：{compact}。\n行动项：明确 owner、优先级、验收口径和上线检查点，保证团队可以立即进入评审和排期。"
        if key == "INFJ_ADVOCATE":
            return f"用户价值：{compact}。\n为了让团队在评审中更容易形成共识，需要补充用户动机、协作边界和对一线使用者的实际帮助。"
        if key == "ENFP_CAMPAIGNER":
            return f"机会点：{compact}。\n这不是单纯把文档写快，而是让 PM 在创作过程中获得一个会提醒、会补全、会陪跑的小鸟搭档，同时保留清晰验收条件。"
        return f"结构化表述：{compact}。\n边界：需明确适用对象、触发条件、非目标、验收标准和潜在风险，避免需求在评审阶段继续扩散。"

    def _review_summary(self, quality_metrics: List[dict], missing_sections: List[dict], risk_flags: List[dict]) -> str:
        avg = round(sum(item["score"] for item in quality_metrics) / len(quality_metrics)) if quality_metrics else 0
        missing_text = "、".join(item["label"] for item in missing_sections[:4]) or "暂无关键缺失"
        risk_text = "、".join(item["title"] for item in risk_flags[:3]) or "暂无高优先级风险"
        return f"当前 PRD 综合就绪度 {avg} 分，优先补齐：{missing_text}。主要风险：{risk_text}。"

    def _fallback_section_text(self, key: str, label: str) -> str:
        return f"## {label}\n请补充 {label}，并明确对象、触发条件、边界和验收口径。"

    def _polish_next_step_text(self, current_text: str) -> str:
        return "## 下一步\n当前 PRD 的核心章节已基本齐备，建议进入交付计划拆解：确认 owner、依赖、检查点、灰度策略和复盘指标。"

    def _default_evidence_refs(self, ids: Iterable[str]) -> List[dict]:
        lookup: Dict[str, dict] = {}
        for item in self.pack.get("style_fingerprints", []):
            lookup[item["id"]] = {"id": item["id"], "source_type": "style_fingerprint", "title": item.get("display_name") or item.get("name"), "detail": "；".join(item.get("signals", [])[:2])}
        for item in self.pack.get("delivery_rules", []):
            lookup[item["id"]] = {"id": item["id"], "source_type": "delivery_rule", "title": item.get("display_name") or item.get("name"), "detail": item.get("description", "")}
        for item in self.pack.get("glossary", []):
            lookup[item["id"]] = {"id": item["id"], "source_type": "glossary", "title": item.get("term", ""), "detail": item.get("definition", "")}
        return [lookup[item_id] for item_id in ids if item_id in lookup]

    def writing_radar_cards(self, current_text: str) -> List[dict]:
        text = current_text or ""
        stripped = text.strip()
        if not stripped:
            return []
        missing = {item["key"] for item in self.missing_sections(text)}
        rule_lookup = {item.get("key"): item for item in self.pack.get("writing_radar_rules", [])}
        cards: List[dict] = []
        evidence_hits = self._keyword_hits(text, ["访谈", "调研", "用户反馈", "数据来源", "证据", "客服", "工单", "复盘"])
        if evidence_hits == 0 and len(stripped) > 80:
            cards.append(self._radar_card(rule_lookup.get("missing_user_evidence"), "missing_user_evidence"))
        has_number = bool(re.search(r"\d+|%|分钟|小时|天|周|月|当前值|目标值", text))
        if "metrics" in missing or ("指标" in text and not has_number):
            cards.append(self._radar_card(rule_lookup.get("missing_metric_baseline"), "missing_metric_baseline"))
        solution_hits = self._keyword_hits(text, ["方案", "实现", "系统需要", "功能", "能力", "支持"])
        if solution_hits > 0 and {"background", "goal"}.intersection(missing):
            cards.append(self._radar_card(rule_lookup.get("solution_before_problem"), "solution_before_problem"))
        requirement_hits = self._keyword_hits(text, ["需求", "系统需要", "功能", "能力", "支持", "用户可以"])
        if "acceptance" in missing and requirement_hits > 0:
            cards.append(self._radar_card(rule_lookup.get("acceptance_candidate"), "acceptance_candidate"))
        owner_hits = self._keyword_hits(text, ["owner", "负责人", "PM", "产品", "设计", "研发", "测试", "QA", "Engineering", "Design"])
        if owner_hits == 0 and len(stripped) > 140:
            cards.append(self._radar_card(rule_lookup.get("owner_missing"), "owner_missing"))
        vague_hits = self._keyword_hits(text, ["提升", "优化", "更好", "智能", "自动", "效率", "快速", "完善", "重整"])
        concrete_hits = self._keyword_hits(text, ["验收", "指标", "范围", "非目标", "触发", "边界", "Given", "When", "Then"])
        if vague_hits >= 2 and concrete_hits < 3:
            cards.append(self._radar_card(rule_lookup.get("vague_outcome"), "vague_outcome"))
        return cards[:4]

    def _radar_card(self, rule: Optional[dict], fallback_key: str) -> dict:
        rule = rule or {
            "key": fallback_key,
            "display_label": "写作雷达",
            "message": "当前段落有一个可补齐点。",
            "suggested_action": "补充对象、触发条件、边界或验收口径。",
            "severity": "low",
            "mascot_state": "peek",
            "evidence_ref": "rule-observable-criteria",
        }
        return {
            "key": rule.get("key", fallback_key),
            "display_label": rule.get("display_label", "写作雷达"),
            "message": rule.get("message", ""),
            "suggested_action": rule.get("suggested_action", ""),
            "severity": rule.get("severity", "low"),
            "mascot_state": rule.get("mascot_state", "peek"),
            "evidence_ref": rule.get("evidence_ref", ""),
            "source": "WritingRadar",
        }

    def _milestone_cards(self, current_text: str, idle_seconds: int | float) -> List[dict]:
        stripped = (current_text or "").strip()
        preview = self.build_artifact_preview(current_text)
        risk_flags = self.risk_flags(current_text)
        cards: List[dict] = []
        if not stripped:
            cards.append({"key": "page_start", "display_label": "页面刚创建", "message": "先写一句问题背景，系统就能开始做 next edit 联想。", "status": "idle"})
            return cards
        cards.append({"key": "readiness", "display_label": "交付就绪度", "message": f"已覆盖 {preview['section_count']}/{preview['required_section_count']} 个核心章节，当前就绪度 {preview['readiness']}%。", "status": "working"})
        if float(idle_seconds or 0) >= 90:
            cards.append({"key": "idle_watch", "display_label": "停留时间提醒", "message": "页面停留较久，小鸟保持低打扰，只提示最关键的下一步。", "status": "watch"})
        if preview["readiness"] >= 70 and not any(item.get("severity") == "high" for item in risk_flags):
            cards.append({"key": "result_ready", "display_label": "结果接近可交付", "message": "建议导出 Markdown 并生成交付计划。", "status": "ready"})
        elif risk_flags:
            cards.append({"key": "review_risk", "display_label": "评审风险未清", "message": risk_flags[0]["detail"], "status": "warning"})
        return cards[:3]

    def _resolve_pet_state(self, stripped: str, idle_seconds: int | float, cards: List[dict], radar_cards: List[dict]) -> str:
        if not stripped or len(stripped) < 20:
            return "IDLE_BIRDHOUSE"
        readiness = self.build_artifact_preview(stripped)["readiness"]
        high_radar = any(item.get("severity") == "high" for item in radar_cards)
        high_reminder = any(item.get("severity") == "high" for item in cards)
        if high_radar or high_reminder:
            return "REVIEW_WARNING"
        if readiness >= 70:
            return "RESULT_READY"
        if float(idle_seconds or 0) >= 180:
            return "SLEEPING"
        if radar_cards:
            return "WRITING_RADAR"
        if len(stripped) < 160:
            return "FIRST_LINE_NUDGE"
        return "IDLE_BIRDHOUSE"

    def _pet_profile(self, pet_state: str) -> dict:
        catalog = self.pack.get("pet_state_catalog", [])
        fallback = {"key": pet_state, "display_label": pet_state, "mascot_state": "peek", "emotion_state": "calm", "bubble": "小鸟正在低打扰待命。", "motion": "soft_breathing"}
        return next((item for item in catalog if item.get("key") == pet_state), fallback)

    def _pet_bubble(self, pet_profile: dict, reminder_cards: List[dict], radar_cards: List[dict], milestone_cards: List[dict]) -> str:
        if radar_cards:
            return radar_cards[0].get("message", pet_profile.get("bubble", ""))
        if reminder_cards:
            return reminder_cards[0].get("message", pet_profile.get("bubble", ""))
        if milestone_cards and milestone_cards[0].get("key") != "readiness":
            return milestone_cards[0].get("message", pet_profile.get("bubble", ""))
        return pet_profile.get("bubble", "")

    def _active_journey_state(self, pet_state: str) -> str:
        return {
            "IDLE_BIRDHOUSE": "EMPTY_PAGE",
            "PEEK_GREETING": "EMPTY_PAGE",
            "FIRST_LINE_NUDGE": "FIRST_LINE",
            "WRITING_RADAR": "WRITING_RADAR",
            "NEXT_EDIT_WORKING": "NEXT_EDIT_WORKING",
            "REVIEW_WARNING": "REVIEW_WARNING",
            "RESULT_READY": "DELIVER_READY",
            "SLEEPING": "EMPTY_PAGE",
        }.get(pet_state, "EMPTY_PAGE")

    def _reminder_card(self, rule: Optional[dict], fallback_trigger: str) -> dict:
        rule = rule or {"trigger": fallback_trigger, "message": "当前 PRD 有一个可优化点。", "mascot_state": "peek", "severity": "low"}
        return {"trigger": rule.get("trigger", fallback_trigger), "message": rule.get("message", ""), "mascot_state": rule.get("mascot_state", "peek"), "severity": rule.get("severity", "low")}

    def _highest_mascot_state(self, cards: List[dict]) -> str:
        rank = {"warning": 5, "working": 4, "celebrate": 3, "fly_out": 2, "peek": 1}
        return max(cards, key=lambda item: rank.get(item.get("mascot_state", "peek"), 1)).get("mascot_state", "peek")

    def _emotion_for_mascot(self, mascot_state: str) -> str:
        return {"peek": "calm", "fly_out": "ready", "working": "focused", "warning": "alert", "celebrate": "happy"}.get(mascot_state, "calm")

    def _build_inline_diff(self, before_text: str, after_text: str, diff_type: str, summary: str) -> dict:
        return {"type": diff_type, "summary": summary, "before_text": before_text, "after_text": after_text, "added_text": self._diff_suffix(before_text, after_text), "can_accept": True, "can_reject": True, "can_rollback": True}

    def _store_rollback(self, before_text: str, after_text: str, action: str) -> str:
        token = hashlib.sha1(f"{action}\n{before_text}\n{after_text}\n{time.time()}".encode("utf-8")).hexdigest()[:16]
        self.rollback_store[token] = {"before_text": before_text, "after_text": after_text, "action": action, "created_at": time.time()}
        max_history = int(self.pack.get("rollback_policy", {}).get("max_history", 12))
        if len(self.rollback_store) > max_history:
            oldest = sorted(self.rollback_store.items(), key=lambda item: item[1]["created_at"])[0][0]
            self.rollback_store.pop(oldest, None)
        return token

    def _normalize_agent_mode(self, agent_mode: str) -> str:
        text = (agent_mode or "reminder").strip().lower()
        return "ASSISTANT" if text in {"assistant", "assistantmode", "assist"} else "REMINDER"

    def _normalize_persona_key(self, persona: str) -> str:
        raw = (persona or "INTJ_ARCHITECT").strip().upper().replace(" ", "_").replace("-", "_")
        aliases = {"INTJ": "INTJ_ARCHITECT", "ENTJ": "ENTJ_COMMANDER", "INFJ": "INFJ_ADVOCATE", "ENFP": "ENFP_CAMPAIGNER"}
        return aliases.get(raw, raw if any(item.get("key") == raw for item in self.pack.get("persona_profiles", [])) else "INTJ_ARCHITECT")

    def _extract_persona_key(self, command: str) -> Optional[str]:
        upper = (command or "").upper()
        for profile in self.pack.get("persona_profiles", []):
            if profile.get("key", "") in upper or profile.get("key", "")[:4] in upper:
                return profile.get("key")
        return None

    def _extract_last_paragraph(self, current_text: str) -> str:
        parts = [item.strip() for item in re.split(r"\n\s*\n", current_text or "") if item.strip()]
        return parts[-1] if parts else ""

    def _diff_suffix(self, before_text: str, after_text: str) -> str:
        return after_text[len(before_text):].strip() if after_text.startswith(before_text) else after_text

    def _extract_title(self, current_text: str) -> str:
        match = re.search(r"^#\s+(.+)$", current_text or "", flags=re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _keyword_hits(self, text: str, keywords: Iterable[str]) -> int:
        return sum(1 for keyword in keywords if keyword.lower() in (text or "").lower())

    def _score_status(self, score: int) -> str:
        if score >= 85:
            return "strong"
        if score >= 65:
            return "watch"
        return "weak"

    def _single_line(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text or "").strip()
        return cleaned.rstrip("。；;")

    def _ensure_leading_blank_line(self, text: str) -> str:
        stripped = (text or "").strip()
        return "\n\n" + stripped if stripped else ""
