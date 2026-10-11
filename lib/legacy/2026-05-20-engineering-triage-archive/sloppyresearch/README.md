The Relational Research Program Repository (RRPR) is a working lab for Relationing — a mathematical and practical program (influenced by Lakota cosmogeny) that unifies topology and dynamics into operational research.

What lives here
- content/: the research corpus (flat files — Markdown, images, etc.)
  - content/relationing/… and content/mathematics/… hold manuscripts by discipline
  - content/docs/ contains agent/dev guides; content/triage/ is human intake
- code/: the RRP interface (headless Python toolkit) and scripts
  - code/rrp/ is the package (models, parsers, ingestors, queries, publish, CLI)
  - code/scripts/ holds CLI shims and small utilities
- data/: wipeable runtime state (e.g., data/databases/rsc.db + backups)
- pub/: published outputs (PDF/HTML/JSON)
- Root invariants: replit.md, README.md, Makefile, pyproject.toml, AGENTS.md, LICENSE

Getting started
1) Install dependencies
   - make install  # pandoc/XeLaTeX + Python deps (incl. panflute)
2) Use a branch‑local database (isolated per agent/branch)
   - python -m rrp.cli.main db switch --branch "$(git rev-parse --abbrev-ref HEAD)"
3) Publish a dry‑run of documents
   - python -m rrp.cli.main publish docs --dry-run

Conventions we follow
- Co‑located issues live beside the files they concern (content/…/issues/ or code/rrp/issues/)
- All research is plain files under content/ (no notebooks in code/)
- Code stays headless and functional where possible; CLIs and web are thin wrappers
- Rewrites and moves happen atomically and are documented in replit.md

License
- Code: MIT (see LICENSE)
- Documents: individual files may specify their own license

Citation
@online{emsenn_RRPR_2025,
  author = {emsenn},
  title  = {Relational Research Program Repository},
  url    = {https://github.com/emsenn/rrpr},
  year   = {2025},
  license= {MIT}
}
