from __future__ import annotations

import sys
from collections import Counter
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "math" / "content"
ACTS_DIR = DOCS / "acts"
TEXTS_DIR = DOCS / "texts"
GRAPH_PATH = DOCS / "graph.json"


def load_frontmatter(path: Path) -> dict:
    """Return the YAML frontmatter for a markdown file (or {} if missing)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    try:
        _, front, _ = text.split("---", 2)
    except ValueError:
        return {}
    data = yaml.safe_load(front)
    return data or {}


def validate_acts(slug_map: dict[str, Path], name_map: dict[str, str], act_refs: list[tuple[str, str]]) -> list[str]:
    errors: list[str] = []
    slugs = Counter()
    for md_path in sorted(ACTS_DIR.glob("*.md")):
        if md_path.name == "index.md":
            continue
        meta = load_frontmatter(md_path)
        rel = md_path.relative_to(ROOT)
        required = ["title", "act", "slug", "summary", "tags"]
        missing = [key for key in required if key not in meta]
        if missing:
            errors.append(f"{rel}: missing keys {missing}")
            continue
        slug = meta["slug"]
        slug_map[slug] = md_path
        act_name = meta.get("act")
        if act_name:
            name_map[act_name] = slug
        for key in ("top", "bottom"):
            ref = meta.get(key)
            if ref and ref != "null":
                act_refs.append((slug, ref))
        slugs[slug] += 1
    # report duplicate slugs
    for slug, count in slugs.items():
        if count > 1:
            errors.append(f"acts: slug '{slug}' appears {count} times")
    return errors


def markdown_files_under(dir_path: Path) -> list[Path]:
    return sorted(p for p in dir_path.rglob("*.md") if p.is_file())


def validate_texts(slug_map: dict[str, Path], graph: dict) -> list[str]:
    errors: list[str] = []
    warnings: list[str] = []
    entries = []
    for md_path in markdown_files_under(TEXTS_DIR):
        if md_path.name == "index.md":
            continue
        rel_root = md_path.relative_to(ROOT)
        rel_text = md_path.relative_to(TEXTS_DIR)
        meta = load_frontmatter(md_path)
        if not meta:
            errors.append(f"{rel_root}: missing frontmatter")
            continue
        title = meta.get("title")
        if not title:
            errors.append(f"{rel_root}: missing 'title'")
        if "tags" not in meta:
            errors.append(f"{rel_root}: missing 'tags'")
        parts = rel_text.parts
        if len(parts) < 2:
            errors.append(f"{rel_root}: invalid text path")
            continue
        category = parts[0]
        if category == "theorem":
            if len(parts) < 3:
                errors.append(f"{rel_root}: invalid theorem path")
                continue
            layer = parts[1]
            if layer not in {"internal", "external"}:
                errors.append(f"{rel_root}: unknown theorem layer '{layer}'")
                continue
            node_type = layer
        elif category == "specifications":
            node_type = "specification"
            layer = "specification"
        elif category == "computer-architecture":
            node_type = "architecture"
            layer = "architecture"
        else:
            errors.append(f"{rel_root}: unknown text category '{category}'")
            continue
        node_id = str(rel_text.with_suffix("")).replace("\\", "/")
        entries.append(
            {
                "path": rel_root,
                "node_id": node_id,
                "title": title,
                "layer": layer,
                "type": node_type,
                "depends": meta.get("depends_on", []) or [],
                "operations": meta.get("operations", []) or [],
            }
        )
    node_types = {}
    for entry in entries:
        graph["nodes"].append(
            {
                "id": entry["node_id"],
                "type": entry["type"],
                "title": entry["title"],
                "path": str(entry["path"]),
            }
        )
        node_types[entry["node_id"]] = entry["type"]
    for entry in entries:
        rel_root = entry["path"]
        layer = entry["type"]
        depends = entry["depends"]
        if not depends:
            warnings.append(f"{rel_root}: missing 'depends_on'")
        for dep in depends:
            if layer == "internal":
                if dep.startswith("theorem/"):
                    target_type = node_types.get(dep)
                    if target_type != "internal":
                        errors.append(
                            f"{rel_root}: internal theorem depends on non-internal '{dep}'"
                        )
                        continue
                    graph["edges"].append(
                        {"src": entry["node_id"], "dst": dep}
                    )
                else:
                    target = slug_map.get(dep)
                    if not target:
                        errors.append(
                            f"{rel_root}: depends_on unknown act slug '{dep}'"
                        )
                        continue
                    graph["edges"].append(
                        {"src": entry["node_id"], "dst": f"act:{dep}"}
                    )
            elif layer == "external":
                target_type = node_types.get(dep)
                if target_type != "internal":
                    errors.append(
                        f"{rel_root}: external theorem depends on non-internal '{dep}'"
                    )
                    continue
                graph["edges"].append(
                    {"src": entry["node_id"], "dst": dep}
                )
            elif layer == "specification":
                target_type = node_types.get(dep)
                if target_type not in {"internal", "external"}:
                    errors.append(
                        f"{rel_root}: specification depends on non-theorem '{dep}'"
                    )
                    continue
                graph["edges"].append(
                    {"src": entry["node_id"], "dst": dep}
                )
            elif layer == "architecture":
                target_type = node_types.get(dep)
                if target_type not in {"specification", "architecture"}:
                    errors.append(
                        f"{rel_root}: architecture node depends on non-spec '{dep}'"
                    )
                    continue
                graph["edges"].append(
                    {"src": entry["node_id"], "dst": dep}
                )
        # operations mapping
        for op in entry["operations"]:
            for act_slug in op.get("acts", []):
                if act_slug not in slug_map:
                    errors.append(
                        f"{rel_root}: operation references unknown act slug '{act_slug}'"
                    )
                    continue
                graph["edges"].append(
                    {"src": entry["node_id"], "dst": f"act:{act_slug}"}
                )
    for warn in warnings:
        print(f"Warning: {warn}")
    return errors


def main() -> int:
    slug_map: dict[str, Path] = {}
    name_map: dict[str, str] = {}
    act_refs: list[tuple[str, str]] = []
    graph = {"nodes": [], "edges": []}
    # add act nodes first
    errors = validate_acts(slug_map, name_map, act_refs)
    for slug, path in slug_map.items():
        rel = path.relative_to(ROOT)
        meta = load_frontmatter(path)
        graph["nodes"].append(
            {
                "id": f"act:{slug}",
                "type": "act",
                "title": meta.get("title"),
                "path": str(rel),
            }
        )
    # act dependency edges (top/bottom)
    for src_slug, ref_name in act_refs:
        target_slug = None
        if ref_name in name_map:
            target_slug = name_map[ref_name]
        elif ref_name in slug_map:
            target_slug = ref_name
        if not target_slug:
            errors.append(
                f"acts: dependency '{ref_name}' referenced by '{src_slug}' not found"
            )
            continue
        graph["edges"].append(
            {"src": f"act:{src_slug}", "dst": f"act:{target_slug}"}
        )
    errors += validate_texts(slug_map, graph)
    if errors:
        print("Validation failed:")
        for line in errors:
            print(f" - {line}")
        return 1
    GRAPH_PATH.write_text(json.dumps(graph, indent=2))
    print(f"All documents validated successfully. Graph written to {GRAPH_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
