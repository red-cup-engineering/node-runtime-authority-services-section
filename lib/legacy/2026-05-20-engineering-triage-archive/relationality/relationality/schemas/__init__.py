"""
Schema loading utilities.

Schemas live under ``relationality/schemas``.  They are part of the normative
typing discipline and must be loaded verbatim; no derived or inferred schemas
are allowed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


SCHEMA_DIR = Path(__file__).resolve().parent


def schema_path(name: str) -> Path:
    """
    Compute the on-disk path to a schema.
    """
    return SCHEMA_DIR / name


def load_schema(name: str) -> dict[str, Any]:
    """
    Load a JSON or YAML schema by filename.

    The loader does not cache schemas to avoid hidden state; callers should
    manage reuse explicitly if desired.
    """
    path = schema_path(name)
    if not path.exists():
        raise FileNotFoundError(f"schema {name} not found at {path}")
    if path.suffix in {".json"}:
        return json.loads(path.read_text())
    if path.suffix in {".yaml", ".yml"}:
        return yaml.safe_load(path.read_text())
    raise ValueError(f"unsupported schema extension for {name}")
