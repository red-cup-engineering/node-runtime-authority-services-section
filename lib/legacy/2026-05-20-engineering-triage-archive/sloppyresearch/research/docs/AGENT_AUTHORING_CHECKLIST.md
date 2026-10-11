Agent Authoring Checklist — RRPR Papers

Purpose: help agents produce thesis‑centered, testable papers that align with RRPR ingestion and research workflows.

Before you start
- Read the source notes; list 3–5 core claims and any new terms.
- Decide the audience and scope (specialist vs. general RRPR reader).

Thesis and Structure
- Abstract has a one‑sentence thesis.
- Add “0. Thesis (Centered)” with Claim → Mechanism → Consequence → Contributions.
- Use the template in `docs/templates/rrpr_paper_template.md` to scaffold sections.

Foundations and Mapping
- For each foundation (e.g., Foucault, Bourdieu), include:
  - Mechanism (how it operates here)
  - Observables (what readers can see)
  - Mapping (which variables it sets: i, p, σ, φ, A_reg, T_auth)
- Add “Theory→Model Synthesis” defining variables and functions by name (A_perc, N, C, R_auth, H).

Math That “Does Work”
- Write U with the named functions; derive partials to show which levers move behavior.
- Include at least 1 lemma with sufficient conditions for a behavior flip (e.g., authority‑drift vs. resistance).
- Include at least 1 demonstration (principal–agent, selection dynamics, time‑step) and preferably a 6‑row mini table for two regimes.

Patterns, Practices, Ecology
- Add a “What to Look For” checklist; include platform regime heuristics and, if helpful, a typology quadrant.
- Add “Practices” (design patterns) and a short worked example timeline.

Measurement and Ethics
- Append a measurement appendix with proxies and thresholds (Uncertainty Index, Authority Markers, Cadence, Novelty, Support Lag).
- Optionally add an ethics/position note when terminology could be misread; focus on structural levers rather than moral framing.

Frontmatter
- Required: `id`, `title`. Recommended: `authors`, `date_created`, `date_modified`, `status`, `document_type`, `topics`, `disciplines`, `keywords`.
- Use `cites_internal` for RRPR docs; `[cites_external](cites_external)` with `key`, `title`, optional `authors`, `year`, `venue`, `doi`, `url`.
- Define new terms in `[defines](defines)` with `id`, `label`, `description`.

Quality Gates (final)
- Frontmatter validates (use `rsc/frontmatter_parser.py` if needed).
- Synthesis and variable names in theory match the math section exactly.
- At least one lemma + one demonstration present.
- Measurement appendix included with at least one operational proxy.
- Ethics/position present.

Optional
- Keep `.source.org` sibling for provenance when converting notes.
- Add a Glossary if jargon is unavoidable.

CLI Shortcuts
- Scaffold: `python3 code/apps/cli.py authoring scaffold txt/scientific-texts/<domain>/<subdomain> <id> "<Title>" --authors "<You>"`
- Lint: `python3 code/apps/cli.py authoring lint txt/scientific-texts/<...>/<id>.md`
- From note: `python3 code/apps/cli.py authoring from-note research/notes/<note>.md txt/scientific-texts/<domain>/<subdomain> <new-id>`

Examples
- Structure/model pattern: `txt/scientific-texts/sociology/contemporary/mapping-the-neurotic-platform-intellectual.md`.
- Theorem structure: `txt/scientific-texts/information/theorem-of-necessary-misalignment-of-truth-value-under-epistemic-constraint.md`.
