#!/usr/bin/env python3
"""
Layer dependency linter.

Rulebook (single source of truth — edit here first):

Common frontmatter (all layers)
- required: `title`, `status`, `layer`.
- status ∈ {someday, later, soon, plan, make, test, doc, release}.
- generic `depends_on` is forbidden; use typed deps per kind below.

Layer ordering
act (0) → math (1) → calculus (2) → system/spec (3) → machine (4) → arch/computer (5).
No upward references are allowed.

Layer-specific schema
- Layer 0 (acts): required keys {`act`, `slug`, `top`, `bottom`}. `top`/`bottom`
  must name existing acts; only Relationlessness may be null.
- Layers 1–5: typed deps only. Use:
  - `derived_from`: upstream structures/operators this item lifts/refines,
  - `uses`: structures/operators consumed,
  - `produces`: structures produced (for operators),
  - `used_by` / `produced_by`: reverse links for structures (optional).
  Structure/operator/act `kind` should match the filepath (`structure`,
  `operator`, `act`).

Dependency checks
- All deps must resolve to known layers; no upward deps.
- For `derived_from`, prefer items in the immediate prior layer.
- Filepath layer must match `layer` metadata; `kind` must match filename context.

Layer mapping:
0: acts
1: math (internal-theorem, math/structure, math/operator)
2: calculus
3: system/spec
4: machine
5: arch (computer)
"""
from __future__ import annotations

import pathlib
import re
import sys
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


LAYER_ORDER = {
    "act": 0,
    "internal-theorem": 1,
    "math": 1,
    "calculus": 2,
    "system": 3,
    "spec": 3,
    "machine": 4,
    "arch": 5,
}

REQUIRED_KEYS = {"title", "status", "layer"}
LAYER_SPECIFIC_KEYS = {
    0: {"act", "slug", "top", "bottom"},
}
ALLOWED_STATUS = {"someday", "later", "soon", "plan", "make", "test", "doc", "release"}


def infer_layer_from_path(path: pathlib.Path) -> int | None:
    parts = path.parts
    if "math" in parts and "acts" in parts:
        return 0
    if "math" in parts:
        return 1
    if "calculus" in parts:
        return 2
    if "system" in parts:
        return 3
    if "app" in parts and "spec" in parts:
        return 3
    if "machine" in parts:
        return 4
    if "arch" in parts or ("app" in parts and "arch" in parts):
        return 5
    return None


def priority_for(path: pathlib.Path, layer: int | None) -> int:
    """Order issues by proximity to acts (higher numbers = closer to acts).

    Highest-priority (closest to acts) items are printed last so the bottom of
    the report shows the most destabilizing issues.
    """
    if layer is None:
        inferred = infer_layer_from_path(path)
        if inferred is None:
            return 0
        return 10 - inferred
    return 10 - layer


def layer_of_dep(dep: str) -> int | None:
    if dep.startswith("acts/"):
        return 0
    if dep.startswith("theorem/internal/") or dep.startswith("math/"):
        return 1
    if dep.startswith("calculus/"):
        return 2
    if dep.startswith("system/") or dep.startswith("spec/"):
        return 3
    if dep.startswith("machine/"):
        return 4
    if dep.startswith("arch/"):
        return 5
    if dep.startswith("reference/"):
        # treat references as external math layer for now
        return 1
    return None


def main() -> int:
    issues: dict[str, dict[str, object]] = {}
    issue_counts: dict[str, int] = {}

    # Precompute known acts (by their `act` identifier) for validating tops/bottoms.
    known_acts: set[str] = set()
    doc_ids: set[str] = set()
    for md in ROOT.rglob("docs/**/*.md"):
        rel = md.relative_to(ROOT).with_suffix("")
        doc_ids.add(str(rel))
    for act_path in ROOT.glob("docs/math/acts/*.md"):
        try:
            text = act_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        try:
            fm_text = text.split("---", 2)[1]
            meta = yaml.safe_load(fm_text) or {}
        except Exception:
            continue
        act_id = meta.get("act") or meta.get("title") or act_path.stem
        if isinstance(act_id, str):
            known_acts.add(act_id)

    def add(
        path: pathlib.Path,
        msg: str,
        layer_hint: int | None = None,
        *,
        blocking: bool = False,
        category: str = "graph",
        code: str | None = None,
    ) -> None:
        code_key = code or msg
        issue_counts[code_key] = issue_counts.get(code_key, 0) + 1
        key = str(path)
        prio = priority_for(path, layer_hint)
        entry = issues.setdefault(
            key,
            {
                "priority": prio,
                "layer": layer_hint,
                "score": 0,
                "blocking": [],
                "refactor": [],
                "graph": [],
            },
        )
        # keep the max priority (closest to acts) for the file
        entry["priority"] = max(entry["priority"], prio)
        if layer_hint is not None:
            entry["layer"] = layer_hint
        bucket = "blocking" if blocking else (category if category in ("refactor",) else "graph")
        if msg not in entry[bucket]:
            entry[bucket].append(msg)

    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        if "docs" not in path.parts:
            continue

        # Legacy buckets to nudge refactors
        if "docs" in path.parts and "reference" in path.parts:
            add(path, "reference doc: convert to earned structure/operator or mark external explicitly", category="refactor")
        if "math" in path.parts and "theorem" in path.parts:
            add(path, "legacy theorem: split into atomic math structures/operators", category="refactor")

        text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.startswith("---"):
            add(path, "missing frontmatter", blocking=True)
            continue
        try:
            fm_text = text.split("---", 2)[1]
            meta = yaml.safe_load(fm_text) or {}
        except Exception as e:
            add(path, f"frontmatter parse error: {e}", blocking=True)
            continue

        layer_name = meta.get("layer")
        file_layer: int | None = None
        if not layer_name:
            add(path, "missing layer", blocking=True)
            file_layer = infer_layer_from_path(path)
        else:
            file_layer = LAYER_ORDER.get(layer_name)
            if file_layer is None:
                add(path, f"unknown layer {layer_name}", blocking=True)
        # path-layer consistency
        expected_layer = infer_layer_from_path(path)
        if file_layer is not None and expected_layer is not None and file_layer != expected_layer:
            add(
                path,
                f"layer {layer_name} disagrees with path (expected {expected_layer})",
                file_layer,
                category="refactor",
            )
        # required keys
        for req in REQUIRED_KEYS:
            if req not in meta:
                add(path, f"missing {req}", file_layer, blocking=True)
        if file_layer in LAYER_SPECIFIC_KEYS:
            for req in LAYER_SPECIFIC_KEYS[file_layer]:
                if req not in meta:
                    add(path, f"missing {req}", file_layer, blocking=True)
        deps_raw = meta.get("depends_on")
        if deps_raw:
            add(path, "depends_on is disallowed; use derived_from/uses/produces", file_layer, blocking=True)
        deps_raw = []
        status = meta.get("status")
        if status and status not in ALLOWED_STATUS:
            add(path, f"invalid status {status}", file_layer, blocking=True)

        if file_layer is None:
            continue

        text_has_proof = bool(re.search(r"^## +Proof", text, flags=re.MULTILINE))

        # expected kind for structure/operator/act paths
        kind = meta.get("kind")
        if "structure" in path.parts:
            if kind is None:
                add(path, "missing kind for structure (expected 'structure')", file_layer, blocking=True)
            elif kind != "structure":
                add(path, f"kind should be 'structure' (found {kind})", file_layer, blocking=True)
        if "operator" in path.parts:
            if kind is None:
                add(path, "missing kind for operator (expected 'operator')", file_layer, blocking=True)
            elif kind != "operator":
                add(path, f"kind should be 'operator' (found {kind})", file_layer, blocking=True)
        if "acts" in path.parts:
            if kind is None:
                add(path, "missing kind for act (expected 'act')", file_layer, blocking=True)
            elif kind != "act":
                add(path, f"kind should be 'act' (found {kind})", file_layer, blocking=True)

        # Acts must declare top/bottom that refer to other acts, except the root
        if file_layer == 0:
            top = meta.get("top")
            bottom = meta.get("bottom")
            act_id = meta.get("act") or path.stem
            slug = meta.get("slug")
            # slug/filename consistency
            if slug and slug != path.stem:
                add(path, f"slug mismatch: slug={slug} filename={path.stem}", file_layer, category="refactor")
            if act_id and slug and act_id != slug:
                add(path, f"act name {act_id} differs from slug {slug}", file_layer, category="refactor")
            if act_id == "Relationlessness":
                # root act is allowed to have null anchors
                pass
            else:
                if top is None:
                    add(path, "missing top", file_layer, blocking=True)
                if bottom is None:
                    add(path, "missing bottom", file_layer, blocking=True)
            # Relationlessness is allowed to have null anchors
            if act_id != "Relationlessness":
                if isinstance(top, str):
                    if top not in known_acts:
                        add(path, f"top not in known acts: {top}", file_layer, blocking=True)
                else:
                    add(path, "top must reference a prior act", file_layer, blocking=True)
                if isinstance(bottom, str):
                    if bottom not in known_acts:
                        add(path, f"bottom not in known acts: {bottom}", file_layer, blocking=True)
                else:
                    add(path, "bottom must reference a prior act", file_layer, blocking=True)
            continue

        # Typed deps for non-act items
        derived_raw = meta.get("derived_from", [])
        uses_raw = meta.get("uses", [])
        produces_raw = meta.get("produces", [])
        used_by_raw = meta.get("used_by", [])
        produced_by_raw = meta.get("produced_by", [])
        for key in ("derived_raw", "uses_raw", "produces_raw", "used_by_raw", "produced_by_raw"):
            pass
        if isinstance(derived_raw, str):
            derived_raw = [derived_raw]
        if isinstance(uses_raw, str):
            uses_raw = [uses_raw]
        if isinstance(produces_raw, str):
            produces_raw = [produces_raw]
        if isinstance(used_by_raw, str):
            used_by_raw = [used_by_raw]
        if isinstance(produced_by_raw, str):
            produced_by_raw = [produced_by_raw]

        derived: list[str] = list(derived_raw)
        uses: list[str] = list(uses_raw)
        produces: list[str] = list(produces_raw)
        used_by: list[str] = list(used_by_raw)
        produced_by: list[str] = list(produced_by_raw)
        deps: list[str] = derived + uses + produces + used_by + produced_by
        if not deps:
            add(path, "missing derived_from/uses/produces", file_layer, blocking=True)
        # Derivation/composition rule:
        # - either exactly one derived_from in the prior layer, or
        # - a pure composition of same-layer items via uses/produces.
        if derived:
            if len(derived) != 1:
                add(path, f"expected exactly one derived_from (found {len(derived)})", file_layer, blocking=True)
        else:
            # no derived_from: require uses/produces and same-layer composition
            if not (uses or produces):
                add(path, "no derived_from and no uses/produces (need composition)", file_layer, blocking=True)
        if kind in ("structure", "operator") and not text_has_proof:
            add(path, "missing Proof section", file_layer, blocking=True)

        known_deps: list[tuple[str, int]] = []
        known_annotated: list[tuple[str, int, str]] = []
        for dep in deps:
            dep_layer = layer_of_dep(dep)
            if dep_layer is None:
                add(path, f"unknown dep {dep}", file_layer)
                continue
            # existence check for known docs (best effort)
            dep_path = dep if dep.endswith(".md") else f"{dep}"
            if not dep_path.endswith(".md"):
                dep_path = f"{dep_path}.md"
            dep_id = dep_path.removesuffix(".md")
            if dep_id not in doc_ids and not dep.startswith("acts/"):
                add(path, f"dep not found in docs: {dep}", file_layer, category="refactor")
            known_deps.append((dep, dep_layer))
            if dep_layer > file_layer:
                add(path, f"depends on higher layer {dep} ({dep_layer}>{file_layer})", file_layer)
            if dep in derived:
                source = "derived_from"
            elif dep in uses:
                source = "uses"
            elif dep in produces:
                source = "produces"
            elif dep in used_by:
                source = "used_by"
            else:
                source = "produced_by"
            known_annotated.append((dep, dep_layer, source))

        # calculus heuristic for multiple math lifts
        if file_layer == 2:
            math_deps = [d for d, l in known_deps if l == 1]
            if len(math_deps) > 1:
                add(path, f"calculus depends on multiple math items: {math_deps}", file_layer)

        # Layer checks for deps above acts
        if file_layer > 0 and known_annotated:
            prior_layer = file_layer - 1
            derived_bad = []
            derived_wrong_layer = []
            uses_bad = []
            produces_bad = []
            for dep, dep_layer, source in known_annotated:
                if source == "derived_from":
                    if dep_layer > file_layer:
                        derived_bad.append(dep)
                    if dep_layer != prior_layer:
                        derived_wrong_layer.append(dep)
                if source == "uses" and dep_layer > file_layer:
                    uses_bad.append(dep)
                if source == "produces" and dep_layer > file_layer:
                    produces_bad.append(dep)
            if derived_bad:
                add(path, f"derived_from higher layer {derived_bad}", file_layer)
            if derived_wrong_layer:
                add(path, f"derived_from not in immediate prior layer {derived_wrong_layer}", file_layer)
            if not derived and uses and any(l != file_layer for _, l, s in known_annotated if s == "uses"):
                add(path, "composition uses items outside current layer", file_layer)
            if uses_bad:
                add(path, f"uses higher layer {uses_bad}", file_layer)
            if produces_bad:
                add(path, f"produces higher layer {produces_bad}", file_layer)

    if issues:
        try:
            blocking_total = sum(len(v.get("blocking", [])) for v in issues.values())
            refactor_total = sum(len(v.get("refactor", [])) for v in issues.values())
            graph_total = sum(len(v.get("graph", [])) for v in issues.values())
            for payload in issues.values():
                b = len(payload.get("blocking", []))
                r = len(payload.get("refactor", []))
                g = len(payload.get("graph", []))
                payload["score"] = b * 5 + r * 3 + g * 1 + payload["priority"]

            layer_summary: dict[int, dict[str, int]] = {}
            for _, payload in issues.items():
                layer_idx = payload.get("layer") if payload.get("layer") is not None else -1
                ls = layer_summary.setdefault(layer_idx, {"blocking": 0, "refactor": 0, "graph": 0})
                ls["blocking"] += len(payload.get("blocking", []))
                ls["refactor"] += len(payload.get("refactor", []))
                ls["graph"] += len(payload.get("graph", []))

            print(f"Summary: blocking {blocking_total}, refactor {refactor_total}, graph {graph_total}")
            print("By layer (layer: blocking/refactor/graph):")
            for layer_idx in sorted(layer_summary.keys()):
                ls = layer_summary[layer_idx]
                print(f"  {layer_idx}: {ls['blocking']}/{ls['refactor']}/{ls['graph']}")

            print("Most frequent issue codes:")
            for code_key, count in sorted(issue_counts.items(), key=lambda kv: kv[1])[-10:]:
                print(f"  {code_key}: {count}")

            top_n = sorted(
                issues.items(), key=lambda kv: (kv[1]["score"], kv[1]["priority"], kv[0])
            )[-10:]
            print("Top 10 most destabilizing files:")
            for path, payload in top_n:
                print(
                    f"  {path} (score {payload['score']}, blocking {len(payload.get('blocking', []))}, "
                    f"refactor {len(payload.get('refactor', []))}, graph {len(payload.get('graph', []))})"
                )

            for path, payload in sorted(
                issues.items(), key=lambda kv: (kv[1]["priority"], kv[0])
            ):
                layer_hint = payload.get("layer")
                layer_txt = f"layer {layer_hint}" if layer_hint is not None else "layer ?"
                blocking = payload.get("blocking", [])
                refactor = payload.get("refactor", [])
                graph = payload.get("graph", [])
                score = payload.get("score", len(blocking) * 5 + len(refactor) * 3 + len(graph) * 1 + payload["priority"])
                print(
                    f"{path} ({layer_txt}, priority {payload['priority']}, score {score},"
                    f" blocking {len(blocking)}, refactor {len(refactor)}, graph {len(graph)}):"
                )
                if blocking:
                    print("  blocking (add missing info/schema):")
                    for msg in blocking:
                        print(f"    - {msg}")
                if refactor:
                    print("  refactor (rewrite/split/move):")
                    for msg in refactor:
                        print(f"    - {msg}")
                if graph:
                    print("  graph (derivation/deps):")
                    for msg in graph:
                        print(f"    - {msg}")
        except BrokenPipeError:
            pass
        return 1
    print("No layer violations found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
