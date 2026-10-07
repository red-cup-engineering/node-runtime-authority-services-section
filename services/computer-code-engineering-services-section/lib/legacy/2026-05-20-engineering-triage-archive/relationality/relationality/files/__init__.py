"""
Filesystem CRUD for serialized AOG artifacts (objects, runbooks, systems).

This package will be used by the runtime to load/validate/write carriers and
runbooks from the data/ directory. The API surface is intentionally narrow and
typed to allow later integration with the AOG boot sequence.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Dict, List, Optional

import orjson
import yaml
from jsonschema import ValidationError, validators


DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data"
SCHEMA_PKG = "relationality.schemas"


def _canonical_signature(kind: str, acts: List[str], payload: Dict[str, object]) -> str:
    material = {"kind": kind, "acts": sorted(acts), "payload": payload}
    data = orjson.dumps(material, option=orjson.OPT_SORT_KEYS)
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path) -> Dict:
    with path.open("rb") as handle:
        return orjson.loads(handle.read())


def _load_yaml(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_schema(name: str) -> Dict:
    try:
        schema_path = resources.files(SCHEMA_PKG).joinpath(name)
    except Exception as exc:
        raise FileNotFoundError(f"Schema package not available for {name}") from exc
    if not schema_path.is_file():
        raise FileNotFoundError(f"Schema not found: {name}")
    if schema_path.suffix in {".yaml", ".yml"}:
        return yaml.safe_load(schema_path.read_text())
    return orjson.loads(schema_path.read_bytes())


def _validate(instance: Dict, schema_name: str) -> None:
    schema = _load_schema(schema_name)
    cls = validators.validator_for(schema)
    cls.check_schema(schema)
    cls(schema).validate(instance)


def _verify_signature(kind: str, acts: List[str], payload: Dict[str, object], signature: Optional[str]) -> None:
    if signature is None:
        return
    expected = _canonical_signature(kind, acts, payload)
    if signature != expected:
        raise ValidationError(f"Signature mismatch for kind {kind}: expected {expected}, found {signature}")


@dataclass
class SerializedObject:
    id: str
    kind: str
    acts: List[str]
    payload: Dict[str, object]
    signature: Optional[str] = None


@dataclass
class SerializedRunbook:
    id: str
    name: str
    input_kind: str
    output_kind: str
    steps: List[Dict[str, object]]
    acts: List[str]
    signature: Optional[str] = None


def load_objects(data_root: Path | None = None) -> List[SerializedObject]:
    base = data_root or DATA_ROOT
    objects_dir = base / "objects"
    objects: List[SerializedObject] = []
    for path in sorted(objects_dir.glob("*.object.json")):
        raw = _load_json(path)
        _validate(raw, "object.schema.json")
        _verify_signature(raw.get("kind", ""), raw.get("acts", []), raw.get("payload", {}), raw.get("signature"))
        objects.append(
            SerializedObject(
                id=raw["id"],
                kind=raw["kind"],
                acts=raw.get("acts", []),
                payload=raw["payload"],
                signature=raw.get("signature"),
            )
        )
    return objects


def load_runbooks(data_root: Path | None = None) -> List[SerializedRunbook]:
    base = data_root or DATA_ROOT
    runbooks_dir = base / "runbooks"
    books: List[SerializedRunbook] = []
    for path in sorted(runbooks_dir.glob("*.yaml")):
        raw = _load_yaml(path)
        _validate(raw, "runbook.schema.yaml")
        _verify_signature(raw.get("input_kind", ""), raw.get("acts", []), {"steps": raw.get("steps", [])}, raw.get("signature"))
        books.append(
            SerializedRunbook(
                id=raw["id"],
                name=raw["name"],
                input_kind=raw["input_kind"],
                output_kind=raw["output_kind"],
                steps=raw.get("steps", []),
                acts=raw.get("acts", []),
                signature=raw.get("signature"),
            )
        )
    return books


def load_systems(data_root: Path | None = None) -> List[Dict]:
    base = data_root or DATA_ROOT
    systems_dir = base / "objects"
    systems: List[Dict] = []
    for path in sorted(systems_dir.glob("*.system.object.json")):
        raw = _load_json(path)
        _validate(raw, "system.schema.json")
        _verify_signature(raw.get("id", ""), [], raw, raw.get("signature"))
        systems.append(raw)
    return systems


def write_object(obj: SerializedObject, data_root: Path | None = None) -> Path:
    base = data_root or DATA_ROOT
    path = base / "objects" / f"{obj.id}.object.json"
    data = {
        "id": obj.id,
        "kind": obj.kind,
        "acts": obj.acts,
        "payload": obj.payload,
    }
    data["signature"] = obj.signature or _canonical_signature(obj.kind, obj.acts, obj.payload)
    _validate(data, "object.schema.json")
    path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    return path


def write_runbook(runbook: SerializedRunbook, data_root: Path | None = None) -> Path:
    base = data_root or DATA_ROOT
    path = base / "runbooks" / f"{runbook.id}.yaml"
    data = {
        "id": runbook.id,
        "name": runbook.name,
        "input_kind": runbook.input_kind,
        "output_kind": runbook.output_kind,
        "steps": runbook.steps,
        "acts": runbook.acts,
    }
    data["signature"] = runbook.signature or _canonical_signature(runbook.input_kind, runbook.acts, {"steps": runbook.steps})
    _validate(data, "runbook.schema.yaml")
    path.write_text(yaml.safe_dump(data))
    return path
