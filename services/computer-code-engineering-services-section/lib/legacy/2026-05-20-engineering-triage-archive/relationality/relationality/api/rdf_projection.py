from __future__ import annotations

"""
RDF projections for AOG carriers.

This module provides read-only projections of carrier payloads into RDF
and JSON-LD, without introducing any new runtime state or semantics.
Projections are deterministic functions of the existing carriers.
"""

from typing import Any, Dict, Iterable, Mapping, Sequence


BASE_IRI = "https://relationality.emsenn.net/aog/"


def _node_iri(node_id: str) -> str:
    return f"{BASE_IRI}node/{node_id}"


def _escape_literal(value: str) -> str:
    """
    Minimal Turtle literal escaping for double quotes and backslashes.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


def carriers_to_turtle(
    carriers: Sequence[Mapping[str, Any]],
    node_ids: Iterable[str],
    header_lines: Sequence[str] | None = None,
) -> str:
    """
    Render a collection of carriers as Turtle triples.

    ``node_ids`` is the universe of IDs that should be treated as IRIs
    when encountered as string values in fields.
    """
    node_id_set = set(node_ids)
    lines: list[str] = []
    if header_lines:
        lines.extend(header_lines)

    for node in sorted(carriers, key=lambda n: n["id"]):
        nid = node["id"]
        kind = node.get("kind", "")
        subject = f"<{_node_iri(nid)}>"
        lines.append("")
        lines.append(f"{subject} a <{BASE_IRI}kind/{kind}> .")

        for key, value in node.items():
            if key in {"id", "kind"}:
                continue
            predicate = f"<{BASE_IRI}prop/{key}>"

            def emit_object(val: Any) -> None:
                if isinstance(val, str) and val in node_id_set:
                    lines.append(f"{subject} {predicate} <{_node_iri(val)}> .")
                elif isinstance(val, (int, float, bool)):
                    lit = _escape_literal(str(val))
                    lines.append(f'{subject} {predicate} "{lit}" .')
                elif isinstance(val, dict):
                    # Nested structures are emitted as canonical JSON literals.
                    import json

                    lit = _escape_literal(json.dumps(val, sort_keys=True, separators=(",", ":")))
                    lines.append(f'{subject} {predicate} "{lit}" .')
                elif isinstance(val, list):
                    for item in val:
                        emit_object(item)
                else:
                    lit = _escape_literal(str(val))
                    lines.append(f'{subject} {predicate} "{lit}" .')

            emit_object(value)

    return "\n".join(lines) + "\n"


def _value_to_jsonld(val: Any, node_ids: Iterable[str]) -> Any:
    """
    Convert a JSON value into a JSON-LD compatible structure.

    Any string equal to a node ID in the System subgraph is mapped to an
    IRI reference; other values are left as JSON scalars or nested
    objects.
    """
    if isinstance(val, str) and val in node_ids:
        return {"@id": _node_iri(val)}
    if isinstance(val, list):
        return [_value_to_jsonld(item, node_ids) for item in val]
    if isinstance(val, dict):
        return {k: _value_to_jsonld(v, node_ids) for k, v in val.items()}
    return val


def carriers_to_jsonld(
    carriers: Sequence[Mapping[str, Any]],
    objects_by_id: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """
    Render a collection of carriers as a JSON-LD document.

    This is used to provide JSON-LD views of the canonical JSON API
    (e.g. /systems and /systems/{id}) via content negotiation. Carriers
    are treated as nodes; any string field equal to a known object ID is
    rendered as an IRI reference.
    """
    node_ids = set(objects_by_id.keys())
    context = {
        "@vocab": f"{BASE_IRI}prop/",
        "rel": BASE_IRI,
    }
    graph_nodes: list[Dict[str, Any]] = []
    for carrier in sorted(carriers, key=lambda n: n["id"]):
        nid = carrier["id"]
        kind = carrier.get("kind", "")
        node: Dict[str, Any] = {
            "@id": _node_iri(nid),
            "@type": [f"{BASE_IRI}kind/{kind}"],
        }
        for key, value in carrier.items():
            if key in {"id", "kind"}:
                continue
            node[key] = _value_to_jsonld(value, node_ids)
        graph_nodes.append(node)
    return {
        "@context": context,
        "@graph": graph_nodes,
    }
