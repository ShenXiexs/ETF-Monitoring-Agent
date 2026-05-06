from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class PRDSkill:
    key: str
    skill_name: str
    display_label: str
    focus: str
    instruction: str
    output_contract: str


SKILL_REGISTRY: Dict[str, PRDSkill] = {
    "style_profiler": PRDSkill(
        key="style_profiler",
        skill_name="StyleProfiler",
        display_label="风格画像",
        focus="Extract reusable writing patterns from seeded PRD and MRD examples.",
        instruction="Prefer concrete section shape, decision vocabulary, and delivery tone over generic writing advice.",
        output_contract="Return style signals, reusable phrases, and source references.",
    ),
    "requirement_completer": PRDSkill(
        key="requirement_completer",
        skill_name="RequirementCompleter",
        display_label="需求补全",
        focus="Predict the next useful PRD section from the current cursor context.",
        instruction="Complete the missing requirement section with concise, implementation-ready Chinese content.",
        output_contract="Return ghost text plus evidence references for why the completion is relevant.",
    ),
    "rewrite_editor": PRDSkill(
        key="rewrite_editor",
        skill_name="RewriteEditor",
        display_label="改写编辑",
        focus="Rephrase selected text while preserving product intent and delivery constraints.",
        instruction="Rewrite toward the selected mode without inventing unsupported business facts.",
        output_contract="Return replacement text, mode name, and rewrite rationale.",
    ),
    "acceptance_criteria_builder": PRDSkill(
        key="acceptance_criteria_builder",
        skill_name="AcceptanceCriteriaBuilder",
        display_label="验收标准",
        focus="Convert fuzzy requirements into testable Given/When/Then or checklist criteria.",
        instruction="Make criteria observable, bounded, and verifiable by product, design, engineering, and QA.",
        output_contract="Return acceptance criteria with measurable pass conditions.",
    ),
    "risk_reviewer": PRDSkill(
        key="risk_reviewer",
        skill_name="RiskReviewer",
        display_label="风险评审",
        focus="Find ambiguity, missing ownership, dependency risk, and delivery blind spots.",
        instruction="Call out risks as actionable warnings rather than vague concerns.",
        output_contract="Return risk flags with severity, evidence, and mitigation hints.",
    ),
    "task_planner": PRDSkill(
        key="task_planner",
        skill_name="TaskPlanner",
        display_label="任务拆解",
        focus="Translate PRD content into delivery phases, tasks, owners, and dependencies.",
        instruction="Keep tasks implementation-neutral but concrete enough for sprint planning.",
        output_contract="Return phases, task rows, dependency notes, and review checkpoints.",
    ),
    "trace_explainer": PRDSkill(
        key="trace_explainer",
        skill_name="TraceExplainer",
        display_label="联想解释",
        focus="Explain why the AI proposed a completion, rewrite, review warning, or task split.",
        instruction="Connect each suggestion to seeded knowledge, section templates, glossary, or delivery rules.",
        output_contract="Return human-readable trace entries with source IDs.",
    ),
    "persona_stylist": PRDSkill(
        key="persona_stylist",
        skill_name="PersonaStylist",
        display_label="人格风格",
        focus="Apply an English-canonical MBTI writing persona to PRD drafting and rewriting.",
        instruction="Adjust tone, density, risk posture, and structure without changing the core requirement intent.",
        output_contract="Return persona-aware replacement text and the persona profile used.",
    ),
    "reminder_planner": PRDSkill(
        key="reminder_planner",
        skill_name="ReminderPlanner",
        display_label="提醒规划",
        focus="Plan low-noise reminders based on document state, idle time, missing sections, and delivery risk.",
        instruction="Prefer small, contextual nudges instead of interruptive chatbot responses.",
        output_contract="Return reminder cards with trigger, message, severity, and mascot state.",
    ),
    "rollback_manager": PRDSkill(
        key="rollback_manager",
        skill_name="RollbackManager",
        display_label="状态回滚",
        focus="Track reversible inline review and rewrite suggestions.",
        instruction="Create deterministic rollback tokens and restore previous content safely.",
        output_contract="Return inline diff metadata, rollback token, and restored text when requested.",
    ),
}


PRD_IDE_WORKFLOW = [
    "style_profiler",
    "requirement_completer",
    "rewrite_editor",
    "acceptance_criteria_builder",
    "risk_reviewer",
    "task_planner",
    "trace_explainer",
    "persona_stylist",
    "reminder_planner",
    "rollback_manager",
]


def get_skill_cards(skill_keys: Iterable[str] | None = None) -> List[dict]:
    cards: List[dict] = []
    for key in skill_keys or PRD_IDE_WORKFLOW:
        skill = SKILL_REGISTRY[key]
        cards.append(
            {
                "key": skill.key,
                "skill_name": skill.skill_name,
                "display_label": skill.display_label,
                "focus": skill.focus,
                "instruction": skill.instruction,
                "output_contract": skill.output_contract,
            }
        )
    return cards


def build_skillbook(skill_keys: Iterable[str] | None = None) -> str:
    lines: List[str] = []
    for card in get_skill_cards(skill_keys):
        lines.append(
            "- {skill_name}: focus={focus}; instruction={instruction}; output_contract={output_contract}".format(
                **card
            )
        )
    return "\n".join(lines)
