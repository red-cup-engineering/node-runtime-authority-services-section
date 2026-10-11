from __future__ import annotations

"""
Generate docs/math/content/instruction_set.json from the live rewriter registry.

This script inspects the HandlerRegistry and ACT_BINDINGS to produce a
machine-readable map from earned act slugs to their implementation details:
handler module/class and, where available, input/output carrier schemas.

Usage:
    python scripts/generate_instruction_set.py

Requires the application dependencies (including pydantic) to be installed so
that app.rewriter.* and app.schemas.* can be imported.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from app.rewriter.act_bindings import ACT_BINDINGS, ActBinding
from app.rewriter.handlers import HandlerRegistry


ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "docs" / "math" / "content"
GRAPH_JSON = DOCS_ROOT / "graph.json"
OUT_PATH = DOCS_ROOT / "instruction_set.json"


def schema_name(schema: Optional[Type[Any]]) -> Optional[str]:
    if schema is None:
        return None
    return getattr(schema, "__name__", repr(schema))


def main() -> None:
    registry = HandlerRegistry.get_instance()

    # Access the internal handler map; this is a deliberate introspection for
    # documentation purposes, not part of normal runtime behaviour.
    handlers: Dict[str, Any] = getattr(registry, "_handlers", {})

    # Optionally enrich act entries with their supporting theorems/specs/arch
    # from the documentation DAG, if the generated graph is present.
    doc_graph: Dict[str, Any] = {"nodes": [], "edges": []}
    node_index: Dict[str, Dict[str, Any]] = {}
    incoming_to_act: Dict[str, List[str]] = {}
    if GRAPH_JSON.exists():
        doc_graph = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
        for node in doc_graph.get("nodes", []):
            node_index[node["id"]] = node
        for edge in doc_graph.get("edges", []):
            src = edge["src"]
            dst = edge["dst"]
            incoming_to_act.setdefault(dst, []).append(src)

    instruction_set: Dict[str, Dict[str, Any]] = {}

    for act, handler in sorted(handlers.items()):
        cls = handler.__class__
        mod = cls.__module__
        name = cls.__name__

        binding: Optional[ActBinding] = ACT_BINDINGS.get(act)
        input_schema = schema_name(binding.input_schema) if binding else None
        output_schema = schema_name(binding.output_schema) if binding else None

        doc_id = f"act:{act}"
        supporters = incoming_to_act.get(doc_id, [])
        internal_theorems: List[str] = []
        external_theorems: List[str] = []
        specifications: List[str] = []
        architectures: List[str] = []
        for src in supporters:
            node = node_index.get(src)
            if not node:
                continue
            node_type = node.get("type")
            if node_type == "internal":
                internal_theorems.append(src)
            elif node_type == "external":
                external_theorems.append(src)
            elif node_type == "specification":
                specifications.append(src)
            elif node_type == "architecture":
                architectures.append(src)

        instruction_set[act] = {
            "handler_module": mod,
            "handler_class": name,
            "input_schema": input_schema,
            "output_schema": output_schema,
            "docs": {
                "internal_theorems": sorted(internal_theorems),
                "external_theorems": sorted(external_theorems),
                "specifications": sorted(specifications),
                "architectures": sorted(architectures),
            },
        }

    OUT_PATH.write_text(
        json.dumps(instruction_set, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote instruction set for {len(instruction_set)} acts to {OUT_PATH}")


if __name__ == "__main__":
    main()
