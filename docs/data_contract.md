# PRD Knowledge Pack Contract v2.1

The app runs without external integrations by loading a seeded PRD knowledge pack. A custom pack can be supplied with `PRD_KNOWLEDGE_PACK_PATH`.

Internal keys must stay English and stable. Chinese should be used only for user-facing UI labels, PRD content, assistant messages, and exported reports.

## Required Top-level Keys

- `workspace`: app name, slogan, tagline, description, and shortcut labels.
- `challenge_story`: competition narrative, market gap, demo flow, and differentiators.
- `flash_insight`: core product thesis explaining why process completion beats full-document generation for v1.
- `market_landscape`: competitive matrix across productivity SaaS, AI IDE, desktop pet products, and our wedge.
- `style_fingerprints`: reusable PRD/MRD writing patterns.
- `glossary`: product and delivery terms.
- `delivery_rules`: rules used by suggestion, review, reminder, radar, and task planning.
- `section_templates`: PRD section templates used for ghost suggestions.
- `demo_documents`: deterministic demo drafts.
- `rewrite_modes`: supported rewrite modes.
- `next_edit_patterns`: deterministic patterns for Tab completion plus rephrase diff.
- `cross_page_assets`: seeded PRD/MRD/retro/acceptance assets used to simulate cross-page knowledge.
- `writing_journey_states`: birdhouse process states from empty page to delivery-ready.
- `agent_modes`: English canonical modes such as `REMINDER` and `ASSISTANT`.
- `mascot_assets`: local asset paths for birdhouse, assistant mascot, brand hero, and persona matrix.
- `persona_profiles`: MBTI writing persona definitions with English canonical keys.
- `assistant_commands`: command palette entries such as `/assistant`, `@mbti`, `@review`, and `@expand`.
- `reminder_rules`: low-noise reminder triggers and mascot states.
- `pet_state_catalog`: English canonical desktop-pet states, user-facing bubble copy, mascot state, emotion state, and motion hint.
- `writing_radar_rules`: current-cell diagnostic rules used by Writing Radar.
- `pet_design_refs`: reference products and product lessons used for the pet status layer.
- `rollback_policy`: deterministic rollback constraints and retention policy.

## Pet State Catalog

Each `pet_state_catalog` item should include:

- `key`: English canonical key, e.g. `IDLE_BIRDHOUSE`, `WRITING_RADAR`, `REVIEW_WARNING`.
- `display_label`: Chinese UI label.
- `trigger`: English canonical trigger or condition name.
- `mascot_state`: `peek`, `fly_out`, `working`, `warning`, or `celebrate`.
- `emotion_state`: English state such as `calm`, `ready`, `scanning`, `focused`, `alert`, `happy`, or `sleepy`.
- `motion`: English UI motion hint such as `soft_breathing`, `radar_pulse`, or `warning_shake`.
- `bubble`: Chinese low-noise status copy.

## Writing Radar Rules

Each `writing_radar_rules` item should include:

- `key`: English canonical key, e.g. `missing_user_evidence`.
- `display_label`: Chinese UI label.
- `trigger`: English canonical trigger condition.
- `message`: Chinese user-facing hint.
- `suggested_action`: Chinese recommended next action.
- `severity`: `low`, `medium`, or `high`.
- `mascot_state`: mascot state shown when the card is active.
- `evidence_ref`: source rule or style id.

## Next Edit Patterns

Each `next_edit_patterns` item should include:

- `id`: stable English identifier.
- `kind`: English canonical kind such as `rewrite_then_complete` or `acceptance_completion`.
- `display_label`: Chinese UI label.
- `trigger`: Chinese user-facing trigger explanation.
- `behavior`: Chinese explanation of what Tab/rephrase should do.

## Agent Modes

Each `agent_modes` item should include:

- `key`: English canonical key, e.g. `REMINDER` or `ASSISTANT`.
- `display_label`: Chinese UI label.
- `description`: Chinese user-facing explanation.
- `default_mascot_state`: one of `peek`, `fly_out`, `working`, `warning`, or `celebrate`.

## Persona Profiles

Each `persona_profiles` item should include:

- `key`: English canonical key, e.g. `INTJ_ARCHITECT`.
- `display_label`: Chinese label, e.g. `建筑师`.
- `tone`: English style bucket such as `concise`, `formal`, `warm`, or `creative`.
- `rewrite_rules`: Chinese user-facing style rules.
- `risk_bias`: how strongly the persona surfaces risk.
- `sample_prompt`: optional Chinese prompt example shown in the UI.

The v2.1 demo ships four high-signal personas: `INTJ_ARCHITECT`, `ENTJ_COMMANDER`, `INFJ_ADVOCATE`, and `ENFP_CAMPAIGNER`.

## Reminder Rules

Each `reminder_rules` item should include:

- `trigger`: `empty_page`, `idle`, `missing_acceptance`, `long_section`, or `deadline`.
- `threshold`: numeric threshold or condition string.
- `message`: Chinese user-facing hint.
- `mascot_state`: `peek`, `fly_out`, `working`, `warning`, or `celebrate`.
- `severity`: low-noise priority such as `low`, `medium`, or `high`.

## Section Templates

Each item in `section_templates` should use a stable English key:

- `background`
- `goal`
- `user_story`
- `scope`
- `non_goals`
- `flow`
- `requirements`
- `acceptance`
- `metrics`
- `risks`
- `rollout`

Each template needs:

- `title`: user-facing Chinese section title.
- `ghost_text`: Markdown text returned by `inline_suggest` and `next_edit_suggest`.

## Evidence Refs

Every `style_fingerprints`, `glossary`, and `delivery_rules` item must include an `id`. These IDs become `evidence_refs` in API responses so the UI can explain why a suggestion was made.

## Compatibility

v2.1 intentionally avoids live Feishu, Notion, Slack, or DingTalk integrations. Those sources can later be converted into the same pack shape after permission, indexing, and access-control work is designed.
