"""
Semiotic universe tooling.

This package contains:
- core datamodel + semantics (`model`, `semantics`, `linting`),
- loaders that construct universes from concrete backends
  (currently markdown via `markdown_universe`), and
- publishers that render universes into external views
  (`universe_publish`) plus CLI orchestration (`cli`, `site_publish`).

It replaces the original single‑file `semiotic_site.py` script; new
tools should import from `src.*` modules and invoke `src.cli` for
command‑line entrypoints.
"""
