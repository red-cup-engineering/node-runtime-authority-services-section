"""
Data-layer loaders for objects and runbooks.

These loaders are intentionally strict: filenames must match IDs, payloads must
validate against schemas, and canonical hashes must agree with embedded IDs.
No partial acceptance or silent coercion is allowed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import yaml

from .canonical import assert_id_coherence, ensure_id_coherence
from .validation import validate_object, validate_runbook


OBJECTS_DIR = Path("data/objects")
RUNBOOKS_DIR = Path("data/runbooks")


@dataclass(frozen=True)
class ObjectIndex:
    by_id: Dict[str, dict]
    by_kind: Dict[str, Dict[str, dict]]


@dataclass(frozen=True)
class RunbookIndex:
    by_id: Dict[str, dict]
    by_name: Dict[str, Dict[str, dict]]


def _parse_object_filename(path: Path) -> Tuple[str, str]:
    name = path.name
    if not name.endswith(".object.json"):
        raise ValueError(f"object filename must end with .object.json: {name}")
    parts = name[:-12].split(".")
    if len(parts) != 2:
        raise ValueError(f"object filename must be <id>.<kind>.object.json: {name}")
    obj_id, kind = parts
    return obj_id, kind


def _parse_runbook_filename(path: Path) -> str:
    name = path.name
    if not name.endswith(".runbook.yaml"):
        raise ValueError(f"runbook filename must end with .runbook.yaml: {name}")
    return name[:-13]


def load_object_file(path: Path) -> dict:
    """
    Load and validate a single object file.

    This performs:
    - filename ↔ id coherence checks,
    - canonical ID coherence, and
    - schema + carrier-local law validation via ``validate_object``.

    It deliberately does **not** enforce graph-level laws (Flow/Nucleus/
    System, geometry_profile, runbook laws); those require AOG context
    and are handled at runtime via ``relationality.law_enforcement``.
    """
    obj_id, kind = _parse_object_filename(path)
    payload = json.loads(path.read_text())
    if payload.get("kind") != kind:
        raise ValueError(f"kind mismatch for {path}: expected {kind}, found {payload.get('kind')}")
    assert_id_coherence(payload)
    if payload["id"] != obj_id:
        raise ValueError(f"id mismatch for {path}: filename {obj_id} vs payload {payload['id']}")
    validate_object(payload)
    return payload


def load_runbook_file(path: Path) -> dict:
    """
    Load and validate a single runbook file.

    This enforces:
    - filename ↔ id coherence,
    - canonical ID coherence, and
    - structural typing via ``validate_runbook``.

    Algebraic runbook laws (operator sequencing, regime suppression,
    etc.) are enforced separately by the law layer, not by the loader.
    """
    runbook_id = _parse_runbook_filename(path)
    raw_payload = yaml.safe_load(path.read_text())
    payload = dict(raw_payload)
    assert_id_coherence(payload)
    if payload["id"] != runbook_id:
        raise ValueError(f"id mismatch for {path}: filename {runbook_id} vs payload {payload['id']}")
    validate_runbook(payload)
    return payload


def load_objects(directory: Path = OBJECTS_DIR) -> ObjectIndex:
    """
    Load all object files in a directory keyed by their IDs.
    """
    objects: Dict[str, dict] = {}
    if not directory.exists():
        return ObjectIndex(by_id=objects, by_kind={})
    for path in directory.glob("*.object.json"):
        payload = load_object_file(path)
        objects[payload["id"]] = payload
    by_kind: Dict[str, Dict[str, dict]] = {}
    for obj in objects.values():
        by_kind.setdefault(obj["kind"], {})[obj["id"]] = obj
    return ObjectIndex(by_id=objects, by_kind=by_kind)


def load_runbooks(directory: Path = RUNBOOKS_DIR) -> RunbookIndex:
    """
    Load all runbook files in a directory keyed by their IDs.
    """
    runbooks: Dict[str, dict] = {}
    if not directory.exists():
        return RunbookIndex(by_id=runbooks, by_name={})
    for path in directory.glob("*.runbook.yaml"):
        payload = load_runbook_file(path)
        runbooks[payload["id"]] = payload
    by_name: Dict[str, Dict[str, dict]] = {}
    for rb in runbooks.values():
        by_name.setdefault(rb["name"], {})[rb["id"]] = rb
    return RunbookIndex(by_id=runbooks, by_name=by_name)
