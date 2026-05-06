# PRD IDE Example

This folder is reserved for generated PRD IDE exports.

Recommended manual demo path:

1. `GET /`
2. `POST /workspace` with `action=load_prd_demo`
3. `POST /workspace` with `action=switch_agent_mode`
4. `POST /workspace` with `action=next_edit_suggest`
5. `POST /workspace` with `action=inline_suggest`
6. `POST /workspace` with `action=rewrite_selection`
7. `POST /workspace` with `action=apply_persona_rewrite`
8. `POST /workspace` with `action=inline_review`
9. `POST /workspace` with `action=rollback_suggestion`
10. `POST /workspace` with `action=reminder_snapshot`
11. `POST /workspace` with `action=generate_delivery_plan`
12. `POST /workspace` with `action=export_prd`

The active seeded context lives in [data/prd_knowledge_pack.json](/Users/samxie/Research/Agent-Promotion/ai-driven-end-to-end-demand-delivery-engine/data/prd_knowledge_pack.json).
