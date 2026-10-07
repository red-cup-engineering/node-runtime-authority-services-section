+++
id = "guide.research-paper-procedure"
title = "RRPR Research Paper Production Procedure"
status = "active"
document_type = "guide"
topics = ["authoring", "workflow"]
+++

RRPR Research Paper Production Procedure

Purpose: provide a clear, repeatable process to turn exploratory notes into canonical research papers under `txt/` that agents can ingest and traverse. This procedure centers a thesis, grounds it in critical theory or domain foundations, names constructs as variables/functions, then uses compact math to “do work” (prove flip conditions, produce demonstrations), and finishes with measurement and practice.

Scope: theoretical expositions, syntheses, commentaries, and formal items (theorem/definition/proof) that belong in `txt/scientific-texts/...`.

Outcomes
- A single Markdown file with TOML frontmatter that validates against `rrpr/frontmatter_parser.py`.
- A thesis‑centered, testable structure that maps theory → constructs → variables → model → regimes/lemmas → demonstrations → measurement → ethics.
- Optional verbatim `.source.org` for provenance.

CLI Aids (optional)
- Scaffold, lint, or convert notes via `python -m rrpr.cli.main authoring ...` commands (or `scripts/rrpr-cli.py authoring ...`).

Directory and Naming
- Location: choose a topical lane under `txt/scientific-texts/<domain>/<subdomain>/`.
- Filename = slugified `id` with `.md` extension. The `id` must match `^[a-z0-9\-\.]+$`.
- Keep `authors`, `date_created`, `date_modified` ISO `YYYY-MM-DD`, `status` one of: `draft|working|canonical|archived|deprecated`.
- `document_type` one of: `foundational_treatise|paper|theorem|definition|proof|experiment|note|commentary|draft|synthesis`.

Production Steps
1) Center the Thesis
- Write a one‑sentence thesis: what structural mechanism or construction you are claiming and why it matters.
- Add a “0. Thesis (Centered)” box after the Abstract with: Claim → Mechanism → Consequence → Contributions (bullets).

2) Inventory Sources and Claims
- List core claims, examples, and any terms to define. Collate key references (internal/external).
- Prepare `[defines](defines)` for new terms.

3) Foundations → Mechanism → Mapping
- Write “Critical/Domain Foundations” subsections. For each: add three lines:
  - Mechanism: how it operates here.
  - Observable effects: what readers would see.
  - Variable mapping: which parameter(s) it sets (e.g., `i, p, σ, φ, A_reg, T_auth`).
- Add a “Theory→Model Synthesis” table that names variables and functions (`A_perc, N, C, R_auth, H`).

4) Parameter Regimes and Lemmas
- Add a compact “Generation vs. Resistance” regimes box with actionable levers.
- Add 1–2 lemmas that show sufficient flip conditions (authority drift vs. resistance). Keep proofs short and checkable.

5) Mechanism and Demonstrations
- Write the reduced‑form model with the named functions. Derive partials to show which levers move behavior.
- Add demonstrations: principal–agent, selection dynamics, time‑step walkthrough, and a mini 6‑row table contrasting regimes.

6) Patterns, Practices, Ecology
- Add “What to Look For” patterns + a platform regimes heuristic + a typology (quadrants) if relevant.
- Add “Practices” (design patterns) and a worked example timeline.

7) Measurement and Ethics
- Append a measurement appendix: proxies, thresholds, and a composite red‑flag.
- Optionally include an ethics/position note when useful for readers; keep emphasis on structural analysis over individual blame.

8) Frontmatter Authoring (TOML)
- Required: `id`, `title`.
- Recommended: `authors`, `date_created`, `date_modified`, `status`, `document_type`, `topics`, `disciplines`, `keywords`.
- Internal citations: `cites_internal = ["<doc-id>", ...]` (current ingestor records as literal IDs).
- External citations: add per `[cites_external](cites_external)` with `key`, `title`, optional `authors`, `year`, `venue`, `doi`, `url`.
- Term definitions: add `[defines](defines)` with `id`, `label`, optional `description`, `aliases`.
- Validation rules are enforced by `rrpr/frontmatter_parser.py`.

9) Provenance (Optional but Encouraged)
- Append a “Full Source” appendix with verbatim content, or save as a sibling `.source.org` file for traceability.
- Include `depends_on` to reference prerequisite concepts or documents by ID.

10) Placement and Slug
- Choose the target directory under `txt/scientific-texts/` that best matches domain and subdomain. Keep directory depth ≤3.
- Filename = `<id>.md` (or a closely matching slug). Keep `id` and filename consistent.

11) Quality Gates
- Frontmatter passes validation (no parser errors).
- Thesis is front‑center; constructs map to variables/functions in a clear synthesis.
- Includes parameter regimes, at least one lemma, and at least one demonstration (table or numeric walk‑through).
- Defines any new terms in `[defines](defines)`; includes `cites_internal` for RRPR docs.
- Adds measurement appendix with at least one operational proxy.

12) Ingestion (Optional)
- `python -m rrpr.cli.main ingest file <path>` to create RelCells/edges; inspect with `python -m rrpr.cli.main stats` or `... list documents`.

Examples
- Structure/model pattern: `txt/scientific-texts/sociology/contemporary/mapping-the-neurotic-platform-intellectual.md`.
- Theorem structure: `txt/scientific-texts/information/theorem-of-necessary-misalignment-of-truth-value-under-epistemic-constraint.md`.

Checklists
- Frontmatter
  - id (lowercase, hyphen/dot ok), title present
  - status, document_type valid (see enums above)
  - authors[], dates ISO
  - topics[], disciplines[]
  - keywords[] present when applicable
  - cites_internal[], [cites_external](cites_external) blocks valid
  - [defines](defines) present for any new concept terms

- Body
  - Abstract ≤ 150 words, names the thesis
  - Thesis box (0.) present and sharp
  - Foundations include Mechanism → Observables → Mapping
  - Synthesis names variables/functions; parameter regimes and lemmas present
  - Mechanism + demonstrations included (at least one table)
  - Patterns, practices, measurement, and ethics included
  - Conclusion restates contributions and levers

Notes for Agents
- Do not silently drop content. If condensing, preserve the source in a `.source.org` sibling.
- Prefer precise, checkable claims; cite internal IDs, not filenames.
- Name constructs and use the same names in math; make the math prove a behavior flip or bound.
- If a section feels repetitive, move definitions to synthesis or the glossary rather than restating them.
