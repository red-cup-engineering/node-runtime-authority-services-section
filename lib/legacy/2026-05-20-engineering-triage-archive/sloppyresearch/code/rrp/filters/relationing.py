#!/usr/bin/env python3
"""
Relationing Markdown filter for Pandoc — Refactored (Best Practices).

Features (Phases 0–5):
  • Stable Pandoc integration (panflute run_filter entrypoint)
  • Provenance metadata on all nodes (source + timestamp)
  • Scopes as contextual ontologies (#open-x{...} … #close-x) with subgraphs
  • Cross-scope relations (e.g., src=Hypo:Being → @cross_scope)
  • Corpus loading from Markdown / JSON-LD / TTL / CSV / DOT
  • Export to JSON-LD / TTL / CSV / DOT (global and per-scope)
  • Registry-driven arity checks (polymorphic patterns) + kind checks
  • Lint/reporting with soft/strict modes and optional policy controls

Metadata keys:
  - registry: [paths...]           # corpus inputs (md/jsonld/ttl/csv/dot)
  - merge: { mode: override|union|intersect }  # reserved (loader precedence)
  - lint: { rule: warn|error|ignore, ... }
  - cross_scope: allow|warn|deny   # policy mapped to ignore|warn|error
  - lint_mode: soft|strict         # exit code behavior
  - report: path.(json|yaml|txt)   # structured lint report file
  - emit: jsonld|ttl|dot|csv       # emit single format to stdout & exit
  - emit_mode: contextual|merged|flattened
  - emit_scopes: true|false
  - emit_scopes_dir: path

This refactor improves:
  • readability (type hints, dataclasses, small helpers)
  • reliability (explicit policies, structured report)
  • testability (pure helpers separated from panflute callbacks)
  • logging & error handling (no silent failures)
"""
from __future__ import annotations

import copy
import dataclasses as dc
import enum
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Iterable, Any

import panflute as pf
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

# --------------------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------------------
LOG = logging.getLogger("relationing.filter")
if not LOG.handlers:
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    LOG.addHandler(h)
LOG.setLevel(logging.INFO)

# --------------------------------------------------------------------------------------
# Regex Patterns
# --------------------------------------------------------------------------------------
RE_OPEN       = re.compile(r"#open-([A-Za-z][\w-]*)\{([^}]*)\}")
RE_CLOSE      = re.compile(r"#close-([A-Za-z][\w-]*)")
RE_MORPH_REF  = re.compile(r"#([A-Za-z][\w-]*)\{([^}]*)\}")
RE_CELL_REF   = re.compile(r"(?<!#)#([A-Za-z][\w-]*)(?![{#])")
RE_MORPH_DEF  = re.compile(r"##([A-Za-z][\w-]*)\{([^}]*)\}")
RE_CELL_DEF   = re.compile(r"##([A-Za-z][\w-]*)")

FIND_OPEN     = RE_OPEN
FIND_CLOSE    = RE_CLOSE
FIND_MREF     = RE_MORPH_REF
FIND_CREF     = RE_CELL_REF
FIND_MDEF     = RE_MORPH_DEF
FIND_CDEF     = RE_CELL_DEF

# --------------------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------------------
def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, *parts: str) -> str:
    import hashlib
    s = prefix + "::" + "::".join(parts)
    return hashlib.sha1(s.encode()).hexdigest()[:10]


def parse_args(argstr: Optional[str]) -> Dict[str, str]:
    """Parse k=v pairs or positional args from a comma-separated string.
    Quotes are preserved inside values; surrounding quotes are stripped.
    """
    if argstr is None:
        return {}
    args: List[str] = []
    buf = ''
    in_quotes = False
    for ch in argstr:
        if ch == '"':
            in_quotes = not in_quotes
            buf += ch
        elif ch == ',' and not in_quotes:
            if buf.strip():
                args.append(buf.strip())
            buf = ''
        else:
            buf += ch
    if buf.strip():
        args.append(buf.strip())

    parsed: Dict[str, str] = {}
    for i, chunk in enumerate(args):
        if '=' in chunk:
            k, v = chunk.split('=', 1)
            parsed[k.strip()] = v.strip().strip('"')
        else:
            parsed[str(i)] = chunk.strip().strip('"')
    return parsed


def serialize_args(d: Dict[str, Any]) -> str:
    return ";".join(f"{k}={v}" for k, v in d.items())


def span(classes: Iterable[str], attrs: Dict[str, str], text: Optional[str] = None) -> pf.Span:
    return pf.Span(pf.Str(text) if text else [], classes=list(classes), attributes=attrs)


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------
class Severity(enum.Enum):
    IGNORE = "ignore"
    WARN = "warn"
    ERROR = "error"


@dc.dataclass
class ValidationReport:
    warnings: List[str] = dc.field(default_factory=list)
    errors: List[str] = dc.field(default_factory=list)

    def add(self, sev: Severity, msg: str) -> None:
        if sev is Severity.WARN:
            self.warnings.append(msg)
        elif sev is Severity.ERROR:
            self.errors.append(msg)

    @property
    def status(self) -> str:
        if self.errors:
            return "error"
        if self.warnings:
            return "warn"
        return "ok"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "warnings": self.warnings,
            "errors": self.errors,
            "summary": {
                "warnings": len(self.warnings),
                "errors": len(self.errors),
                "status": self.status,
            },
        }


def write_report(report: ValidationReport, path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    ext = p.suffix.lower()
    data = report.to_dict()
    if ext in (".json", ".jsonld"):
        p.write_text(json.dumps(data, indent=2))
        return
    if ext in (".yml", ".yaml") and yaml is not None:
        p.write_text(yaml.safe_dump(data))
        return
    # plain text
    lines = [
        f"Status: {data['summary']['status']}",
        f"Warnings: {data['summary']['warnings']}",
        f"Errors: {data['summary']['errors']}",
    ]
    if data["warnings"]:
        lines.append("\nWarnings:")
        lines.extend(f" - {w}" for w in data["warnings"])
    if data["errors"]:
        lines.append("\nErrors:")
        lines.extend(f" - {e}" for e in data["errors"])
    p.write_text("\n".join(lines))


# --------------------------------------------------------------------------------------
# Graph Core
# --------------------------------------------------------------------------------------
@dc.dataclass
class RelGraph:
    registry: Dict[str, Any] = dc.field(default_factory=dict)
    lint_cfg: Dict[str, Any] = dc.field(default_factory=dict)
    default_source: str = "stdin"

    cells: Dict[str, Dict[str, Any]] = dc.field(default_factory=dict)
    morphs: List[Dict[str, Any]] = dc.field(default_factory=list)
    scopes: List[Dict[str, Any]] = dc.field(default_factory=list)
    scope_graphs: Dict[str, "RelGraph"] = dc.field(default_factory=dict)

    refs: Dict[str, Set[str]] = dc.field(default_factory=lambda: {"cells": set(), "morph_heads": set()})
    defs: Dict[str, Set[str]] = dc.field(default_factory=lambda: {"cells": set(), "morph_heads": set()})

    report: ValidationReport = dc.field(default_factory=ValidationReport)
    corpus: Optional["RelGraph"] = None

    # ---- lint helpers
    def _mode(self, rule: str, default: Severity = Severity.IGNORE) -> Severity:
        raw = (self.lint_cfg.get(rule) or self.registry.get("lint", {}).get(rule) or default.value)
        try:
            return Severity(str(raw))
        except Exception:
            return default

    def warn_or_error(self, rule: str, msg: str) -> None:
        sev = self._mode(rule)
        if sev is Severity.WARN:
            self.report.add(Severity.WARN, msg)
        elif sev is Severity.ERROR:
            self.report.add(Severity.ERROR, msg)

    # ---- provenance
    def _prov(self, node: Dict[str, Any], source: Optional[str] = None) -> Dict[str, Any]:
        node["@source"] = source or self.default_source
        node["@timestamp"] = utcnow_iso()
        return node

    # ---- scopes
    def ensure_scope_graph(self, scope_id: str, head: Optional[str] = None, args: Optional[Dict[str, Any]] = None) -> "RelGraph":
        if scope_id not in self.scope_graphs:
            sub = RelGraph(registry=self.registry, lint_cfg=self.lint_cfg, default_source=f"scope:{scope_id}")
            sub.scopes.append(self._prov({"@id": scope_id, "@type": "Scope", "head": head or "scope", **(args or {})}, source=f"scope:{scope_id}"))
            self.scope_graphs[scope_id] = sub
        return self.scope_graphs[scope_id]

    def mirror_into_scope(self, node: Dict[str, Any], scope_id: str) -> None:
        sg = self.ensure_scope_graph(scope_id)
        t = node.get("@type")
        if t == "RelCell":
            sg.cells[node["@id"]] = copy.deepcopy(node)
        elif t == "Morphism":
            sg.morphs.append(copy.deepcopy(node))

    def promote_scope(self, scope_id: str) -> None:
        sg = self.scope_graphs.get(scope_id)
        if not sg:
            return
        for cid, cnode in sg.cells.items():
            promoted = copy.deepcopy(cnode)
            promoted.pop("@scope", None)
            promoted.pop("@contextual", None)
            promoted["@promoted_from"] = scope_id
            self.cells[cid] = promoted
        for m in sg.morphs:
            promoted = copy.deepcopy(m)
            promoted.pop("@scope", None)
            promoted.pop("@contextual", None)
            promoted["@promoted_from"] = scope_id
            self.morphs.append(promoted)

    # ---- adders
    def add_cell_ref(self, name: str) -> None:
        self.refs["cells"].add(name)

    def add_cell_def(self, name: str, source: Optional[str] = None) -> None:
        self.defs["cells"].add(name)
        if name not in self.cells:
            self.cells[name] = self._prov({"@id": name, "@type": "RelCell"}, source)

    def add_cell(self, name: str, source: Optional[str] = None) -> None:
        if name not in self.cells:
            self.cells[name] = self._prov({"@id": name, "@type": "RelCell"}, source)

    @staticmethod
    def _split_scope_qualifier(val: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        if isinstance(val, str) and ":" in val:
            a, b = val.split(":", 1)
            return a, b
        return None, val

    def add_morph(self, head: str, args: Dict[str, Any], source: Optional[str], declared_via: str) -> None:
        src_scope, src_val = self._split_scope_qualifier(args.get("src"))
        dst_scope, dst_val = self._split_scope_qualifier(args.get("dst"))
        if src_scope is not None:
            args["src"] = src_val
        if dst_scope is not None:
            args["dst"] = dst_val
        mid = stable_id(head, json.dumps(args, sort_keys=True))
        node = self._prov({"@id": mid, "@type": "Morphism", "head": head, **args, "declared_via": declared_via}, source)
        if src_scope is not None:
            node["@src_scope"] = src_scope
            node["@cross_scope"] = True
        if dst_scope is not None:
            node["@dst_scope"] = dst_scope
            node["@cross_scope"] = True
        self.morphs.append(node)

    def add_morph_ref(self, head: str, args: Dict[str, Any], source: Optional[str] = None) -> None:
        self.refs["morph_heads"].add(head)
        self.add_morph(head, args, source, declared_via="#")

    def add_morph_def(self, head: str, args: Dict[str, Any], source: Optional[str] = None) -> None:
        self.defs["morph_heads"].add(head)
        self.add_morph(head, args, source, declared_via="##")

    def add_scope(self, head: str, args: Dict[str, Any], source: Optional[str] = None) -> str:
        sid = args.get("scope_id") or stable_id(head, json.dumps(args, sort_keys=True))
        scope_node = self._prov({"@id": sid, "@type": "Scope", "head": head, **{k: v for k, v in args.items() if k != 'scope_id'}}, source)
        self.scopes.append(scope_node)
        self.ensure_scope_graph(sid, head=head, args=args)
        return sid

    # ---- serialization
    def to_jsonld(self) -> Dict[str, Any]:
        return {"@graph": list(self.cells.values()) + self.morphs + self.scopes}

    def to_ttl(self) -> str:
        lines: List[str] = []
        for c in self.cells.values():
            lines.append(f":{c['@id']} a :RelCell .")
        for m in self.morphs:
            src = m.get('src', '_'); dst = m.get('dst', '_')
            lines.append(f":{m['@id']} a :Morphism ; :head '{m['head']}' ; :src :{src} ; :dst :{dst} .")
            if m.get('@cross_scope'):
                sid_src = m.get('@src_scope_id') or m.get('@src_scope')
                sid_dst = m.get('@dst_scope_id') or m.get('@dst_scope')
                if sid_src and sid_dst:
                    lines.append(f":{sid_src} :crossScopeLink :{sid_dst} .")
        for s in self.scopes:
            lines.append(f":{s['@id']} a :Scope ; :head '{s['head']}' .")
        return "\n".join(lines)

    def to_dot(self) -> str:
        lines = ["digraph R {"]
        for m in self.morphs:
            src = m.get('src', '?'); dst = m.get('dst', '?')
            dashed = ', style="dashed"' if m.get('@cross_scope') else ''
            lines.append(f'  "{src}" -> "{dst}" [label="{m["head"]}"{dashed}];')
        lines.append("}")
        return "\n".join(lines)

    def to_csv(self) -> str:
        rows = ["head,src,dst"]
        for m in self.morphs:
            rows.append(f"{m['head']},{m.get('src','')},{m.get('dst','')}")
        return "\n".join(rows)

    # ---- scope exports
    def scope_to_jsonld(self, scope_id: str) -> Dict[str, Any]:
        sg = self.scope_graphs.get(scope_id)
        return {"@graph": []} if not sg else sg.to_jsonld()

    def scope_to_ttl(self, scope_id: str) -> str:
        sg = self.scope_graphs.get(scope_id)
        return "" if not sg else sg.to_ttl()

    def scope_to_dot(self, scope_id: str) -> str:
        sg = self.scope_graphs.get(scope_id)
        return "digraph R {}" if not sg else sg.to_dot()

    def scope_to_csv(self, scope_id: str) -> str:
        sg = self.scope_graphs.get(scope_id)
        return "head,src,dst\n" if not sg else sg.to_csv()

    # ---- load / scan
    def load(self, fmt: Optional[str], path: str) -> None:
        suf = (fmt or Path(path).suffix.lstrip('.')).lower()
        data = Path(path).read_text()
        source = str(path)
        if suf in ("md", "markdown"):
            self._scan_markdown_text(data, source)
            return
        if suf in ("jsonld", "json"):
            items = json.loads(data).get("@graph", [])
            for node in items:
                t = node.get("@type")
                node = self._prov(node, source)
                if t == "RelCell":
                    self.cells[node["@id"]] = node
                elif t == "Morphism":
                    self.morphs.append(node)
                elif t == "Scope":
                    self.scopes.append(node)
            return
        if suf == "ttl":
            for line in data.splitlines():
                if 'a :RelCell' in line:
                    name = line.split()[0].lstrip(':')
                    self.add_cell(name, source)
                elif 'a :Morphism' in line:
                    m = re.search(r':head "([^"]+)".*:src :([^ ;]+).*:dst :([^ ;]+)', line)
                    if m:
                        head, src_v, dst_v = m.groups()
                        self.add_morph_def(head, {"src": src_v, "dst": dst_v}, source)
            return
        if suf == "csv":
            for i, line in enumerate(data.splitlines()):
                if i == 0:
                    continue
                head, src_v, dst_v = [x.strip() for x in line.split(',')]
                self.add_morph_def(head, {"src": src_v, "dst": dst_v}, source)
            return
        if suf == "dot":
            for m in re.finditer(r'"([^"]+)"\s*->\s*"([^"]+)"\s*\[label=\"([^\"]+)\"\]', data):
                src_v, dst_v, head = m.groups()
                self.add_morph_def(head, {"src": src_v, "dst": dst_v}, source)
            return
        self.report.add(Severity.WARN, f"Unknown corpus format: {suf}")

    def _scan_markdown_text(self, text: str, source: str) -> None:
        # defs
        for m in FIND_CDEF.finditer(text):
            self.add_cell_def(m.group(1), source)
        for m in FIND_MDEF.finditer(text):
            self.add_morph_def(m.group(1), parse_args(m.group(2)), source)
        # refs
        for m in FIND_CREF.finditer(text):
            name = m.group(1)
            if text[max(0, m.start()-1):m.start()] == '#':
                continue
            self.add_cell_ref(name)
            self.add_cell(name, source)
        for m in FIND_MREF.finditer(text):
            if text[max(0, m.start()-1):m.start()] == '#':
                continue
            self.add_morph_ref(m.group(1), parse_args(m.group(2)), source)
        # scopes
        for m in FIND_OPEN.finditer(text):
            self.add_scope(m.group(1), parse_args(m.group(2)), source)
        for m in FIND_CLOSE.finditer(text):
            self.add_scope(m.group(1), {"close": True}, source)

    # ---- validation
    def validate(self) -> None:
        self.validate_structure()
        self.validate_corpus()
        self.postprocess_cross_scope_ids()
        self.validate_context()

    def validate_structure(self) -> None:
        kind = self.registry.get('kind', {})
        arity = self.registry.get('arity', {})
        for m in self.morphs:
            head = m.get('head')
            if head in kind and kind[head] != 'morphism':
                self.report.add(Severity.ERROR, f"E_HEAD_KIND_MISMATCH: {head} declared {kind[head]} but used as morphism")
            expected_patterns = arity.get(head)
            given = {
                k for k in m.keys()
                if k not in {'@id','@type','head','declared_via','@source','@timestamp','@scope','@contextual','@merged_from','@promoted_from','@src_scope','@dst_scope','@cross_scope','@src_scope_id','@dst_scope_id'}
            }
            if expected_patterns:
                ok = False
                if isinstance(expected_patterns, (list, tuple)) and expected_patterns and isinstance(expected_patterns[0], (list, tuple)):
                    for pat in expected_patterns:
                        if set(pat) <= given:
                            ok = True
                            break
                else:
                    if set(expected_patterns) <= given:
                        ok = True
                if not ok:
                    self.warn_or_error('missing_arity', f"E_ARITY_POLYMORPH_FAIL: {head} did not match any arity pattern; have keys {sorted(given)}")
            if m.get('@cross_scope'):
                policy = (self.lint_cfg.get('cross_scope') or 'ignore').lower()
                if policy == 'warn':
                    self.report.add(Severity.WARN, f"CROSS_SCOPE: {m.get('@id')} uses cross-scope relation")
                elif policy == 'error':
                    self.report.add(Severity.ERROR, f"E_CROSS_SCOPE_POLICY: cross-scope not allowed for {m.get('@id')}")

    def validate_corpus(self) -> None:
        if not self.corpus:
            return
        corpus_cells = set(self.corpus.cells.keys())
        corpus_morph_heads = {mm.get('head') for mm in self.corpus.morphs if 'head' in mm}
        for c in self.refs['cells']:
            if c not in corpus_cells:
                self.warn_or_error('novel_refs', f"Unknown cell reference: {c}")
        for h in self.refs['morph_heads']:
            if h not in corpus_morph_heads:
                self.warn_or_error('novel_refs', f"Unknown morphism reference: {h}")
        for c in self.defs['cells']:
            if c not in corpus_cells:
                self.warn_or_error('novel_cells', f"Novel cell definition: {c}")
        for h in self.defs['morph_heads']:
            if h not in corpus_morph_heads:
                self.warn_or_error('novel_morphs', f"Novel morphism definition: {h}")

    def resolve_scope(self, token: Optional[str]) -> Optional[str]:
        if not token:
            return None
        for s in reversed(self.scopes):
            if s.get('@id') == token:
                return token
        for s in reversed(self.scopes):
            if s.get('head') == token:
                return s.get('@id')
        return None

    def postprocess_cross_scope_ids(self) -> None:
        for m in self.morphs:
            if m.get('@src_scope') and not m.get('@src_scope_id'):
                sid = self.resolve_scope(m['@src_scope'])
                if sid:
                    m['@src_scope_id'] = sid
            if m.get('@dst_scope') and not m.get('@dst_scope_id'):
                sid = self.resolve_scope(m['@dst_scope'])
                if sid:
                    m['@dst_scope_id'] = sid

    def validate_context(self) -> None:
        scoped_ids = {s.get('@id') for s in self.scopes}
        for m in self.morphs:
            if m.get('@contextual') and m.get('@scope') not in scoped_ids:
                self.warn_or_error('orphan_scopes', f"Contextual morphism with missing scope: {m.get('@id')}")
            if m.get('@cross_scope'):
                src_ok = True
                dst_ok = True
                if m.get('@src_scope'):
                    src_ok = (m.get('@src_scope_id') in scoped_ids) if m.get('@src_scope_id') else False
                if m.get('@dst_scope'):
                    dst_ok = (m.get('@dst_scope_id') in scoped_ids) if m.get('@dst_scope_id') else False
                if not src_ok or not dst_ok:
                    self.report.add(Severity.ERROR, f"E_SCOPE_REF_MISSING: {m.get('@id')} references missing scope(s)")
        for cid, c in self.cells.items():
            if c.get('@contextual') and c.get('@scope') not in scoped_ids:
                self.warn_or_error('orphan_scopes', f"Contextual cell with missing scope: {cid}")


# --------------------------------------------------------------------------------------
# Scope Stack helper
# --------------------------------------------------------------------------------------
@dc.dataclass
class ScopeFrame:
    head: str
    args: Dict[str, Any]
    id: str
    locals_cells: Set[str] = dc.field(default_factory=set)
    locals_morphs: List[str] = dc.field(default_factory=list)


class ScopeStack:
    def __init__(self) -> None:
        self._stack: List[ScopeFrame] = []

    def push(self, head: str, args: Dict[str, Any]) -> ScopeFrame:
        sid = stable_id(head, json.dumps(args, sort_keys=True))
        fr = ScopeFrame(head=head, args=dict(args), id=sid)
        self._stack.append(fr)
        return fr

    def pop(self, head: Optional[str] = None) -> Optional[ScopeFrame]:
        if not self._stack:
            return None
        top = self._stack[-1]
        if head is None or head == top.head:
            return self._stack.pop()
        return None

    def nearest_args(self) -> Dict[str, Any]:
        return self._stack[-1].args if self._stack else {}

    def current_id(self) -> Optional[str]:
        return self._stack[-1].id if self._stack else None

    def has(self) -> bool:
        return bool(self._stack)


# --------------------------------------------------------------------------------------
# Inline expansion (panflute callbacks)
# --------------------------------------------------------------------------------------
_graph: Optional[RelGraph] = None
_scopes = ScopeStack()


def _inherit_args(args: Dict[str, Any]) -> Dict[str, Any]:
    if not _scopes.has():
        return args
    merged = dict(_scopes.nearest_args())
    merged.update(args)
    return merged


def _tag_scoped(node: Dict[str, Any]) -> Dict[str, Any]:
    sid = _scopes.current_id()
    if sid is not None and _graph is not None:
        node['@scope'] = sid
        node['@contextual'] = True
        _graph.mirror_into_scope(node, sid)
    return node


def expand_markdown_inlines(text: str) -> List[pf.Element]:
    out: List[pf.Element] = []
    i, L = 0, len(text)
    patterns = [
        ('open', RE_OPEN), ('close', RE_CLOSE),
        ('mdef', RE_MORPH_DEF), ('mref', RE_MORPH_REF),
        ('cdef', RE_CELL_DEF), ('cref', RE_CELL_REF),
    ]
    while i < L:
        earliest = None
        kind = None
        for k, rx in patterns:
            m = rx.search(text, i)
            if m and (earliest is None or m.start() < earliest.start()):
                earliest = m; kind = k
        if not earliest:
            out.append(pf.Str(text[i:]))
            break
        if earliest.start() > i:
            out.append(pf.Str(text[i:earliest.start()]))
        m = earliest
        if kind == 'open':
            head, argstr = m.groups(); args = parse_args(argstr)
            fr = _scopes.push(head, args)
            if _graph is not None:
                _graph.add_scope(head, {**args, 'scope_id': fr.id})
                _graph.ensure_scope_graph(fr.id, head=head, args=args)
            out.append(span(["open"], {"data-head": head, "data-args": serialize_args(args)}))
        elif kind == 'close':
            head = m.group(1)
            _scopes.pop(head)
            out.append(span(["close"], {"data-head": head}))
        elif kind == 'mdef':
            head, argstr = m.groups(); args = _inherit_args(parse_args(argstr))
            assert _graph is not None
            _graph.add_morph_def(head, args)
            _tag_scoped(_graph.morphs[-1])
            out.append(span(["morphism","def"], {"data-head": head, "data-args": serialize_args(args)}))
        elif kind == 'mref':
            head, argstr = m.groups(); args = _inherit_args(parse_args(argstr))
            assert _graph is not None
            _graph.add_morph_ref(head, args)
            _tag_scoped(_graph.morphs[-1])
            out.append(span(["morphism","ref"], {"data-head": head, "data-args": serialize_args(args)}))
        elif kind == 'cdef':
            name = m.group(1)
            assert _graph is not None
            _graph.add_cell_def(name)
            _tag_scoped(_graph.cells[name])
            out.append(span(["relcell","def"], {"data-name": name}, name))
        elif kind == 'cref':
            name = m.group(1)
            if text[max(0, m.start()-1):m.start()] == '#':
                out.append(pf.Str(text[m.start():m.end()]))
            else:
                assert _graph is not None
                _graph.add_cell_ref(name)
                _graph.add_cell(name)
                _tag_scoped(_graph.cells[name])
                out.append(span(["relcell","ref"], {"data-name": name}, name))
        i = m.end()
    return out


def replace_inlines(elem: pf.Element, doc: pf.Doc) -> Optional[List[pf.Element]]:
    if isinstance(elem, pf.Str):
        parts = expand_markdown_inlines(elem.text)
        if len(parts) == 1 and isinstance(parts[0], pf.Str) and parts[0].text == elem.text:
            return None
        return parts
    return None


# --------------------------------------------------------------------------------------
# Finalization / Emit
# --------------------------------------------------------------------------------------
class FilterExit(Exception):
    def __init__(self, code: int) -> None:
        super().__init__(f"Filter exit {code}")
        self.code = code


def _write_scope_files(graph: RelGraph, fmt: str, outdir: str) -> None:
    d = Path(outdir)
    d.mkdir(parents=True, exist_ok=True)
    for s in graph.scopes:
        sid = s.get('@id')
        head = s.get('head', 'scope')
        base = f"{head}_{sid}"
        if fmt == 'jsonld':
            (d / f"{base}.jsonld").write_text(json.dumps(graph.scope_to_jsonld(sid), indent=2))
        elif fmt == 'ttl':
            (d / f"{base}.ttl").write_text(graph.scope_to_ttl(sid))
        elif fmt == 'dot':
            (d / f"{base}.dot").write_text(graph.scope_to_dot(sid))
        elif fmt == 'csv':
            (d / f"{base}.csv").write_text(graph.scope_to_csv(sid))


def finalize(doc: pf.Doc) -> None:
    assert _graph is not None

    # Load registry.yaml (optional)
    registry_path = Path('registry.yaml')
    registry = {}
    if registry_path.exists() and yaml is not None:
        try:
            registry = yaml.safe_load(open(registry_path)) or {}
        except Exception as e:
            LOG.warning("Failed to load registry.yaml: %s", e)
    _graph.registry = registry

    # Lint configuration
    lint_cfg = doc.get_metadata('lint') or {}
    cs_policy = doc.get_metadata('cross_scope')
    if cs_policy:
        lint_cfg = dict(lint_cfg)
        mapping = {'allow': 'ignore', 'warn': 'warn', 'deny': 'error'}
        lint_cfg['cross_scope'] = mapping.get(str(cs_policy).lower(), 'ignore')
    _graph.lint_cfg = lint_cfg

    # Load external corpora
    reg_item = doc.get_metadata('registry')
    if reg_item:
        base = RelGraph(default_source="corpus")
        paths = reg_item if isinstance(reg_item, list) else [reg_item]
        for p in paths:
            p = str(p)
            suffix = Path(p).suffix.lstrip('.')
            try:
                tmp = RelGraph(default_source=p)
                tmp.load(suffix, p)
                for cid, cnode in tmp.cells.items():
                    base.cells[cid] = cnode
                base.morphs.extend(tmp.morphs)
                base.scopes.extend(tmp.scopes)
            except Exception as e:
                LOG.warning("Failed to load corpus %s: %s", p, e)
        _graph.corpus = base

    # Validate
    _graph.validate()

    # Reports
    report_path = doc.get_metadata('report')
    if report_path:
        try:
            write_report(_graph.report, str(report_path))
        except Exception as e:
            LOG.warning("Failed to write report %s: %s", report_path, e)

    lint_mode = (str(doc.get_metadata('lint_mode') or '').lower() or 'strict')
    has_errors = bool(_graph.report.errors)

    # Emit
    emit = str(doc.get_metadata('emit', 'html')).lower()
    emit_mode = str(doc.get_metadata('emit_mode') or 'contextual').lower()
    emit_scopes = bool(doc.get_metadata('emit_scopes'))
    emit_scopes_dir = doc.get_metadata('emit_scopes_dir')

    # Promote scopes for merged mode
    if emit_mode == 'merged':
        for s in _graph.scopes:
            sid = s.get('@id')
            _graph.promote_scope(sid)

    if emit in ('jsonld', 'ttl', 'dot', 'csv'):
        if emit_mode == 'contextual' and emit_scopes and emit_scopes_dir:
            try:
                _write_scope_files(_graph, emit, emit_scopes_dir)
            except Exception as e:
                LOG.warning("Failed to write scope files: %s", e)

        if emit == 'jsonld':
            print(json.dumps(_graph.to_jsonld(), indent=2))
        elif emit == 'ttl':
            print(_graph.to_ttl())
        elif emit == 'dot':
            print(_graph.to_dot())
        elif emit == 'csv':
            print(_graph.to_csv())

        raise FilterExit(1 if (lint_mode == 'strict' and has_errors) else 0)

    # Normal Pandoc flow: respect strict mode
    if lint_mode == 'strict' and has_errors:
        raise FilterExit(1)


# --------------------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------------------

def main(doc: Optional[pf.Doc] = None) -> Any:
    global _graph, _scopes
    _graph = RelGraph(default_source="stdin")
    _scopes = ScopeStack()
    try:
        return pf.run_filter(replace_inlines, finalize=finalize, doc=doc)
    except FilterExit as e:
        sys.exit(e.code)


if __name__ == "__main__":
    main()
