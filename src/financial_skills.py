from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class FinancialSkill:
    key: str
    label: str
    focus: str
    instruction: str
    output_contract: str


SKILL_LIBRARY: Dict[str, FinancialSkill] = {
    "product_structure_analyst": FinancialSkill(
        key="product_structure_analyst",
        label="产品结构分析",
        focus="识别产品定位、跟踪标的、规模层级和结构差异。",
        instruction="优先回答产品事实、结构特征和与同类样本的相对位置。",
        output_contract="结论要给出产品事实、结构解释和适用边界。",
    ),
    "flow_signal_reader": FinancialSkill(
        key="flow_signal_reader",
        label="资金与成交信号",
        focus="解释成交额、净流入、持续性与价量配合关系。",
        instruction="先描述资金行为，再解释它可能代表的市场情绪和持续性。",
        output_contract="区分已发生的量化信号与对后续走势的审慎判断。",
    ),
    "market_impact_analyst": FinancialSkill(
        key="market_impact_analyst",
        label="宏观与市场影响",
        focus="将政策或事件映射到市场流动性、风险偏好与板块影响。",
        instruction="从宏观、行业、交易层三个层次解释影响路径。",
        output_contract="结论需区分短期影响、中期传导和不确定性。",
    ),
    "policy_interpreter": FinancialSkill(
        key="policy_interpreter",
        label="政策解读",
        focus="提炼政策目标、约束条件、执行对象与关键条款。",
        instruction="优先还原政策文本中的强制要求、适用范围和信号变化。",
        output_contract="摘要必须能回答“说了什么、为什么重要、影响谁”。",
    ),
    "product_strategy_advisor": FinancialSkill(
        key="product_strategy_advisor",
        label="产品策略建议",
        focus="把政策和市场变化翻译成产品观察、策略动作和沟通抓手。",
        instruction="只给出能落地的产品视角建议，不输出空泛口号。",
        output_contract="建议要包含对象、动作和触发条件。",
    ),
    "risk_compliance_reviewer": FinancialSkill(
        key="risk_compliance_reviewer",
        label="风险与合规",
        focus="识别表述边界、适当性风险、信息缺口和过度解读风险。",
        instruction="对所有判断补充前提条件、限制事项和表述边界。",
        output_contract="必须单列风险提示，避免确定性过强的表述。",
    ),
    "report_editor": FinancialSkill(
        key="report_editor",
        label="报告编审",
        focus="把多视角分析整理成结构清晰、层次分明、专业克制的输出。",
        instruction="统一口径、消除重复、把事实判断建议分层排布。",
        output_contract="最终报告必须具备标题层级、摘要感和执行优先级。",
    ),
    "narrative_planner": FinancialSkill(
        key="narrative_planner",
        label="内容叙事设计",
        focus="把研究结论转换成面向业务沟通的主线、标题和内容骨架。",
        instruction="围绕事实证据组织叙事，不夸张，不制造虚假确定性。",
        output_contract="输出应包含主线、受众和沟通节奏。",
    ),
}


MODULE_SKILLS: Dict[str, List[str]] = {
    "product_research": ["product_structure_analyst", "product_strategy_advisor", "risk_compliance_reviewer"],
    "market_monitoring": ["flow_signal_reader", "market_impact_analyst", "risk_compliance_reviewer"],
    "content_strategy": ["narrative_planner", "product_strategy_advisor", "risk_compliance_reviewer"],
    "policy_analysis": [
        "policy_interpreter",
        "market_impact_analyst",
        "product_strategy_advisor",
        "risk_compliance_reviewer",
        "report_editor",
    ],
}


DOCUMENT_WORKFLOWS: Dict[str, List[str]] = {
    "summary": ["policy_interpreter", "market_impact_analyst", "risk_compliance_reviewer", "report_editor"],
    "report": [
        "policy_interpreter",
        "market_impact_analyst",
        "product_strategy_advisor",
        "risk_compliance_reviewer",
        "report_editor",
    ],
}


def get_skill_cards(skill_keys: List[str]) -> List[dict]:
    cards = []
    for key in skill_keys:
        skill = SKILL_LIBRARY[key]
        cards.append(
            {
                "key": skill.key,
                "label": skill.label,
                "focus": skill.focus,
                "instruction": skill.instruction,
                "output_contract": skill.output_contract,
            }
        )
    return cards


def get_module_skill_cards(module_key: str) -> List[dict]:
    return get_skill_cards(MODULE_SKILLS.get(module_key, []))


def build_skillbook(skill_keys: List[str], include_contract: bool = True) -> str:
    lines: List[str] = []
    for key in skill_keys:
        skill = SKILL_LIBRARY[key]
        line = f"- {skill.label}：{skill.focus} 要求：{skill.instruction}"
        if include_contract:
            line += f" 输出标准：{skill.output_contract}"
        lines.append(line)
    return "\n".join(lines)

