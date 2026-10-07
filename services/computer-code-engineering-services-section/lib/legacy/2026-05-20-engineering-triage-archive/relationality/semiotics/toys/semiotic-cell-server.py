#!/usr/bin/env python3
"""
Semiotic Cell Server v0.4
=========================

A one-file MCP server exposing a semiotic universe backed by a JSON "cell",
shaped to reflect the Semiotic Universe construction:

- Semantic field H is a normalized term algebra with:
    * AC-idempotent 'and'
    * structural 'impl'
    * idempotent modal operator 'box'
- The modality j is represented by 'box(t)' with:
    * box(box(t)) = box(t)
    * 'stable' tags marking the modal fragment H^st
- Trace G is represented by 'trace(t)' with a simple law trace(t) ⇒ box(trace(t)).
- Syntactic operators ("op" terms) live entirely inside the universe and act
  via "apply(op, args)" terms. Interpretation is:
    apply(op[a1,...,an]) ↦ box(body[x1:=a1, ..., xn:=an]).
- Closure operators:
    S_sem  (semantic closure)
    S_syn  (syntactic closure / op emergence)
    S_fus  (fusion closure: term equality + unary/op behavioral fusion
             + mutual-implication term fusion on the stable fragment)
  are monotone and idempotent; their composite S is iterated to a fixed point.
- Emergent unary ops come from definability patterns like and(atom(A), X).

MCP Tools (FastMCP):

- inject(term_text)
- close()
- query(term_text)
- operators()
- snapshot()
- prove(term_text)
- why(term_text)
- modal(term_text)
- trace_info(term_text)
- apply_op(op_name, arg_text)
- interpret_op(op_name, arg_text)
- diff_cell()
- reset_cell(keep_ops: bool)

Dependencies:
    pip install mcp

Run:
    python semiotic_cell_server.py

Configure as MCP tool in your client with e.g.:
    "command": "python",
    "args": ["path/to/semiotic_cell_server.py"]
"""

import json
import os
import hashlib
from copy import deepcopy
from typing import Any, Dict, List, Tuple, Optional, Set

from mcp.server.fastmcp import FastMCP

# ============================================================
# Persistent JSON "cell" store
# ============================================================

CELL_PATH = os.environ.get("SEMIOTIC_CELL_PATH", "cell.json")


def empty_cell() -> Dict[str, Any]:
    return {
        "semantic": [],  # list of {"id": int, "term": {...}, "tags": [str]}
        "ops": [],       # list of {"id": int, "term": {...}, "op_index": int}
        "entails": [],   # list of {"from": int, "to": int, "reason": str}
        "counter": {"next_id": 1, "next_op": 1},
    }


def load_cell() -> Dict[str, Any]:
    if not os.path.exists(CELL_PATH):
        return empty_cell()
    with open(CELL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cell(cell: Dict[str, Any]) -> None:
    with open(CELL_PATH, "w", encoding="utf-8") as f:
        json.dump(cell, f, indent=2, ensure_ascii=False)


# ============================================================
# Term representation, normalization, equality
# ============================================================

def terms_equal(a: Any, b: Any) -> bool:
    """Structural equality for term ASTs."""
    if type(a) != type(b):
        return False
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return False
        return all(terms_equal(a[k], b[k]) for k in a.keys())
    if isinstance(a, list):
        return len(a) == len(b) and all(terms_equal(x, y) for x, y in zip(a, b))
    return a == b


def canonical_term(term: Any) -> str:
    """Canonical string representation of a term (for hashing/comparison)."""
    return json.dumps(term, sort_keys=True, ensure_ascii=False)


def flatten_and(term: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect all conjuncts in an 'and' term into a flat list."""
    if term.get("tag") != "and":
        return [term]
    flat: List[Dict[str, Any]] = []
    for t in term["args"]:
        if isinstance(t, dict) and t.get("tag") == "and":
            flat.extend(flatten_and(t))
        else:
            flat.append(t)
    return flat


def normalize_term(term: Any) -> Any:
    """
    Normalize a term to enforce algebraic properties:
      - 'and' is associative, commutative, idempotent:
            and(and(a,b),c) = and(a,b,c) = and(c,a,b), etc.
      - box(box(t)) = box(t)
      - impl terms are normalized structurally
    """
    if isinstance(term, dict):
        tag = term.get("tag")

        if tag == "and":
            children = [normalize_term(t) for t in flatten_and(term)]
            seen: Dict[str, Dict[str, Any]] = {}
            for c in children:
                seen[canonical_term(c)] = c
            children = list(seen.values())
            children.sort(key=canonical_term)
            if not children:
                return {"tag": "atom", "name": "⊤"}
            if len(children) == 1:
                return children[0]
            return {"tag": "and", "args": children}

        if tag == "box":
            inner = normalize_term(term["arg"])
            if isinstance(inner, dict) and inner.get("tag") == "box":
                return inner  # idempotence
            return {"tag": "box", "arg": inner}

        if tag in ("proto", "trace", "stable"):
            return {"tag": tag, "arg": normalize_term(term["arg"])}

        if tag == "impl":
            return {
                "tag": "impl",
                "args": [normalize_term(term["args"][0]),
                         normalize_term(term["args"][1])],
            }

        if tag == "apply":
            return {
                "tag": "apply",
                "op": normalize_term(term["op"]),
                "args": [normalize_term(a) for a in term["args"]],
            }

        if tag == "op":
            return {
                "tag": "op",
                "name": term["name"],
                "params": term["params"],
                "body": normalize_term(term["body"]),
            }

        if tag in ("atom", "var"):
            return {"tag": tag, "name": term["name"]}

        # fallback: recursively normalize
        return {k: normalize_term(v) for k, v in term.items()}

    if isinstance(term, list):
        return [normalize_term(t) for t in term]

    return term


# ============================================================
# Compact DSL parser
# ============================================================

def strip_outer_parens(s: str) -> str:
    s = s.strip()
    if not s.startswith("("):
        return s
    depth = 0
    end_index = -1
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end_index = i
                break
    if end_index == len(s) - 1:
        return s[1:-1].strip()
    return s


def find_top_level(s: str, needle: str) -> int:
    """Find first occurrence of 'needle' at parentheses depth 0, or -1."""
    depth = 0
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and s.startswith(needle, i):
            return i
        i += 1
    return -1


def split_top_level(s: str, sep: str) -> List[str]:
    """Split on 'sep' at depth 0, trimming whitespace."""
    parts: List[str] = []
    depth = 0
    start = 0
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and ch == sep:
            parts.append(s[start:i].strip())
            start = i + 1
        i += 1
    parts.append(s[start:].strip())
    return [p for p in parts if p]


def parse_atomic(s: str) -> Dict[str, Any]:
    return {"tag": "atom", "name": s.strip()}


def parse_prefix_op(s: str, op: str) -> Dict[str, Any]:
    s = s.strip()
    if s.startswith(op + "(") and s.endswith(")"):
        inner = s[len(op) + 1: -1]
        return {"tag": op, "arg": parse_term(inner)}
    if s.startswith(op + " "):
        inner = s[len(op) + 1:]
        return {"tag": op, "arg": parse_term(inner)}
    return parse_atomic(s)


def parse_apply_or_atom(s: str) -> Dict[str, Any]:
    """Parse function-like application: foo(a,b) or fall back to atom."""
    s = s.strip()
    depth = 0
    paren_index = -1
    for i, ch in enumerate(s):
        if ch == "(":
            if depth == 0:
                paren_index = i
            depth += 1
        elif ch == ")":
            depth -= 1
    if paren_index == -1 or not s.endswith(")"):
        return parse_atomic(s)
    name = s[:paren_index].strip()
    inner = s[paren_index + 1: -1].strip()
    if not name:
        return parse_atomic(s)
    if not inner:
        args_terms: List[Dict[str, Any]] = []
    else:
        arg_strs = split_top_level(inner, ",")
        args_terms = [parse_term(a) for a in arg_strs]
    return {"tag": "apply", "op": {"tag": "atom", "name": name}, "args": args_terms}


def parse_term(text: str) -> Dict[str, Any]:
    """
    Parse a term in the compact DSL into an internal AST.

    Examples:
        red & ball
        red -> ball
        box red
        trace x
        proto(red & ball)
        foo(a,b)
    """
    s = text.strip()
    if not s:
        return {"tag": "atom", "name": ""}

    prev = None
    while prev != s:
        prev = s
        s = strip_outer_parens(s)

    # implication
    idx = find_top_level(s, "->")
    if idx != -1:
        left = s[:idx].strip()
        right = s[idx + 2:].strip()
        return normalize_term({
            "tag": "impl",
            "args": [parse_term(left), parse_term(right)],
        })

    # conjunction
    depth = 0
    amp_index = -1
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and ch == "&":
            amp_index = i
            break
    if amp_index != -1:
        left = s[:amp_index].strip()
        right = s[amp_index + 1:].strip()
        return normalize_term({
            "tag": "and",
            "args": [parse_term(left), parse_term(right)],
        })

    # prefix ops: proto, box, trace
    for op in ("proto", "box", "trace"):
        if s.startswith(op + " ") or s.startswith(op + "("):
            return normalize_term(parse_prefix_op(s, op))

    # apply or atom
    return normalize_term(parse_apply_or_atom(s))


# ============================================================
# Cell helpers
# ============================================================

def new_semantic(cell: Dict[str, Any], term: Dict[str, Any],
                 tags: Optional[List[str]] = None) -> int:
    term = normalize_term(term)
    existing = get_sem_by_term(cell, term)
    if existing:
        if tags:
            for tag in tags:
                if tag not in existing.get("tags", []):
                    existing["tags"].append(tag)
        return existing["id"]

    sid = cell["counter"]["next_id"]
    cell["counter"]["next_id"] += 1
    cell["semantic"].append({"id": sid, "term": term, "tags": tags or []})
    return sid


def new_op(cell: Dict[str, Any], op_term: Dict[str, Any],
           emergent: bool = False) -> int:
    """
    Add an operator term to the cell if not already present.
    emergent=True means the op came from syntactic closure.
    """
    op_term = normalize_term(op_term)

    # check if same op already exists
    for o in cell["ops"]:
        if terms_equal(normalize_term(o["term"]), op_term):
            return o["id"]

    oid = cell["counter"]["next_id"]
    cell["counter"]["next_id"] += 1
    op_index = cell["counter"].get("next_op", 1)
    cell["counter"]["next_op"] = op_index + 1
    cell["ops"].append({"id": oid, "term": op_term, "op_index": op_index})
    cell["semantic"].append({"id": oid, "term": op_term, "tags": ["operator"]})
    return oid


def get_sem_by_term(cell: Dict[str, Any], term: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    term = normalize_term(term)
    for s in cell["semantic"]:
        if terms_equal(normalize_term(s["term"]), term):
            return s
    return None


def add_entail(cell: Dict[str, Any], frm: int, to: int, reason: str) -> None:
    """Idempotent entailment: don't add duplicates."""
    for e in cell["entails"]:
        if e["from"] == frm and e["to"] == to and e["reason"] == reason:
            return
    cell["entails"].append({"from": frm, "to": to, "reason": reason})


def lookup_op_def(cell: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    for o in cell["ops"]:
        t = o["term"]
        if t.get("tag") == "op" and t.get("name") == name:
            return t
    return None


def op_semantic_id(cell: Dict[str, Any], op_term: Dict[str, Any]) -> Optional[int]:
    op_term = normalize_term(op_term)
    for s in cell["semantic"]:
        if terms_equal(normalize_term(s["term"]), op_term):
            return s["id"]
    return None


def canonical_semantic(cell: Dict[str, Any]) -> List[Tuple[int, str, Tuple[str, ...]]]:
    out: List[Tuple[int, str, Tuple[str, ...]]] = []
    for s in cell["semantic"]:
        out.append(
            (
                s["id"],
                canonical_term(normalize_term(s["term"])),
                tuple(sorted(set(s.get("tags", [])))),
            )
        )
    out.sort()
    return out


def canonical_entails(cell: Dict[str, Any]) -> List[Tuple[int, int, str]]:
    out: List[Tuple[int, int, str]] = []
    for e in cell["entails"]:
        out.append((e["from"], e["to"], e["reason"]))
    out.sort()
    return out


def canonical_ops(cell: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for o in cell["ops"]:
        out.append(canonical_term(normalize_term(o["term"])))
    out.sort()
    return out


def cell_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return (
        canonical_semantic(a) == canonical_semantic(b)
        and canonical_entails(a) == canonical_entails(b)
        and canonical_ops(a) == canonical_ops(b)
    )


# ============================================================
# Substitution for operator bodies
# ============================================================

def substitute(term: Any, env: Dict[str, Any]) -> Any:
    """
    Capture-avoiding substitution for vars in an op body.

    env: mapping from var name -> term
    """
    if isinstance(term, dict):
        tag = term.get("tag")
        if tag == "var":
            name = term["name"]
            if name in env:
                return normalize_term(env[name])
            return term
        if tag == "atom":
            return term
        if tag == "op":
            return {
                "tag": "op",
                "name": term["name"],
                "params": term["params"],
                "body": substitute(term["body"], env),
            }
        if tag in ("proto", "box", "trace", "stable"):
            return {"tag": tag, "arg": substitute(term["arg"], env)}
        if tag == "and":
            return {
                "tag": "and",
                "args": [substitute(arg, env) for arg in term["args"]],
            }
        if tag == "impl":
            return {
                "tag": "impl",
                "args": [substitute(term["args"][0], env),
                         substitute(term["args"][1], env)],
            }
        if tag == "apply":
            return {
                "tag": "apply",
                "op": substitute(term["op"], env),
                "args": [substitute(a, env) for a in term["args"]],
            }
        return {k: substitute(v, env) for k, v in term.items()}

    if isinstance(term, list):
        return [substitute(t, env) for t in term]
    return term


# ============================================================
# Small helpers
# ============================================================

def is_stable(cell: Dict[str, Any], term: Dict[str, Any]) -> bool:
    """Check if a term appears as stable in the semantic set."""
    t_norm = normalize_term(term)
    for s in cell["semantic"]:
        if terms_equal(normalize_term(s["term"]), t_norm) and "stable" in s.get("tags", []):
            return True
    return False


# ============================================================
# Closure operators
# ============================================================

def semantic_closure(cell: Dict[str, Any]) -> Dict[str, Any]:
    """
    Semantic closure S_sem:

      - proto(t) => t, box(t)
      - and(t1, ..., tn) => each ti
      - and(a, impl(a,b)) => b
      - and(impl(c,a), impl(a,b)) => impl(c,b) (Heyting-like composition)
      - impl(a,b) & a => b
      - impl(a,b) => box(impl(a,b))
      - if a,b stable and impl(a,b) present, impl(a,b) stable
      - box(t) => t stable
      - trace(t) => box(trace(t))
      - apply(op, args) => box(body[args/params])  (modal discipline)
    """
    new_cell = deepcopy(cell)

    def ensure_term(t: Dict[str, Any], reason: str, frm_id: int,
                    tags: Optional[List[str]] = None) -> int:
        t = normalize_term(t)
        existing = get_sem_by_term(new_cell, t)
        if existing:
            if tags:
                for tag in tags:
                    if tag not in existing.get("tags", []):
                        existing["tags"].append(tag)
            sid_inner = existing["id"]
        else:
            sid_inner = new_semantic(new_cell, t, tags=tags)
        add_entail(new_cell, frm_id, sid_inner, f"S_sem:{reason}")
        return sid_inner

    original_sem = cell["semantic"]

    for s in original_sem:
        sid = s["id"]
        t = normalize_term(s["term"])
        tag = t.get("tag")

        # proto(t)
        if tag == "proto":
            arg = t["arg"]
            ensure_term(arg, "proto-unpack", sid)
            ensure_term({"tag": "box", "arg": arg}, "proto->box", sid)

        # and(t1, ..., tn)
        if tag == "and":
            args = t["args"]

            # elimination: each conjunct
            for child in args:
                ensure_term(child, "and-elim", sid)

            # and(a, impl(a,b)) => b
            for child in args:
                if isinstance(child, dict) and child.get("tag") == "impl":
                    impl_a, impl_b = child["args"]
                    for other in args:
                        if terms_equal(other, impl_a):
                            ensure_term(impl_b, "and-impl-elim", sid)
                            break

            # Heyting-like composition: and(impl(c,a), impl(a,b)) => impl(c,b)
            impls = [c for c in args if isinstance(c, dict) and c.get("tag") == "impl"]
            for impl1 in impls:
                c1, a1 = impl1["args"]
                for impl2 in impls:
                    a2, b2 = impl2["args"]
                    if terms_equal(a1, a2):
                        composed = {"tag": "impl", "args": [c1, b2]}
                        ensure_term(composed, "impl-compose", sid)

            # if all conjuncts stable, mark the conjunction as stable
            if all(is_stable(new_cell, child) for child in args):
                ensure_term(t, "and-stable", sid, tags=["stable"])

        # impl(a,b)
        if tag == "impl":
            a, b = t["args"]

            # impl(a,b) => box(impl(a,b))
            ensure_term({"tag": "box", "arg": t}, "impl-modalize", sid)

            # impl(a,b) & a => b
            for s2 in original_sem:
                if terms_equal(normalize_term(s2["term"]), normalize_term(a)):
                    ensure_term(b, "modus-ponens", sid)

            # if a,b stable, mark impl(a,b) as stable
            if is_stable(new_cell, a) and is_stable(new_cell, b):
                ensure_term(t, "impl-stable", sid, tags=["stable"])

        # box(t) => t stable
        if tag == "box":
            arg = normalize_term(t["arg"])
            ensure_term(arg, "box-stabilize", sid, tags=["stable"])

        # trace(t) => box(trace(t))
        if tag == "trace":
            ensure_term({"tag": "box", "arg": t}, "trace-box", sid)

        # apply(op, args) => box(body[args/params])
        if tag == "apply":
            op_term = t["op"]
            args = t["args"]
            if op_term.get("tag") == "atom":
                op_def = lookup_op_def(cell, op_term["name"])
                if op_def:
                    params = op_def["params"]
                    body = op_def["body"]
                    if len(params) == len(args):
                        env = {p: a for p, a in zip(params, args)}
                        instantiated = substitute(body, env)
                        instantiated = normalize_term(instantiated)
                        boxed = {"tag": "box", "arg": instantiated}
                        ensure_term(boxed, "op-apply-boxed", sid)

    return new_cell


def syntactic_closure(cell: Dict[str, Any]) -> Dict[str, Any]:
    """
    Syntactic closure S_syn:

      - Reflect stability: for any semantic term with tag 'stable',
        add stable(t) syntactic markers.
      - Emergent unary operators for patterns and(atom(A), X) or and(X, atom(A))
        with at least 2 distinct holes. Emergent ops only use and/atom/var.
    """
    new_cell = deepcopy(cell)

    # Reflect stability
    for s in cell["semantic"]:
        if "stable" in s.get("tags", []):
            stable_term = {"tag": "stable", "arg": normalize_term(s["term"])}
            if not get_sem_by_term(new_cell, stable_term):
                nid = new_semantic(new_cell, stable_term, tags=["syntactic"])
                add_entail(new_cell, s["id"], nid, "S_syn:reflect-stability")

    # Emergent ops
    patterns: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}

    for s in cell["semantic"]:
        t = normalize_term(s["term"])
        if t.get("tag") == "and":
            args = t["args"]
            # for each atom A in the conjunction, treat any other conjunct as a hole
            for idx, arg in enumerate(args):
                if isinstance(arg, dict) and arg.get("tag") == "atom":
                    atom_name = arg["name"]
                    for jdx, other in enumerate(args):
                        if jdx == idx:
                            continue
                        key_left = ("left", atom_name)
                        holes_left = patterns.setdefault(key_left, {})
                        holes_left[canonical_term(other)] = other

                        key_right = ("right", atom_name)
                        holes_right = patterns.setdefault(key_right, {})
                        holes_right[canonical_term(other)] = other

    existing_op_terms = [o["term"] for o in cell["ops"]]

    for (side, atom_name), holes in patterns.items():
        if len(holes) < 2:
            continue

        var_name = "x"
        if side == "left":
            body = {
                "tag": "and",
                "args": [
                    {"tag": "atom", "name": atom_name},
                    {"tag": "var", "name": var_name},
                ],
            }
            op_hint = f"op_and_left_{atom_name}"
        else:
            body = {
                "tag": "and",
                "args": [
                    {"tag": "var", "name": var_name},
                    {"tag": "atom", "name": atom_name},
                ],
            }
            op_hint = f"op_and_right_{atom_name}"

        body = normalize_term(body)

        # check if operator body already exists
        already = False
        for oterm in existing_op_terms:
            if oterm.get("tag") == "op":
                if terms_equal(normalize_term(oterm.get("body")), body) and len(oterm.get("params", [])) == 1:
                    already = True
                    break
        if already:
            continue

        op_index = new_cell["counter"].get("next_op", 1)
        new_cell["counter"]["next_op"] = op_index + 1
        op_name = f"{op_hint}_{op_index}"

        op_term = {
            "tag": "op",
            "name": op_name,
            "params": [var_name],
            "body": body,
        }
        new_op(new_cell, op_term, emergent=True)

    return new_cell


def behavioral_eq_unary(cell: Dict[str, Any],
                        f: Dict[str, Any],
                        g: Dict[str, Any],
                        stable_terms: List[Dict[str, Any]]) -> bool:
    """
    Check equality of two unary operators on the current modal fragment
    (stable_terms). Compare instantiated bodies modulo normalization.
    """
    params_f = f.get("params", [])
    params_g = g.get("params", [])
    if len(params_f) != 1 or len(params_g) != 1:
        return False
    px_f = params_f[0]
    px_g = params_g[0]
    body_f = f.get("body")
    body_g = g.get("body")

    for t in stable_terms:
        inst_f = normalize_term(substitute(body_f, {px_f: t}))
        inst_g = normalize_term(substitute(body_g, {px_g: t}))
        if not terms_equal(inst_f, inst_g):
            return False
    return True


def fusion_closure(cell: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fusion closure S_fus:

      - Term-level: if two semantic objects have identical normalized terms,
        relate them via definitional-eq.
      - Term-level (fragmentwise): if two stable terms mutually imply each other
        (impl(t1,t2) and impl(t2,t1) present), fuse them via definitional-eq.
      - Unary op-level: if two unary ops behave identically on all stable terms,
        relate them via op-definitional-eq.
    """
    new_cell = deepcopy(cell)
    sems = new_cell["semantic"]
    n = len(sems)

    # term-level: syntactic equality
    for i in range(n):
        for j in range(i + 1, n):
            if terms_equal(normalize_term(sems[i]["term"]),
                           normalize_term(sems[j]["term"])):
                add_entail(new_cell, sems[i]["id"], sems[j]["id"], "S_fus:term-eq")
                add_entail(new_cell, sems[j]["id"], sems[i]["id"], "S_fus:term-eq")

    # collect stable terms (unique normalized)
    stable_terms: List[Dict[str, Any]] = []
    stable_seen: Set[str] = set()
    for s in new_cell["semantic"]:
        if "stable" in s.get("tags", []):
            t_norm = normalize_term(s["term"])
            key = canonical_term(t_norm)
            if key not in stable_seen:
                stable_seen.add(key)
                stable_terms.append(t_norm)

    # fragmentwise mutual implication fusion for stable terms
    for i in range(len(stable_terms)):
        for j in range(i + 1, len(stable_terms)):
            t1 = stable_terms[i]
            t2 = stable_terms[j]
            impl_12 = {"tag": "impl", "args": [t1, t2]}
            impl_21 = {"tag": "impl", "args": [t2, t1]}
            sem_impl_12 = get_sem_by_term(new_cell, impl_12)
            sem_impl_21 = get_sem_by_term(new_cell, impl_21)
            if sem_impl_12 and sem_impl_21:
                # fuse all occurrences of t1 and t2
                for s_a in new_cell["semantic"]:
                    if terms_equal(normalize_term(s_a["term"]), t1):
                        for s_b in new_cell["semantic"]:
                            if terms_equal(normalize_term(s_b["term"]), t2):
                                add_entail(new_cell, s_a["id"], s_b["id"], "S_fus:term-mutual-impl")
                                add_entail(new_cell, s_b["id"], s_a["id"], "S_fus:term-mutual-impl")

    # unary op behavioral fusion
    unary_ops = [o["term"] for o in new_cell["ops"]
                 if o["term"].get("tag") == "op"
                 and len(o["term"].get("params", [])) == 1]
    m = len(unary_ops)

    for i in range(m):
        for j in range(i + 1, m):
            f = unary_ops[i]
            g = unary_ops[j]
            if behavioral_eq_unary(new_cell, f, g, stable_terms):
                fid = op_semantic_id(new_cell, f)
                gid = op_semantic_id(new_cell, g)
                if fid is not None and gid is not None:
                    add_entail(new_cell, fid, gid, "S_fus:op-eq")
                    add_entail(new_cell, gid, fid, "S_fus:op-eq")

    return new_cell


def apply_closure(cell: Dict[str, Any]) -> Dict[str, Any]:
    """Apply global closure S = S_fus ∘ S_syn ∘ S_sem."""
    cell = semantic_closure(cell)
    cell = syntactic_closure(cell)
    cell = fusion_closure(cell)
    return cell


def run_to_fixpoint(cell: Dict[str, Any], max_iter: int = 32) -> Dict[str, Any]:
    """Iteratively apply closure until fixed point or max_iter hits."""
    for _ in range(max_iter):
        new_cell = apply_closure(cell)
        if cell_equal(cell, new_cell):
            return new_cell
        cell = new_cell
    return cell


# ============================================================
# Proof / explanation support
# ============================================================

def semantic_ids_for_term(cell: Dict[str, Any], term: Dict[str, Any]) -> List[int]:
    term = normalize_term(term)
    ids: List[int] = []
    for s in cell["semantic"]:
        if terms_equal(normalize_term(s["term"]), term):
            ids.append(s["id"])
    return ids


def backward_why(cell: Dict[str, Any], target_ids: List[int],
                 max_depth: int = 6) -> Dict[int, Dict[str, Any]]:
    """
    Build a backward explanation graph for a set of target semantic ids.
    Returns a map id -> {"term": ..., "tags": [...], "incoming": [...]}.
    """
    graph: Dict[int, Dict[str, Any]] = {}
    queue: List[Tuple[int, int]] = [(tid, 0) for tid in target_ids]
    visited: Set[int] = set()

    incoming_map: Dict[int, List[Dict[str, Any]]] = {}
    for e in cell["entails"]:
        incoming_map.setdefault(e["to"], []).append(e)

    sem_map: Dict[int, Dict[str, Any]] = {s["id"]: s for s in cell["semantic"]}

    while queue:
        nid, depth = queue.pop(0)
        if nid in visited or depth > max_depth:
            continue
        visited.add(nid)
        s = sem_map.get(nid)
        if not s:
            continue
        graph[nid] = {
            "id": nid,
            "term": s["term"],
            "tags": s.get("tags", []),
            "incoming": incoming_map.get(nid, []),
        }
        for e in incoming_map.get(nid, []):
            frm = e["from"]
            if frm not in visited:
                queue.append((frm, depth + 1))

    return graph


def compute_universe_hash(cell: Dict[str, Any]) -> str:
    """Compute a short hash summarizing the semantic+ops state."""
    payload = {
        "semantic": canonical_semantic(cell),
        "ops": canonical_ops(cell),
    }
    data = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def diff_cells(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a simple diff between two cells."""
    old_sem = {canonical_term(normalize_term(s["term"])) for s in old["semantic"]}
    new_sem = {canonical_term(normalize_term(s["term"])) for s in new["semantic"]}
    old_ops = set(canonical_ops(old))
    new_ops = set(canonical_ops(new))
    old_ent = set(canonical_entails(old))
    new_ent = set(canonical_entails(new))

    return {
        "semantic_added": sorted(list(new_sem - old_sem)),
        "semantic_removed": sorted(list(old_sem - new_sem)),
        "ops_added": sorted(list(new_ops - old_ops)),
        "ops_removed": sorted(list(old_ops - new_ops)),
        "entails_added": sorted(list(new_ent - old_ent)),
        "entails_removed": sorted(list(old_ent - new_ent)),
    }


# ============================================================
# MCP server
# ============================================================

mcp = FastMCP("SemioticCell", json_response=True)


@mcp.tool()
def inject(term_text: str) -> Dict[str, Any]:
    """
    Inject a proto-recognition term into the semiotic cell and run closure.

    Examples:
        inject("proto red")
        inject("proto(red & ball)")
        inject("proto(The Wreck of the Edmund Fitzgerald -> maritime_tragedy)")
    """
    cell = load_cell()

    parsed = parse_term(term_text)
    if parsed.get("tag") == "proto":
        proto_term = parsed
    else:
        proto_term = {"tag": "proto", "arg": parsed}

    sid = new_semantic(cell, proto_term, tags=["input"])

    cell = run_to_fixpoint(cell)
    save_cell(cell)

    return {
        "status": "ok",
        "inserted_id": sid,
        "semantic_count": len(cell["semantic"]),
        "ops_count": len(cell["ops"]),
        "entails_count": len(cell["entails"]),
        "universe_hash": compute_universe_hash(cell),
    }


@mcp.tool()
def close() -> Dict[str, Any]:
    """
    Manually force closure S to a fixed point.

    Useful if you edit cell.json externally or want to reclamp the universe.
    """
    cell = load_cell()
    before_sem = len(cell["semantic"])
    before_entails = len(cell["entails"])
    before_ops = len(cell["ops"])

    cell = run_to_fixpoint(cell)
    save_cell(cell)

    return {
        "status": "ok",
        "semantic_before": before_sem,
        "semantic_after": len(cell["semantic"]),
        "entails_before": before_entails,
        "entails_after": len(cell["entails"]),
        "ops_before": before_ops,
        "ops_after": len(cell["ops"]),
        "universe_hash": compute_universe_hash(cell),
    }


@mcp.tool()
def query(term_text: str) -> Dict[str, Any]:
    """
    Query the universe for a term in DSL form.

    Examples:
        query("red & ball")
        query("box red")
        query("The Wreck of the Edmund Fitzgerald")
    """
    cell = load_cell()
    t = parse_term(term_text)
    t_norm = normalize_term(t)
    matches = [s for s in cell["semantic"]
               if terms_equal(normalize_term(s["term"]), t_norm)]
    return {
        "query_term": t_norm,
        "matches": matches,
    }


@mcp.tool()
def operators() -> Dict[str, Any]:
    """
    List all operator terms in the universe, including emergent ones.
    """
    cell = load_cell()
    return {"ops": cell["ops"]}


@mcp.tool()
def snapshot() -> Dict[str, Any]:
    """
    Return the entire cell JSON: semantic, ops, entails, counters,
    along with a universe_hash summarizing the logical content.
    """
    cell = load_cell()
    out = deepcopy(cell)
    out["universe_hash"] = compute_universe_hash(cell)
    return out


@mcp.tool()
def prove(term_text: str) -> Dict[str, Any]:
    """
    Check if a term is derivable (present in the semantic set), modulo normalization.

    A term is considered provable if:
      - it exists as a semantic term, or
      - its boxed version exists as a semantic term.
    """
    cell = load_cell()
    t = normalize_term(parse_term(term_text))
    ids_direct = semantic_ids_for_term(cell, t)
    boxed_t = {"tag": "box", "arg": t}
    ids_boxed = semantic_ids_for_term(cell, boxed_t)

    return {
        "term": t,
        "provable": bool(ids_direct or ids_boxed),
        "direct_ids": ids_direct,
        "boxed_ids": ids_boxed,
    }


@mcp.tool()
def why(term_text: str) -> Dict[str, Any]:
    """
    Provide a justification graph for a term, if derivable.

    Returns a small backward entailment graph from the term's semantic id(s).
    """
    cell = load_cell()
    t = normalize_term(parse_term(term_text))
    ids = semantic_ids_for_term(cell, t)
    if not ids:
        boxed_t = {"tag": "box", "arg": t}
        ids = semantic_ids_for_term(cell, boxed_t)

    if not ids:
        return {
            "term": t,
            "found": False,
            "graph": {},
        }

    graph = backward_why(cell, ids)
    return {
        "term": t,
        "found": True,
        "graph": graph,
    }


@mcp.tool(name="modal")
def modal_tool(term_text: str) -> Dict[str, Any]:
    """
    Query the modal status of a term.

    Reports whether:
      - the term itself is stable,
      - its boxed form exists.
    """
    cell = load_cell()
    t = normalize_term(parse_term(term_text))

    is_stable_flag = is_stable(cell, t)

    boxed_t = {"tag": "box", "arg": t}
    boxed_ids = semantic_ids_for_term(cell, boxed_t)

    return {
        "term": t,
        "is_stable": is_stable_flag,
        "boxed_ids": boxed_ids,
    }


@mcp.tool()
def trace_info(term_text: str) -> Dict[str, Any]:
    """
    Show trace-related semantic facts for a term.

    Looks for:
      - trace(t)
      - box(trace(t))
    """
    cell = load_cell()
    t = normalize_term(parse_term(term_text))

    trace_t = {"tag": "trace", "arg": t}
    box_trace_t = {"tag": "box", "arg": trace_t}

    trace_ids = semantic_ids_for_term(cell, trace_t)
    box_trace_ids = semantic_ids_for_term(cell, box_trace_t)

    return {
        "term": t,
        "trace_ids": trace_ids,
        "boxed_trace_ids": box_trace_ids,
    }


@mcp.tool()
def apply_op(op_name: str, arg_text: str) -> Dict[str, Any]:
    """
    Intentionally apply a unary operator to a term.

    Example:
        apply_op("op_and_left_red_1", "ball")

    This creates a semantic term apply(atom(op_name), [arg]),
    runs closure, and returns the resulting boxed instantiation(s) if any.
    """
    cell = load_cell()
    arg_term = normalize_term(parse_term(arg_text))

    apply_term = {
        "tag": "apply",
        "op": {"tag": "atom", "name": op_name},
        "args": [arg_term],
    }
    sid = new_semantic(cell, apply_term, tags=["apply-request"])

    cell = run_to_fixpoint(cell)
    save_cell(cell)

    boxed_results: List[Dict[str, Any]] = []
    for e in cell["entails"]:
        if e["from"] == sid and e["reason"] == "S_sem:op-apply-boxed":
            target_id = e["to"]
            for s in cell["semantic"]:
                if s["id"] == target_id:
                    boxed_results.append(s)
                    break

    return {
        "status": "ok",
        "apply_id": sid,
        "boxed_results": boxed_results,
        "universe_hash": compute_universe_hash(cell),
    }


@mcp.tool()
def interpret_op(op_name: str, arg_text: str) -> Dict[str, Any]:
    """
    Pure interpretation of a unary operator on a given argument, without
    mutating the cell.

    Example:
        interpret_op("op_and_left_red_1", "ball")
    """
    cell = load_cell()
    arg_term = normalize_term(parse_term(arg_text))
    op_def = lookup_op_def(cell, op_name)
    if not op_def:
        return {
            "status": "error",
            "error": f"Operator {op_name!r} not found",
        }
    params = op_def.get("params", [])
    body = op_def.get("body")
    if len(params) != 1:
        return {
            "status": "error",
            "error": f"interpret_op currently supports unary ops only; {op_name!r} has {len(params)} params",
        }
    env = {params[0]: arg_term}
    instantiated = normalize_term(substitute(body, env))
    boxed = {"tag": "box", "arg": instantiated}
    return {
        "status": "ok",
        "op_name": op_name,
        "arg_term": arg_term,
        "instantiated": instantiated,
        "boxed": boxed,
    }


@mcp.tool()
def diff_cell() -> Dict[str, Any]:
    """
    Compute a one-step diff: apply one global closure step (without saving)
    and report what semantic/op/entail elements would be added/removed.
    """
    cell = load_cell()
    new_cell = apply_closure(cell)
    d = diff_cells(cell, new_cell)
    return {
        "status": "ok",
        "diff": d,
        "universe_hash_before": compute_universe_hash(cell),
        "universe_hash_after": compute_universe_hash(new_cell),
    }


@mcp.tool()
def reset_cell(keep_ops: bool = False) -> Dict[str, Any]:
    """
    Reset the cell to an empty (or operator-only) state.

    keep_ops=False:
        fully reset to an empty universe.
    keep_ops=True:
        keep operators and their semantic entries, drop all non-operator
        semantic objects and entailments.
    """
    cell = load_cell()

    if not keep_ops:
        cell = empty_cell()
    else:
        # keep ops and their semantic mirror; drop all non-operator semantics and entailments
        new_semantic: List[Dict[str, Any]] = []
        op_ids: Set[int] = set()
        for o in cell["ops"]:
            op_ids.add(o["id"])
        for s in cell["semantic"]:
            if s["id"] in op_ids or "operator" in s.get("tags", []):
                new_semantic.append(s)
        cell["semantic"] = new_semantic
        cell["entails"] = []
        # reset counters: next_id is max existing id + 1, next_op preserved
        max_id = max((s["id"] for s in cell["semantic"]), default=0)
        cell["counter"]["next_id"] = max_id + 1
        cell["counter"]["next_op"] = cell["counter"].get("next_op", 1)

    save_cell(cell)

    return {
        "status": "ok",
        "keep_ops": keep_ops,
        "semantic_count": len(cell["semantic"]),
        "ops_count": len(cell["ops"]),
        "entails_count": len(cell["entails"]),
        "universe_hash": compute_universe_hash(cell),
    }


if __name__ == "__main__":
    mcp.run_stdio()
