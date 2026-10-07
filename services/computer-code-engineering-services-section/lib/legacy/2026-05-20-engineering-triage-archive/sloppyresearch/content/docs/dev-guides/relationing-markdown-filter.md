++
id = "guide.relationing-markdown-filter"
title = "Relationing Markdown Filter"
status = "active"
document_type = "guide"
topics = ["relationing", "pandoc", "tooling"]
keywords = ["markdown", "scope", "pandoc-filter"]
++

# Relationing Markdown Filter

The filter lives at `code/rrp/filters/relationing.py` and is exposed as the CLI command `rrp-relationing-filter`. It extends Markdown with scoped relational syntax that aligns with the Relationing knowledge graph.

## Capabilities

- `#Word` / `##Word{...}` — reference or define RelCells and Morphisms.
- `#open-scope{...}` / `#close-scope` — create scoped ontologies; scopes inherit arguments and can be promoted/exported.
- Cross-scope edges via `src=Scope:Entity` and `dst=Scope:Entity`, with policy controlled by `cross_scope: allow|warn|deny`.
- Registry loading for supplemental corpora (Markdown, JSON-LD, Turtle, CSV, DOT).
- Linting/report writing with soft/strict modes, severity controls, and optional JSON/YAML reports.
- Emit graph data directly (`--metadata emit=ttl|jsonld|dot|csv`) as part of the Pandoc pipeline.

## Running with Pandoc

```bash
pandoc input.md \
  --filter rrp-relationing-filter \
  --metadata lint_mode=strict \
  --metadata cross_scope=warn \
  -o output.pdf
```

Common metadata keys (pass via `--metadata key=value` or frontmatter):

| Key | Purpose |
| --- | --- |
| `registry` | List of corpus files to load (`md`, `jsonld`, `ttl`, `csv`, `dot`) |
| `lint_mode` | `soft` (default) or `strict` exit codes |
| `lint.{rule}` | Override severity (`ignore`, `warn`, `error`) per rule |
| `cross_scope` | Policy for cross-scope links (`allow`, `warn`, `deny`) |
| `report` | Path to emit lint report (`.json`, `.yaml`, `.txt`) |
| `emit` | Export format (`jsonld`, `ttl`, `dot`, `csv`) |
| `emit_mode` | `contextual`, `merged`, or `flattened` |
| `emit_scopes` | `true` to emit each scope individually (requires `emit_scopes_dir`) |

## Development Notes

- The filter is regular Python; run `python -m rrp.filters.relationing --help` to verify dependencies (requires `panflute`).
- Keep the relational syntax in sync with documentation in this guide and `content/relationing/research/methods/paper-authoring/relational-research-paper-specification.md`.
- Tests can stub panflute documents by calling `rrp.filters.relationing.main(doc=my_panflute_doc)`.
