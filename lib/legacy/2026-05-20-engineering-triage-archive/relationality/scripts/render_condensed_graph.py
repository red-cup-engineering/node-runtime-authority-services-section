from __future__ import annotations

import json
import subprocess
from collections import defaultdict, deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAPH_JSON = ROOT / "docs" / "math" / "content" / "graph.json"
DOT_OUT = ROOT / "docs" / "math" / "content" / "graph_condensed.dot"
SVG_OUT = ROOT / "docs" / "math" / "content" / "graph_condensed.svg"


def safe_id(identifier: str) -> str:
    return identifier.replace(":", "_").replace("/", "_")


def main() -> None:
    data = json.loads(GRAPH_JSON.read_text())
    nodes = {node["id"]: node for node in data["nodes"]}
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in data["edges"]:
        adj[edge["src"]].append(edge["dst"])

    # Map acts to their parent internal theorems
    act_parents: dict[str, list[str]] = defaultdict(list)
    for src, dst_list in adj.items():
        if nodes.get(src, {}).get("type") != "internal":
            continue
        for dst in dst_list:
            if dst.startswith("act:"):
                act_parents[dst].append(src)

    internal_nodes = [
        node_id for node_id, node in nodes.items() if node.get("type") == "internal"
    ]
    specification_nodes = [
        node_id
        for node_id, node in nodes.items()
        if node.get("type") == "specification"
    ]
    architecture_nodes = [
        node_id for node_id, node in nodes.items() if node.get("type") == "architecture"
    ]
    act_nodes = [
        node_id for node_id, node in nodes.items() if node.get("type") == "act"
    ]

    def resolve_spec_targets(spec_id: str) -> set[str]:
        """Return set of internal theorem ids reachable from spec via externals."""
        targets: set[str] = set()
        queue = deque(adj.get(spec_id, []))
        visited: set[str] = set()
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            node = nodes.get(current)
            if not node:
                continue
            node_type = node.get("type")
            if node_type == "internal":
                targets.add(current)
            elif node_type == "external":
                for nxt in adj.get(current, []):
                    queue.append(nxt)
        return targets

    lines: list[str] = ["digraph G {", "  rankdir=LR;", "  node [shape=box];"]

    # Add specification nodes
    for spec_id in specification_nodes:
        node = nodes[spec_id]
        label = f"{node.get('title', spec_id)}\\n(spec)"
        lines.append(
            f'  "{safe_id(spec_id)}" [label="{label}", shape=hexagon, color="#005f73"];'
        )

    # Add architecture nodes
    for arch_id in architecture_nodes:
        node = nodes[arch_id]
        label = f"{node.get('title', arch_id)}\\n(arch)"
        lines.append(
            f'  "{safe_id(arch_id)}" [label="{label}", shape=folder, style="filled", fillcolor="#ffd166", color="#b26f00"];'
        )

    # Add internal clusters
    rendered_act_nodes: set[str] = set()

    for idx, internal_id in enumerate(sorted(internal_nodes)):
        node = nodes[internal_id]
        cluster_name = f"cluster_{idx}"
        lines.append(f"  subgraph {cluster_name} {{")
        lines.append("    style=filled;")
        lines.append('    color="#eeeeee";')
        internal_label = f"{node.get('title', internal_id)}"
        internal_node_id = safe_id(internal_id)
        lines.append(
            f'    "{internal_node_id}" [label="{internal_label}\\n(internal)", shape=rectangle, color="#333333", fontcolor="#333333"];'
        )
        for act_id, parents in act_parents.items():
            if internal_id not in parents:
                continue
            act_node = nodes.get(act_id)
            if not act_node:
                continue
            act_label = act_node.get("title", act_id)
            if act_id not in rendered_act_nodes:
                lines.append(
                    f'    "{safe_id(act_id)}" [label="{act_label}\\n(act)", shape=oval, color="#777777"];'
                )
                rendered_act_nodes.add(act_id)
            lines.append(f'    "{internal_node_id}" -> "{safe_id(act_id)}";')
        lines.append("  }")

    # Orphan acts (no internal parent in this view)
    for act_id in sorted(set(act_nodes) - rendered_act_nodes):
        act_node = nodes.get(act_id)
        if not act_node:
            continue
        act_label = act_node.get("title", act_id)
        lines.append(
            f'  "{safe_id(act_id)}" [label="{act_label}\\n(act)", shape=oval, color="#777777"];'
        )

    # Connect specs to internal nodes (resolving through externals)
    for spec_id in specification_nodes:
        targets = resolve_spec_targets(spec_id)
        for internal_id in targets:
            lines.append(
                f'  "{safe_id(spec_id)}" -> "{safe_id(internal_id)}" [color="#336699"];'
            )

    # Connect internal theorems to other internal theorems (use direct edges)
    for src in internal_nodes:
        for dst in adj.get(src, []):
            if nodes.get(dst, {}).get("type") == "internal":
                lines.append(
                    f'  "{safe_id(src)}" -> "{safe_id(dst)}" [style=dashed, color="#888888"];'
                )

    # Connect architecture nodes to specifications (ignore architecture-to-architecture)
    for arch_id in architecture_nodes:
        targets = [
            dst
            for dst in adj.get(arch_id, [])
            if nodes.get(dst, {}).get("type") == "specification"
        ]
        for target in targets:
            lines.append(
                f'  "{safe_id(arch_id)}" -> "{safe_id(target)}" [color="#8d0801"];'
            )

    # Connect acts to their top/bottom references
    for act_id in act_nodes:
        for dst in adj.get(act_id, []):
            if nodes.get(dst, {}).get("type") == "act":
                lines.append(
                    f'  "{safe_id(act_id)}" -> "{safe_id(dst)}" [color="#999999"];'
                )

    lines.append("}")
    DOT_OUT.write_text("\n".join(lines))

    # Render SVG
    subprocess.run(
        ["dot", "-Tsvg", str(DOT_OUT), "-o", str(SVG_OUT)],
        check=True,
        cwd=ROOT,
    )


if __name__ == "__main__":
    main()
