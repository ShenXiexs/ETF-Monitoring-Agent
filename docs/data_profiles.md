# Custom PRD Knowledge Packs

`PRD_KNOWLEDGE_PACK_PATH` selects a custom PRD knowledge pack. The product adapts through one JSON pack rather than scattered demo fixtures.

## When to Customize

Use a custom pack when you want the Work Buddy + PRD IDE to imitate a different team style, domain, mascot behavior, persona set, or delivery process.

Common changes:

- Replace `demo_documents` with your own PRD/MRD examples.
- Adjust `style_fingerprints` to match the team writing style.
- Add glossary terms used by product, engineering, QA, design, BD, or delivery teams.
- Change `delivery_rules` to reflect real review gates.
- Rewrite `section_templates` for another document type.
- Tune `persona_profiles` if your team uses different writing personas.
- Tune `reminder_rules` if the birdhouse assistant feels too quiet or too interruptive.

## Recommended Workflow

1. Copy [data/prd_knowledge_pack.json](/Users/samxie/Research/Agent-Promotion/ai-driven-end-to-end-demand-delivery-engine/data/prd_knowledge_pack.json).
2. Edit the copied JSON.
3. Keep internal keys English and stable.
4. Set `PRD_KNOWLEDGE_PACK_PATH=/absolute/path/to/your_pack.json`.
5. Restart the server.
6. Use `refresh`, `inline_suggest`, `reminder_snapshot`, `inline_review`, and `quality_snapshot` to verify the pack.

## Design Constraint

Internal skill, persona, mode, action, and schema names should stay English canonical. User-facing titles, section text, assistant messages, reminder cards, and generated PRD output can remain Chinese.
