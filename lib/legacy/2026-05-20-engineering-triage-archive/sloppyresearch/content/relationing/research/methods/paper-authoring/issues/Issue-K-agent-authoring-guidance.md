+++
id = "issue.K"
title = "Agent authoring guidance (thesis-centered paper checklist)"
status = "open"
priority = "p3"
area = "authoring"
document_type = "issue"
topics = ["authoring", "guidance"]
created = "2025-11-09"
owner = ""
+++

Context
- Former document `content/docs/AGENT_AUTHORING_CHECKLIST.md` described how agents should structure RRPR papers (thesis box, foundations, math that “does work,” measurement appendix, etc.), and its content now lives in `content/relationing/research/methods/paper-authoring/relational-research-paper-specification.md`.
- Guidance now lives under `content/relationing/research/methods/paper-authoring/relational-research-paper-specification.md`; this issue tracks automation/linting follow-ups so instructions remain actionable.

Guidance (summary)
1. **Pre-work**: read source notes, list core claims/terms, define audience.
2. **Thesis & structure**: abstract with thesis; add “0. Thesis (Claim→Mechanism→Consequence→Contributions)”; use template under `docs/templates/rrpr_paper_template.md`.
3. **Foundations/mapping**: for each foundation, specify mechanism, observables, mapping to variables; add “Theory→Model Synthesis” table.
4. **Math doing work**: define functions, derive partials, include at least one lemma + one demonstration (e.g., principal–agent, selection dynamics) plus regime mini-table.
5. **Patterns/practices**: “What to Look For” checklist, platform regime heuristics, typology, practices + example timeline.
6. **Measurement/ethics**: measurement appendix (proxies, thresholds), optional ethics/position note.
7. **Frontmatter**: include `id`, `title`, `authors`, `status`, `document_type`, `topics`, `keywords`, `cites_internal`, `[cites_external](cites_external)`, `[defines](defines)`.
8. **Quality gates**: frontmatter validation, consistent variable names, lemma+demo, measurement appendix.
9. **CLI aids**: `rrpr authoring scaffold|lint|from-note` commands.

Acceptance
- [ ] Optional: turn checklist into lint rules or authoring tool hints (future issue)
- [ ] Update docs/templates to reflect the checklist (future TODO)

Links
- content/relationing/research/methods/paper-authoring/relational-research-paper-specification.md
- docs/templates/rrpr_paper_template.md
- code/rrp/authoring.py
