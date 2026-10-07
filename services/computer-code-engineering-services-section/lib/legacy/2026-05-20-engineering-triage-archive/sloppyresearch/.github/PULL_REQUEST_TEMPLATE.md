Title: <short thesis-style description>

Summary
- Thesis (one sentence):
- Mechanism (why it happens):
- Consequence (what changes):
- Contributions (bullets):

Changes
- Paper(s):
  - Path(s):
  - Status: draft|working|canonical
- Docs:
  - Procedure/Checklist/Template updates:
- Tooling:
  - CLI authoring: scaffold/lint/from-note
  - Ingestion/DB (if any):

Validation
- Frontmatter lint: `python3 code/apps/cli.py authoring lint <paper>` → OK/Errors
- Structure checks: Thesis box, Foundations, Synthesis, Regimes/Lemmas, Demonstrations, Measurement, Ethics
- Optional ingest: `python3 code/apps/cli.py ingest file <paper>` then `stats`

Notes
- Provenance handled (.source.org or appendix).
- Backward compatibility: no schema changes without migration.
