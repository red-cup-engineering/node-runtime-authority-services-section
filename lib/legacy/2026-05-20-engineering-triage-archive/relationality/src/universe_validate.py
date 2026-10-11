from __future__ import annotations

"""
Universe validation entrypoints.

This module provides a focused interface for validating universes
loaded from markdown vaults (or other backends in future) without
exporting any views.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .linting import lint_universe
from .markdown_universe import build_universe, load_config
from .model import Config


@dataclass
class ValidateOptions:
    config_path: Optional[Path] = None
    vault_dir: Optional[Path] = None
    strict: bool = True


def validate_vault(options: ValidateOptions) -> None:
    """Validate a vault: build the universe and run linting."""

    config = load_config(options.config_path) if options.config_path else Config()
    if options.vault_dir is not None:
        config.vault_dir = str(options.vault_dir)

    vault_arg = options.vault_dir or (Path(config.vault_dir) if config.vault_dir else None)
    if vault_arg is None:
        raise SystemExit("Vault directory must be provided via options or config.")

    vault_dir = Path(vault_arg).resolve()
    universe = build_universe(vault_dir, config, log=(lambda m: print(f"[phase] {m}")))
    print(f"[{config.site_title}] Loaded {len(universe.concepts)} concepts; {len(universe.atoms)} atoms.")

    try:
        lint_universe(universe)
    except SystemExit as exc:
        if options.strict or config.lint_strict:
            raise
        print(str(exc))


__all__ = ["ValidateOptions", "validate_vault"]

