++
id = "guide.authoring-checklist"
title = "Relationing Paper Authoring Checklist"
status = "active"
document_type = "checklist"
topics = ["authoring", "papers"]
keywords = ["thesis", "structure", "measurement"]
origin_issue = "Issue-K"
++

# Relationing Paper Authoring Checklist

Use this workflow when turning exploratory notes into a thesis-centered Relationing paper. Each step can be validated by lint tools or peer review; treat it as a reproducible runbook.

## Pre-Work
- Read relevant notes and list core claims, terms, and audience.
- Draft a concise thesis statement (claim → mechanism → consequence).

## Thesis & Structure
- Write the abstract and insert a `0. Thesis (Claim → Mechanism → Consequence → Contributions)` box immediately after it.
- Base the document on `docs/templates/rrpr_paper_template.md`; keep IDs/filenames aligned.

## Foundations & Mapping
- For each foundation, capture **Mechanism**, **Observables**, and **Variable Mapping** (e.g., `i, σ, φ`).
- Add a “Theory→Model Synthesis” table linking constructs to variables/functions.

## Lemmas & Regimes
- Include at least one lemma proving a behavioral flip (generation vs resistance, stability vs drift).
- Provide a “Regimes” box summarizing actionable levers.

## Mechanism & Demonstrations
- Derive partials for the reduced-form model; show how levers move outcomes.
- Add at least one worked demonstration (principal–agent, selection dynamics, or time-step table).

## Patterns & Practices
- Provide a “What to Look For” checklist, platform regime heuristic, and typology.
- List recommended practices plus an example timeline.

## Measurement & Ethics
- Append a measurement section: proxies, thresholds, composite red-flag.
- Include an ethics/position note when helpful.

## Frontmatter & Citations
- Required TOML: `id`, `title`, `authors`, `date_created`, `date_modified`, `status`, `document_type`, `topics`, `keywords`.
- Include `cites_internal`, optional `[cites_external](cites_external)`, and `[defines](defines)` entries for new terms.
- Add `depends_on`/`builds_on` for lineage tracking.

## Provenance & Tools
- Save `.source.org` excerpts when condensing; mention them in appendices.
- Use `python -m rrpi.cli.main authoring scaffold|lint` to validate structure (or `scripts/rrpr-cli.py authoring ...`).
- When rendering via Pandoc, include `--filter rrpr-relationing-filter` (see `manifold/docs/dev-guides/relationing-markdown-filter.md`) so relational syntax is preserved.

## Completion Gate
- Frontmatter validates via `src/code/rrpi/frontmatter_parser.py`.
- Thesis box, foundations, synthesis table, lemmas, demonstrations, measurement appendix, and citations are all present.
