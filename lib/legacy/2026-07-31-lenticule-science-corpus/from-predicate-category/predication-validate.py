"""Validate the metadata coherence of all registered Python ↔ markdown links.

Walks every per-note Python module to force decorator registration, then
checks each registered link against the corpus filesystem:

- The target markdown note exists.
- For `verifies` links with `pass_=N`, the markdown contains a "Pass N" section.
- (Future: cross-check that the markdown's `verified_by:` frontmatter matches
  the registry.)

Usage: `python -m predication_categories.validate` (run from the chapter root).

Exits with non-zero status if any check fails.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
import sys
from pathlib import Path

from . import link as link_module


def _walk_subpackage(pkg_name: str) -> None:
    """Import every submodule of a sub-package to register decorators."""
    pkg = importlib.import_module(f"predication_categories.{pkg_name}")
    if not hasattr(pkg, "__path__"):
        return
    for module_info in pkgutil.walk_packages(pkg.__path__, prefix=f"predication_categories.{pkg_name}."):
        importlib.import_module(module_info.name)


def force_register_all() -> None:
    """Import every per-note module to force decorator registration."""
    for sub in ("primitives", "examples", "theorems", "objects", "morphisms"):
        try:
            _walk_subpackage(sub)
        except ModuleNotFoundError:
            # Subpackage doesn't exist yet — fine.
            continue


def corpus_root() -> Path:
    """Return the corpus chapter root (the directory containing `tools/`,
    `theorems/`, `examples/`, etc.).

    This module lives at `<root>/tools/predication_categories/validate.py`.
    """
    return Path(__file__).parent.parent.parent


def validate_link_targets() -> list[str]:
    """For each registered link, check the target markdown note exists.

    Returns a list of error strings; empty list means all links are valid.
    """
    errors: list[str] = []
    root = corpus_root()
    for link in link_module.all_links():
        target_path = root / link.target
        if not target_path.exists():
            errors.append(
                f"link target missing: {link.target} (kind={link.kind}, "
                f"obj={link.obj.__qualname__ if hasattr(link.obj, '__qualname__') else link.obj})"
            )
    return errors


def validate_pass_metadata() -> list[str]:
    """For `verifies` links with `pass_=N` metadata, check the markdown note
    actually contains a `Pass N` section."""
    errors: list[str] = []
    root = corpus_root()
    for link in link_module.all_links():
        if link.kind != "verifies":
            continue
        meta = dict(link.metadata)
        pass_n = meta.get("pass_")
        if pass_n is None:
            continue
        target_path = root / link.target
        if not target_path.exists():
            continue
        body = target_path.read_text(encoding="utf-8")
        # Accept any heading level: "## Pass N", "### Pass N", etc.
        # Word boundary after N handles both "Pass 2 (...)" and "Pass 2 — ...".
        if not re.search(rf"^#+\s+Pass {pass_n}\b", body, flags=re.MULTILINE):
            errors.append(
                f"verifies({link.target}, pass_={pass_n}) registered but markdown has no `Pass {pass_n}` heading"
            )
    return errors


def main() -> int:
    force_register_all()

    print(f"Total registered links: {len(link_module.all_links())}")

    errors: list[str] = []
    errors.extend(validate_link_targets())
    errors.extend(validate_pass_metadata())

    if not errors:
        print("All link metadata is coherent.")
        return 0

    print(f"\n{len(errors)} validation error(s):")
    for err in errors:
        print(f"  - {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
