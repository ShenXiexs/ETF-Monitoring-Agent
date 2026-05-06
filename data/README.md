# PRD Knowledge Data

The challenge demo uses a deterministic seeded context pack:

- `prd_knowledge_pack.json`

The pack contains:

- PRD/MRD style fingerprints
- glossary entries
- delivery rules
- PRD section templates
- demo documents
- rewrite modes
- next edit patterns
- cross-page PRD/MRD assets
- market landscape and Flash insight
- `AssistantMode` and `ReminderMode` definitions
- birdhouse mascot asset mapping
- MBTI persona profiles
- assistant command definitions
- reminder rules
- pet state catalog
- writing radar rules
- desktop-pet design references
- rollback policy

Internal keys are English canonical. Chinese appears only in UI copy, assistant messages, generated PRD content, and exported reports.

Set `PRD_KNOWLEDGE_PACK_PATH` to point at a custom pack. If it is unset, the app uses the bundled file above.
