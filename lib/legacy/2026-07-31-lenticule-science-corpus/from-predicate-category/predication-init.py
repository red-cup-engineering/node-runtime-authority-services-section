"""Computational primitives + per-note verification modules for the
predication-categories corpus.

Three layers:

- `primitives/`: shared mathematical primitives (Bilattice, Frame, DFrame, ...).
  Strictly typed, used by all per-note modules.
- `examples/` / `theorems/` / `objects/`: per-note Python modules mirroring
  the markdown structure. Each module's functions are decorated with
  `link.verifies(...)` / `link.example_of(...)` / `link.defines(...)`
  to register what they correspond to in the corpus.
- `link.py`: the decorator + registry layer. Decorators register only;
  pytest discovery handles execution.

Usage:

    pytest predication_categories/                # run all verifications
    python -m predication_categories.validate     # check link metadata coherence
"""

from .link import defines, verifies, example_of, all_links, links_for

__all__ = ["defines", "verifies", "example_of", "all_links", "links_for"]
