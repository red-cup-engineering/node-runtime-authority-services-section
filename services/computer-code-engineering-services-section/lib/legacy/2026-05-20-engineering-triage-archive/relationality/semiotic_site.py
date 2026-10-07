#!/usr/bin/env python3
"""
Semiotic publisher: compute a semiotic universe over a vault and publish to static targets
(HTML/JSON/RDF/OpenAPI) and optionally Pandoc outputs (single doc or book).
Implements a computable subset of the semiotic universe outlined in the docs:
- Atoms form a finite feature set (powerset Heyting approximation).
- j-modality is a graph closure over atoms.
- G-trace is currently identity (placeholder for provenance/time enrichment).
- Fragments and semantics are computed via j/G closure.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from jinja2 import Environment, DictLoader, select_autoescape
from markdown_it import MarkdownIt
from rdflib import Graph, Literal, Namespace, RDF, XSD


# ----------------------------
# Imports and constants
# ----------------------------
FeatureSet = frozenset[int]
AtomId = int
ANNOTATION_INTERPRETERS: Dict[str, Callable[["Universe", "Concept", "AnnotationTerm"], FeatureSet]] = {}
MARKDOWN = MarkdownIt()


# ----------------------------
# Datamodel
# ----------------------------
@dataclass
class Atom:
    """Atom a ∈ A representing a primitive feature."""

    id: int
    kind: str
    value: str


@dataclass
class AnnotationTerm:
    """Annotation term mapping vault syntax to definable operators."""

    op: str
    args: List[str]


@dataclass
class Concept:
    """Concept k with fragment and semantic contribution."""

    id: str
    title: str
    path: Path
    body_markdown: str
    metadata: Dict[str, Any]
    annotations: List[AnnotationTerm]
    subjects: Dict[str, str] = field(default_factory=dict)
    facts: List[Tuple[str, str, str]] = field(default_factory=list)
    created: Optional[str] = None
    updated: Optional[str] = None
    folders: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    status: Optional[str] = None
    type: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    base_features: FeatureSet = field(default_factory=frozenset)
    fragment: FeatureSet = field(default_factory=frozenset)
    semantic: FeatureSet = field(default_factory=frozenset)
    evaluation_score: float = 0.0


@dataclass
class Config:
    """Configurable closure rules and export settings."""

    base_url: str = "http://example.org/"
    site_title: str = "Semiotic Site"
    vault_dir: Optional[str] = None
    output_dir: Optional[str] = None
    mode: str = "site"  # "site" or "doc"
    targets: List[str] = field(default_factory=lambda: ["html", "json", "rdf", "openapi"])
    pandoc_enabled: bool = False
    pandoc_formats: List[str] = field(default_factory=list)
    pandoc_template: Optional[str] = None
    pandoc_filters: List[str] = field(default_factory=list)
    pandoc_output_single: Optional[str] = None
    pandoc_book_title: Optional[str] = None
    ignore: List[str] = field(default_factory=list)
    folder_tag_rules: Dict[str, str] = field(default_factory=dict)
    tag_synonyms: Dict[str, str] = field(default_factory=dict)
    type_tag_rules: Dict[str, str] = field(default_factory=dict)
    status_tag_rules: Dict[str, str] = field(default_factory=dict)
    publish_statuses: List[str] = field(default_factory=list)
    draft_statuses: List[str] = field(default_factory=list)
    lint_strict: bool = False


@dataclass
class Universe:
    """Semiotic universe U with atoms, j-relations, and concept registry."""

    atoms: Dict[int, Atom] = field(default_factory=dict)
    atom_index: Dict[Tuple[str, str], int] = field(default_factory=dict)
    next_atom_id: int = 0
    concepts: Dict[str, Concept] = field(default_factory=dict)
    j_relations: Dict[int, Set[int]] = field(default_factory=dict)
    config: Config = field(default_factory=Config)
    indices: Dict[str, Dict[str, Set[str]]] = field(default_factory=dict)


# ----------------------------
# Semiotic core
# ----------------------------
def intern_atom(universe: Universe, kind: str, value: str) -> AtomId:
    """Intern (kind,value) → atom id, constructing atoms as needed."""
    key = (kind, value)
    if key in universe.atom_index:
        return universe.atom_index[key]
    atom_id = universe.next_atom_id
    universe.next_atom_id += 1
    universe.atom_index[key] = atom_id
    universe.atoms[atom_id] = Atom(id=atom_id, kind=kind, value=value)
    return atom_id


def j_closure(universe: Universe, features: FeatureSet) -> FeatureSet:
    """Compute j-closure (graph reachability) ensuring extensivity, monotonicity, idempotence."""
    closure: Set[int] = set(features)
    frontier: List[int] = list(features)
    while frontier:
        aid = frontier.pop()
        for nxt in universe.j_relations.get(aid, set()):
            if nxt not in closure:
                closure.add(nxt)
                frontier.append(nxt)
    return frozenset(closure)


def temporal_atoms(universe: Universe, concept: Concept) -> FeatureSet:
    """Derive temporal/provenance atoms from created/updated metadata (Heyting trace witness)."""
    atoms: Set[int] = set()
    if concept.created:
        atoms.add(intern_atom(universe, "created", concept.created))
        atoms.add(intern_atom(universe, "created_year", concept.created[:4]))
    if concept.updated:
        atoms.add(intern_atom(universe, "updated", concept.updated))
        atoms.add(intern_atom(universe, "updated_year", concept.updated[:4]))
    return frozenset(atoms)


def G_trace(universe: Universe, concept: Concept, features: FeatureSet) -> FeatureSet:
    """Trace comonad G: enrich features with temporal atoms to approximate provenance semantics."""
    enriched = set(features)
    enriched.update(temporal_atoms(universe, concept))
    return frozenset(enriched)


def closure_with_jG(universe: Universe, concept: Concept, seed: FeatureSet) -> FeatureSet:
    """Iteratively apply G then j to reach a fixed point (fragment/semantic closure)."""
    current = set(seed)
    changed = True
    while changed:
        before = frozenset(current)
        after = j_closure(universe, G_trace(universe, concept, frozenset(current)))
        current = set(after)
        changed = before != after
    return frozenset(current)


def build_concept_fragment(universe: Universe, concept: Concept) -> FeatureSet:
    """Compute fragment F_{k,X} as least j,G-closed feature set containing annotations."""
    concept.fragment = closure_with_jG(universe, concept, concept.base_features)
    return concept.fragment


def build_concept_semantics(universe: Universe, concept: Concept) -> FeatureSet:
    """Compute semantic contribution Sem_X(k) as one more closure step over fragment."""
    concept.semantic = closure_with_jG(universe, concept, concept.fragment)
    return concept.semantic


def semantic_delta(a: Concept, b: Concept) -> FeatureSet:
    """Delta_sem(k,k') = semantics(b) \\ semantics(a)."""
    return frozenset(b.semantic - a.semantic)


def evaluate_concept(universe: Universe, concept: Concept) -> float:
    """Evaluate concept via simple monoid score (#tags + 0.5 * #links)."""
    tags = 0
    links = 0
    facts = 0
    temporal = 0
    for aid in concept.semantic:
        atom = universe.atoms[aid]
        if atom.kind == "tag":
            tags += 1
        elif atom.kind == "link":
            links += 1
        elif atom.kind == "fact":
            facts += 1
        elif atom.kind in {"created_year", "updated_year"}:
            temporal += 1
    score = float(tags + 0.5 * links + 0.3 * facts + 0.1 * temporal)
    concept.evaluation_score = score
    return score


def evaluation_components(universe: Universe, concept: Concept) -> Dict[str, Any]:
    """Recover evaluation components used for a concept's score."""
    tags = 0
    links = 0
    facts = 0
    temporal = 0
    for aid in concept.semantic:
        atom = universe.atoms[aid]
        if atom.kind == "tag":
            tags += 1
        elif atom.kind == "link":
            links += 1
        elif atom.kind == "fact":
            facts += 1
        elif atom.kind in {"created_year", "updated_year"}:
            temporal += 1
    score = float(tags + 0.5 * links + 0.3 * facts + 0.1 * temporal)
    return {
        "tags": tags,
        "links": links,
        "facts": facts,
        "temporal_years": temporal,
        "score": score,
    }


def evaluation_label(score: float) -> str:
    """Qualitative label for evaluation score bands."""
    if score <= 1.0:
        return "sparsely connected"
    if score <= 3.0:
        return "moderately connected"
    return "densely connected"


# ----------------------------
# Annotation interpretation
# ----------------------------
def register_annotation(op: str):
    """Decorator to register annotation interpreter."""

    def wrapper(func: Callable[[Universe, Concept, AnnotationTerm], FeatureSet]):
        ANNOTATION_INTERPRETERS[op] = func
        return func

    return wrapper


@register_annotation("HasTag")
def interpret_tag(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    atom_id = intern_atom(universe, "tag", term.args[0])
    return frozenset({atom_id})


@register_annotation("InFolder")
def interpret_folder(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    atom_id = intern_atom(universe, "folder", term.args[0])
    return frozenset({atom_id})


@register_annotation("LinksTo")
def interpret_link(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    atom_id = intern_atom(universe, "link", term.args[0])
    return frozenset({atom_id})


@register_annotation("HasStatus")
def interpret_status(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    atom_id = intern_atom(universe, "status", term.args[0])
    return frozenset({atom_id})


@register_annotation("HasType")
def interpret_type(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    atom_id = intern_atom(universe, "type", term.args[0])
    return frozenset({atom_id})


@register_annotation("AliasFor")
def interpret_alias(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    atom_id = intern_atom(universe, "alias", term.args[0])
    return frozenset({atom_id})


@register_annotation("Fact")
def interpret_fact(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    """Interpret predicate(subject, object) as a fact atom."""
    predicate, subject_id, object_id = term.args
    atom_value = f"{predicate}:{subject_id}->{object_id}"
    atom_id = intern_atom(universe, "fact", atom_value)
    return frozenset({atom_id})


def interpret_annotations(universe: Universe, concept: Concept) -> FeatureSet:
    """Interpret annotation terms into base feature set."""
    features: Set[int] = set()
    for term in concept.annotations:
        interpreter = ANNOTATION_INTERPRETERS.get(term.op)
        if interpreter:
            features.update(interpreter(universe, concept, term))
    concept.base_features = frozenset(features)
    return concept.base_features


# ----------------------------
# Vault parsing
# ----------------------------
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def load_markdown_with_frontmatter(path: Path) -> Tuple[Dict[str, Any], str]:
    """Load markdown file and split YAML frontmatter from body.

    Frontmatter is expected to be at the top of the file, delimited by lines
    consisting solely of '---'. If YAML or parsing fails, metadata is empty
    and the entire file is treated as body.
    """
    text = path.read_text(encoding="utf-8")
    metadata: Dict[str, Any] = {}
    body = text

    # Only attempt to parse if we see a frontmatter delimiter near the top.
    if text.lstrip().startswith("---"):
        lines = text.splitlines(keepends=True)
        start = None
        for idx, line in enumerate(lines):
            if line.strip() == "---":
                start = idx
                break
        if start is not None:
            fm_lines: List[str] = []
            end = None
            for idx in range(start + 1, len(lines)):
                line = lines[idx]
                if line.strip() == "---":
                    end = idx
                    break
                fm_lines.append(line)
            if end is not None:
                fm_text = "".join(fm_lines)
                try:
                    import yaml  # type: ignore

                    loaded = yaml.safe_load(fm_text) or {}
                    if isinstance(loaded, dict):
                        metadata = dict(loaded)
                except Exception:
                    metadata = {}
                body = "".join(lines[end + 1 :])

    return metadata, body


def slugify(text: str) -> str:
    """Normalize IDs to safe slugs."""
    lowered = text.strip().lower()
    replaced = re.sub(r"[\\/]+", "-", lowered)
    replaced = re.sub(r"[^a-z0-9_-]+", "-", replaced)
    replaced = re.sub(r"-{2,}", "-", replaced).strip("-")
    return replaced or "item"


def extract_links(markdown_text: str) -> List[str]:
    """Extract vault-internal link targets from markdown/wikilink syntax."""
    links: List[str] = []
    for match in WIKILINK_RE.finditer(markdown_text):
        target = slugify(match.group(1))
        links.append(target)
    for match in MARKDOWN_LINK_RE.finditer(markdown_text):
        target = match.group(2)
        if re.match(r"^[a-z]+://", target):
            continue
        target_path = slugify(Path(target).with_suffix("").as_posix())
        links.append(target_path)
    return links


def collect_folders(vault_root: Path, file_path: Path) -> List[str]:
    """Collect folder annotations from path segments."""
    rel = file_path.relative_to(vault_root)
    parts = list(rel.parts[:-1])
    return [slugify(p) for p in parts if p]


def load_markdown_concept(path: Path, vault_root: Path) -> Concept:
    """Load markdown with frontmatter, derive annotations from metadata and structure."""
    metadata, body = load_markdown_with_frontmatter(path)
    metadata = dict(metadata or {})
    rel = path.relative_to(vault_root)
    concept_id = slugify(metadata.get("id") or rel.with_suffix("").as_posix())
    title = metadata.get("title") or rel.stem
    folders = collect_folders(vault_root, path)
    links = extract_links(body)
    tags = [str(t) for t in metadata.get("tags", [])]
    aliases = [str(a) for a in metadata.get("aliases", [])]
    status = metadata.get("status")
    ctype = metadata.get("type")
    created = metadata.get("created")
    updated = metadata.get("updated")

    annotations: List[AnnotationTerm] = []
    raw_subjects = metadata.get("subjects", {}) or {}
    subjects = {str(alias): slugify(str(target)) for alias, target in raw_subjects.items()}
    facts_terms: List[Tuple[str, str, str]] = []

    raw_facts = metadata.get("facts", {}) or {}
    if isinstance(raw_facts, dict):
        for subject_alias, predicate_map in raw_facts.items():
            subject_id = subjects.get(subject_alias, slugify(str(subject_alias)))
            if not isinstance(predicate_map, dict):
                continue
            for predicate, objects in predicate_map.items():
                objs_iter: Iterable[Any]
                if isinstance(objects, (list, tuple)):
                    objs_iter = objects
                else:
                    objs_iter = [objects]
                for obj in objs_iter:
                    obj_id = subjects.get(str(obj), slugify(str(obj)))
                    facts_terms.append((str(predicate), subject_id, obj_id))
                    annotations.append(AnnotationTerm(op="Fact", args=[str(predicate), subject_id, obj_id]))

    for tag in tags:
        annotations.append(AnnotationTerm(op="HasTag", args=[tag]))
    if status:
        annotations.append(AnnotationTerm(op="HasStatus", args=[str(status)]))
    if ctype:
        annotations.append(AnnotationTerm(op="HasType", args=[str(ctype)]))
    for alias in aliases:
        annotations.append(AnnotationTerm(op="AliasFor", args=[alias]))
    for folder in folders:
        annotations.append(AnnotationTerm(op="InFolder", args=[folder]))
    for link in links:
        annotations.append(AnnotationTerm(op="LinksTo", args=[link]))

    return Concept(
        id=concept_id,
        title=title,
        path=path,
        body_markdown=body,
        metadata=metadata,
        annotations=annotations,
        subjects=subjects,
        facts=facts_terms,
        folders=folders,
        links=links,
        tags=tags,
        status=status,
        type=ctype,
        aliases=aliases,
        created=str(created) if created else None,
        updated=str(updated) if updated else None,
    )


# ----------------------------
# Universe builder
# ----------------------------
def load_config(config_path: Optional[Path]) -> Config:
    """Load Config from YAML if provided, else defaults."""
    cfg = Config()
    if config_path is None or not config_path.exists():
        return cfg
    try:
        import yaml  # type: ignore
    except Exception:
        print("YAML not available; using default configuration.")
        return cfg
    data = yaml.safe_load(config_path.read_text()) or {}
    cfg.base_url = data.get("base_url", cfg.base_url)
    cfg.site_title = data.get("site_title", cfg.site_title)
    cfg.vault_dir = data.get("vault_dir", cfg.vault_dir)
    cfg.output_dir = data.get("output_dir", cfg.output_dir)
    cfg.mode = data.get("mode", cfg.mode)
    cfg.targets = data.get("targets", cfg.targets)
    cfg.pandoc_enabled = data.get("pandoc_enabled", cfg.pandoc_enabled)
    cfg.pandoc_formats = data.get("pandoc_formats", cfg.pandoc_formats)
    cfg.pandoc_template = data.get("pandoc_template", cfg.pandoc_template)
    cfg.pandoc_filters = data.get("pandoc_filters", cfg.pandoc_filters)
    cfg.pandoc_output_single = data.get("pandoc_output_single", cfg.pandoc_output_single)
    cfg.pandoc_book_title = data.get("pandoc_book_title", cfg.pandoc_book_title)
    cfg.ignore = list(data.get("ignore", cfg.ignore))
    cfg.folder_tag_rules = dict(data.get("folder_tag_rules", cfg.folder_tag_rules))
    cfg.tag_synonyms = dict(data.get("tag_synonyms", cfg.tag_synonyms))
    cfg.type_tag_rules = dict(data.get("type_tag_rules", cfg.type_tag_rules))
    cfg.status_tag_rules = dict(data.get("status_tag_rules", cfg.status_tag_rules))
    cfg.publish_statuses = list(data.get("publish_statuses", cfg.publish_statuses))
    cfg.draft_statuses = list(data.get("draft_statuses", cfg.draft_statuses))
    cfg.lint_strict = bool(data.get("lint_strict", cfg.lint_strict))
    return cfg


def configure_j_relations(universe: Universe) -> None:
    """Populate j-relations using config rules (folder→tag, synonyms, type/status implications)."""
    cfg = universe.config
    for folder, tag in cfg.folder_tag_rules.items():
        src = intern_atom(universe, "folder", folder)
        dst = intern_atom(universe, "tag", tag)
        universe.j_relations.setdefault(src, set()).add(dst)
    for src_tag, dst_tag in cfg.tag_synonyms.items():
        a = intern_atom(universe, "tag", src_tag)
        b = intern_atom(universe, "tag", dst_tag)
        universe.j_relations.setdefault(a, set()).add(b)
        universe.j_relations.setdefault(b, set()).add(a)
    for type_value, tag in cfg.type_tag_rules.items():
        a = intern_atom(universe, "type", type_value)
        b = intern_atom(universe, "tag", tag)
        universe.j_relations.setdefault(a, set()).add(b)
    for status_value, tag in cfg.status_tag_rules.items():
        a = intern_atom(universe, "status", status_value)
        b = intern_atom(universe, "tag", tag)
        universe.j_relations.setdefault(a, set()).add(b)


def build_indices(universe: Universe) -> None:
    """Construct simple indices (tag, folder, type, status) from semantic features."""
    tag_index: Dict[str, Set[str]] = {}
    folder_index: Dict[str, Set[str]] = {}
    type_index: Dict[str, Set[str]] = {}
    status_index: Dict[str, Set[str]] = {}
    for concept in universe.concepts.values():
        for aid in concept.semantic:
            atom = universe.atoms[aid]
            if atom.kind == "tag":
                tag_index.setdefault(atom.value, set()).add(concept.id)
            elif atom.kind == "folder":
                folder_index.setdefault(atom.value, set()).add(concept.id)
            elif atom.kind == "type":
                type_index.setdefault(atom.value, set()).add(concept.id)
            elif atom.kind == "status":
                status_index.setdefault(atom.value, set()).add(concept.id)
    universe.indices = {
        "tag": tag_index,
        "folder": folder_index,
        "type": type_index,
        "status": status_index,
    }


def build_universe(vault_dir: Path, config: Config, log: Callable[[str], None] | None = None) -> Universe:
    """Build universe: load concepts, interpret annotations, close fragments/semantics, evaluate."""
    logger = log or (lambda msg: None)
    universe = Universe(config=config)

    logger("Collecting markdown concepts")
    for path in vault_dir.rglob("*.md"):
        rel = path.relative_to(vault_dir)
        rel_str = rel.as_posix()
        if any(fnmatch.fnmatch(rel_str, pattern) for pattern in config.ignore):
            continue
        concept = load_markdown_concept(path, vault_dir)
        if concept.id in universe.concepts:
            logger(f"Duplicate concept id {concept.id}; overwriting previous entry.")
        universe.concepts[concept.id] = concept

    logger("Interpreting annotations to base features")
    for concept in universe.concepts.values():
        interpret_annotations(universe, concept)

    logger("Configuring j-relations")
    configure_j_relations(universe)

    logger("Computing fragments, semantics, and evaluations")
    for concept in universe.concepts.values():
        build_concept_fragment(universe, concept)
        build_concept_semantics(universe, concept)
        evaluate_concept(universe, concept)

    logger("Building indices")
    build_indices(universe)
    return universe


# ----------------------------
# Exporters
# ----------------------------
BASE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ title }}</title>
  <style>
    :root {
      --font-body: "Georgia", "Times New Roman", serif;
      --font-ui: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --font-mono: "SF Mono", ui-monospace, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --line-height-body: 1.6;
      --space-1: 0.25rem;
      --space-2: 0.5rem;
      --space-3: 0.75rem;
      --space-4: 1rem;
      --space-5: 1.5rem;
      --space-6: 2rem;
      --space-7: 3rem;
      --radius-1: 2px;
      --radius-2: 4px;
      --color-bg: #ffe;
      --color-bg-elevated: #eed;
      --color-ink: #312;
      --color-ink-muted: #756;
      --color-border-subtle: #756;
      --color-accent: #880;
      --color-accent-soft: #eed;
      --link-color: #880;
      --link-hover-color: #aa2;
      --link-visited-color: #934;
      --link-visited-hover-color: #b56;
      --external-link-color: #008;
      --external-link-hover-color: #60b;
      --external-link-visited-color: #172;
      --external-link-visited-hover-color: #394;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      padding: var(--space-6) var(--space-4) var(--space-7);
      background: var(--color-bg);
      color: var(--color-ink);
      font-family: var(--font-body);
      font-size: 16px;
      line-height: var(--line-height-body);
    }

    header.site-header {
      max-width: 72rem;
      margin: 0 auto var(--space-5);
      padding: 0 var(--space-2);
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      border-bottom: 1px solid var(--color-border-subtle);
    }

    .site-title {
      margin: 0;
      font-family: var(--font-ui);
      font-size: 1.125rem;
      font-weight: 500;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    .site-nav {
      display: flex;
      gap: var(--space-3);
      align-items: baseline;
    }

    .site-nav a {
      font-family: var(--font-ui);
      font-size: 0.8rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      text-decoration: none;
      color: var(--color-ink-muted);
      border-bottom: none;
    }

    .site-nav a:hover,
    .site-nav a:focus {
      color: var(--color-accent);
      text-decoration: underline;
      text-decoration-thickness: 0.08em;
      text-underline-offset: 0.16em;
    }

    .page-main {
      max-width: 72rem;
      margin: 0 auto;
      padding: 0 var(--space-2);
    }

    a,
    .link {
      text-decoration: none;
      color: var(--link-color);
      display: inline;
      position: relative;
      border-bottom: 0.1rem dotted;
      line-height: 1.2;
      transition: border 0.3s;
    }

    a:hover,
    a:focus {
      color: var(--link-hover-color);
      outline-style: none;
      border-bottom: 0.1rem solid;
    }

    a:visited {
      color: var(--link-visited-color);
    }

    a:visited:hover,
    a:visited:focus {
      color: var(--link-visited-hover-color);
    }

    h1, h2, h3, h4 {
      font-family: var(--font-ui);
      font-weight: 500;
      letter-spacing: 0.03em;
      text-rendering: optimizeLegibility;
    }

    h2 {
      font-size: 1.4rem;
      margin: 0 0 var(--space-2);
    }

    h3 {
      font-size: 1rem;
      margin: 0 0 var(--space-2);
    }

    p {
      margin: 0 0 var(--space-3);
    }

    ul, ol {
      margin: 0 0 var(--space-3) 1.25rem;
      padding: 0;
    }

    code, pre {
      font-family: var(--font-mono);
      font-size: 0.9em;
    }

    .meta {
      font-family: var(--font-ui);
      font-size: 0.78rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--color-ink-muted);
    }

    .meta-row {
      display: flex;
      justify-content: space-between;
      gap: var(--space-3);
      margin: 0 0 var(--space-2);
    }

    .meta-label {
      font-family: var(--font-ui);
      font-size: 0.72rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--color-ink-muted);
      white-space: nowrap;
    }

    .meta-value {
      font-family: var(--font-body);
      font-size: 0.9rem;
      letter-spacing: 0;
      text-transform: none;
      color: var(--color-ink);
      text-align: right;
      flex: 1;
    }

    .meta-block {
      margin-top: var(--space-4);
    }

    .score {
      font-weight: 500;
      letter-spacing: 0.08em;
    }

    /* Concept page layout */
    .concept-page {
      margin-bottom: var(--space-7);
    }

    .concept-header {
      margin-bottom: var(--space-4);
    }

    .concept-status-pill {
      display: inline-flex;
      align-items: center;
      padding: 0.1rem 0.6rem;
      margin: 0 0 var(--space-2);
      border-radius: 999px;
      border: 1px solid var(--color-border-subtle);
      font-family: var(--font-ui);
      font-size: 0.7rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      background: #f5f3ea;
      color: var(--color-ink-muted);
    }

    .concept-status-pill--sketch {
      border-color: rgba(177, 92, 0, 0.7);
      background: rgba(177, 92, 0, 0.12);
      color: #5c3300;
    }

    .concept-status-pill--draft {
      border-color: rgba(177, 92, 0, 0.6);
      background: rgba(177, 92, 0, 0.06);
      color: #6e3a00;
    }

    .concept-status-pill--stable,
    .concept-status-pill--public {
      border-color: rgba(40, 94, 54, 0.7);
      background: rgba(40, 94, 54, 0.08);
      color: #245035;
    }

    .concept-status-pill--deprecated {
      border-color: rgba(90, 80, 70, 0.6);
      background: rgba(90, 80, 70, 0.06);
      color: #4a4036;
    }

    .concept-page--status-sketch .concept-meta {
      border-left-color: rgba(177, 92, 0, 0.8);
    }

    .concept-page--status-draft .concept-meta {
      border-left-color: rgba(177, 92, 0, 0.6);
    }

    .concept-page--status-stable .concept-meta,
    .concept-page--status-public .concept-meta {
      border-left-color: rgba(40, 94, 54, 0.7);
    }

    .concept-page--status-deprecated .concept-meta {
      border-left-color: rgba(90, 80, 70, 0.7);
    }

    .concept-title {
      font-size: 1.6rem;
      margin: 0;
    }

    .concept-evaluation {
      margin-top: var(--space-2);
    }

    .evaluation-meter {
      position: relative;
      height: 0.18rem;
      max-width: 12rem;
      border-radius: 999px;
      background: linear-gradient(to right, var(--color-accent) 0, var(--color-accent) 55%, transparent 55%);
      background-color: #d2d7e3;
      overflow: hidden;
    }

    .evaluation-label {
      margin-top: var(--space-2);
    }

    .concept-layout {
      display: grid;
      grid-template-columns: minmax(14rem, 18rem) minmax(0, 1fr);
      column-gap: var(--space-6);
      align-items: flex-start;
    }

    .concept-meta {
      padding-left: var(--space-3);
      border-left: 1px solid var(--color-border-subtle);
    }

    .concept-body {
      max-width: 70ch;
    }

    .body-html > *:first-child {
      margin-top: 0;
    }

    /* Tags / chips */
    .chip-list {
      list-style: none;
      margin: var(--space-2) 0 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
    }

    .chip {
      border-radius: var(--radius-2);
      border: 1px solid var(--color-border-subtle);
      background: #f1f0ea;
      padding: 0.15rem 0.55rem;
      font-family: var(--font-ui);
      font-size: 0.75rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--color-ink-muted);
      white-space: nowrap;
    }

    /* Related concepts */
    .related {
      margin-top: var(--space-6);
      padding-top: var(--space-4);
      border-top: 1px solid var(--color-border-subtle);
    }

    .related-heading {
      font-size: 0.95rem;
      margin: 0 0 var(--space-3);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--color-ink-muted);
    }

    .related-list {
      list-style: none;
      margin: 0;
      padding: 0;
    }

    .related-item {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: var(--space-3);
      margin-bottom: var(--space-2);
    }

    .related-link {
      flex: 1;
    }

    .related-score {
      font-size: 0.75rem;
    }

    /* Index layout */
    .index-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
      gap: var(--space-4);
      margin: var(--space-2) 0 var(--space-6);
    }

    .index-card {
      background: var(--color-bg-elevated);
      border: 1px solid var(--color-border-subtle);
      border-radius: var(--radius-2);
      padding: var(--space-4);
    }

    .index-card-title {
      font-size: 0.95rem;
      margin: 0 0 var(--space-3);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--color-ink-muted);
    }

    .index-metrics {
      margin: 0;
      padding: 0;
    }

    .index-metric {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: var(--space-3);
      font-size: 0.9rem;
      margin-bottom: var(--space-1);
    }

    .index-metric dt {
      font-family: var(--font-ui);
      font-size: 0.75rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--color-ink-muted);
    }

    .index-metric dd {
      margin: 0;
      font-family: var(--font-body);
      color: var(--color-ink);
    }

    .index-section {
      margin-bottom: var(--space-6);
    }

    .index-section-title {
      font-size: 1rem;
      margin: 0 0 var(--space-3);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--color-ink-muted);
    }

    .index-list {
      list-style: none;
      margin: 0;
      padding: 0;
    }

    .index-list-item {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: var(--space-3);
      padding: var(--space-1) 0;
      border-bottom: 1px solid rgba(212, 208, 197, 0.4);
    }

    .index-list-item:last-child {
      border-bottom: none;
    }

    .index-concept-link,
    .index-tag-name {
      flex: 1;
    }

    .index-list-meta {
      font-family: var(--font-ui);
      font-size: 0.78rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--color-ink-muted);
      white-space: nowrap;
    }

    .index-top-concepts {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
    }

    .index-top-concepts li {
      padding: 0.15rem 0.55rem;
      border-radius: var(--radius-2);
      border: 1px solid var(--color-border-subtle);
      background: #f1f0ea;
      font-family: var(--font-ui);
      font-size: 0.78rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--color-ink-muted);
    }

    @media (max-width: 900px) {
      body {
        padding: var(--space-5) var(--space-3) var(--space-6);
      }

      header.site-header,
      .page-main {
        padding: 0 var(--space-1);
      }

      .concept-layout {
        grid-template-columns: minmax(0, 1fr);
      }

      .concept-meta {
        margin-bottom: var(--space-4);
        border-left: none;
        padding-left: 0;
      }

      .index-grid {
        grid-template-columns: minmax(0, 1fr);
      }
    }

    ::selection {
      background-color: #777;
      color: #eee;
    }

    a::selection {
      background-color: #ccc;
    }

    a[href^="https://"]:not([href*="emsenn.net"]):after,
    a[href^="https://"]:not([href*="emsenn.net"]):visited:after,
    .external-link:after,
    .visited-external-link:after {
      content: "^";
      font-size: 0.5em;
      vertical-align: super;
    }

    a[href^="https://"]:not([href*="emsenn.net"]),
    .external-link {
      color: var(--external-link-color);
    }

    a[href^="https://"]:not([href*="emsenn.net"]):hover,
    a[href^="https://"]:not([href*="emsenn.net"]):focus {
      color: var(--external-link-hover-color);
    }

    a[href^="https://"]:not([href*="emsenn.net"]):visited,
    .visited-external-link {
      color: var(--external-link-visited-color);
    }

    a[href^="https://"]:not([href*="emsenn.net"]):visited:hover,
    a[href^="https://"]:not([href*="emsenn.net"]):visited:focus {
      color: var(--external-link-visited-hover-color);
    }
  </style>
  <script>
    window.MathJax = {
      tex: {
        inlineMath: [['\\(', '\\)'], ['$', '$']],
        displayMath: [['\\[', '\\]'], ['$$', '$$']],
        processEscapes: true
      },
      options: {
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
      }
    };
  </script>
  <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
  <header class="site-header">
    <h1 class="site-title">{{ header }}</h1>
    <nav class="site-nav">
      <a href="{{ base_href }}/index.html">Index</a>
    </nav>
  </header>
  <main class="page-main">
    {% block content %}{% endblock %}
  </main>
</body>
</html>
"""

CONCEPT_TEMPLATE = """{% extends "base.html" %}
{% block content %}
<article class="concept-page{% if concept.status %} concept-page--status-{{ concept.status|slugify }}{% endif %}{% if is_draft %} concept-page--draft{% endif %}">
  <header class="concept-header">
    {% if concept.status %}
    <p class="concept-status-pill concept-status-pill--{{ concept.status|slugify }}">
      {{ concept.status|capitalize }}
    </p>
    {% endif %}
    <h2 class="concept-title">{{ concept.title }}</h2>
    <div class="concept-evaluation">
      <div class="evaluation-meter" aria-hidden="true"></div>
      <div class="evaluation-label meta">
        Semantic connectivity: {{ evaluation_label }}
      </div>
    </div>
  </header>
  <section class="concept-layout">
    <aside class="concept-meta" aria-label="Concept metadata">
      {% if concept.status %}
      <p class="meta-row">
        <span class="meta-label">Status</span>
        <span class="meta-value">{{ concept.status }}</span>
      </p>
      {% endif %}
      {% if concept.type %}
      <p class="meta-row">
        <span class="meta-label">Type</span>
        <span class="meta-value">{{ concept.type }}</span>
      </p>
      {% endif %}
      {% if concept.created %}
      <p class="meta-row">
        <span class="meta-label">Created</span>
        <span class="meta-value">{{ concept.created }}</span>
      </p>
      {% endif %}
      {% if concept.updated %}
      <p class="meta-row">
        <span class="meta-label">Updated</span>
        <span class="meta-value">{{ concept.updated }}</span>
      </p>
      {% endif %}
      {% if concept.aliases %}
      <p class="meta-row">
        <span class="meta-label">Aliases</span>
        <span class="meta-value">{{ concept.aliases|join(", ") }}</span>
      </p>
      {% endif %}
      {% if concept.tags %}
      <div class="meta-block">
        <div class="meta-label">Tags</div>
        <ul class="chip-list">
          {% for t in concept.tags %}
          <li class="chip">
            <a href="{{ base_href }}/tags/{{ t|slugify }}.html">{{ t }}</a>
          </li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}
    </aside>
    <div class="concept-body">
      <div class="body-html">
        {{ body_html | safe }}
      </div>
      {% if related %}
      <section class="related">
        <h3 class="related-heading">Related concepts</h3>
        <ol class="related-list">
          {% for rel in related %}
          <li class="related-item">
      <a href="{{ base_href }}/docs/{{ rel.id }}.html" class="related-link">{{ rel.title }}</a>
            <span class="related-score meta">score {{ "%.2f"|format(rel.score) }}</span>
          </li>
          {% endfor %}
        </ol>
      </section>
      {% endif %}
      <section class="math-details">
        <h3 class="index-section-title">Math details</h3>
        <p class="meta">
          Evaluation score is computed as:
          <code>score = #tags + 0.5·#links + 0.3·#facts + 0.1·#temporal_years</code>
        </p>
        <dl class="index-metrics">
          <div class="index-metric">
            <dt>Tags</dt>
            <dd>{{ evaluation.tags }}</dd>
          </div>
          <div class="index-metric">
            <dt>Links</dt>
            <dd>{{ evaluation.links }}</dd>
          </div>
          <div class="index-metric">
            <dt>Facts</dt>
            <dd>{{ evaluation.facts }}</dd>
          </div>
          <div class="index-metric">
            <dt>Temporal years</dt>
            <dd>{{ evaluation.temporal_years }}</dd>
          </div>
          <div class="index-metric">
            <dt>Score</dt>
            <dd>{{ "%.2f"|format(evaluation.score) }}</dd>
          </div>
        </dl>
        <p class="meta">
          Full data:
      <a href="{{ base_href }}/api/concepts/{{ concept.id }}.json">JSON</a>.
        </p>
      </section>
    </div>
  </section>
</article>
{% endblock %}
"""

INDEX_TEMPLATE = """{% extends "base.html" %}
{% block content %}
<section class="index-grid">
  <article class="index-card">
    <h2 class="index-card-title">Universe</h2>
    <dl class="index-metrics">
      <div class="index-metric">
        <dt>Concepts</dt>
        <dd>{{ summary.concepts }}</dd>
      </div>
      <div class="index-metric">
        <dt>Atoms</dt>
        <dd>{{ summary.atoms }}</dd>
      </div>
      <div class="index-metric">
        <dt>Facts</dt>
        <dd>{{ summary.facts }}</dd>
      </div>
      <div class="index-metric">
        <dt>Temporal markers</dt>
        <dd>{{ summary.temporal }}</dd>
      </div>
    </dl>
  </article>
</section>
<section class="index-section">
  <h2 class="index-section-title">Concepts</h2>
  <ul class="index-list index-concepts">
    {% for concept in concepts %}
    <li class="index-list-item">
      <a href="{{ base_href }}/docs/{{ concept.id }}.html" class="index-concept-link">{{ concept.title }}</a>
      <span class="index-list-meta">score {{ "%.2f"|format(concept.evaluation_score) }}</span>
    </li>
    {% endfor %}
  </ul>
</section>
{% if tag_index %}
<section class="index-section">
  <h2 class="index-section-title">Tags</h2>
  <ul class="index-list index-tags">
    {% for tag in tag_index %}
    <li class="index-list-item">
      <a href="{{ base_href }}/tags/{{ tag.slug }}.html" class="index-tag-name">{{ tag.name }}</a>
      <span class="index-list-meta">{{ tag.count }} concepts</span>
    </li>
    {% endfor %}
  </ul>
</section>
{% endif %}
{% endblock %}
"""

CONCEPT_INDEX_TEMPLATE = """{% extends "base.html" %}
{% block content %}
<section class="index-section">
  <h2 class="index-section-title">Concepts</h2>
  <ul class="index-list index-concepts">
    {% for concept in concepts %}
    <li class="index-list-item">
      <a href="{{ base_href }}/docs/{{ concept.id }}.html" class="index-concept-link">{{ concept.title }}</a>
      <span class="index-list-meta">score {{ "%.2f"|format(concept.evaluation_score) }}</span>
    </li>
    {% endfor %}
  </ul>
</section>
{% endblock %}
"""

TAG_LIST_TEMPLATE = """{% extends "base.html" %}
{% block content %}
<section class="index-section">
  <h2 class="index-section-title">Tags</h2>
  <ul class="index-list index-tags">
    {% for tag in tags %}
    <li class="index-list-item">
      <a href="{{ base_href }}/tags/{{ tag.slug }}.html" class="index-tag-name">{{ tag.name }}</a>
      <span class="index-list-meta">{{ tag.count }} concepts</span>
    </li>
    {% endfor %}
  </ul>
</section>
{% endblock %}
"""

TAG_DETAIL_TEMPLATE = """{% extends "base.html" %}
{% block content %}
<section class="index-section">
  <h2 class="index-section-title">{{ tag.name }}</h2>
  {% if tag.doc %}
  <article class="concept-page">
    <header class="concept-header">
      <h3 class="concept-title">{{ tag.doc.title }}</h3>
    </header>
    <div class="concept-body">
      <div class="body-html">
        {{ doc_body_html | safe }}
      </div>
    </div>
  </article>
  {% endif %}
  <p class="meta">
    {{ tag.count }} concept{% if tag.count != 1 %}s{% endif %}
    · connectivity {{ "%.2f"|format(tag.avg_score) }}
  </p>
  <ul class="index-list index-concepts">
    {% for concept in tag.concepts %}
    <li class="index-list-item">
      <a href="{{ base_href }}/docs/{{ concept.id }}.html" class="index-concept-link">{{ concept.title }}</a>
      <span class="index-list-meta">score {{ "%.2f"|format(concept.evaluation_score) }}</span>
    </li>
    {% endfor %}
  </ul>
</section>
{% endblock %}
"""


def render_markdown_to_html(text: str, base_href: str = "") -> str:
    """Render markdown to HTML using markdown-it, expanding [[wikilinks]]."""

    def _wikilink_repl(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        target_id = slugify(label)
        if base_href:
            href = f"{base_href}/docs/{target_id}.html"
        else:
            href = f"docs/{target_id}.html"
        return f"[{label}]({href})"

    expanded = WIKILINK_RE.sub(_wikilink_repl, text)
    return MARKDOWN.render(expanded)


def jaccard(a: FeatureSet, b: FeatureSet) -> float:
    """Compute Jaccard similarity for relatedness."""
    if not a and not b:
        return 0.0
    inter = len(set(a) & set(b))
    union = len(set(a) | set(b))
    return inter / union if union else 0.0


def related_concepts(universe: Universe, concept: Concept, limit: int = 5) -> List[Tuple[Concept, float]]:
    """Find related concepts via Jaccard on semantic features."""
    results: List[Tuple[Concept, float]] = []
    for other in universe.concepts.values():
        if other.id == concept.id:
            continue
        score = jaccard(concept.semantic, other.semantic)
        if score > 0:
            results.append((other, score))
    results.sort(key=lambda pair: pair[1], reverse=True)
    return results[:limit]


LINT_ATOM_KINDS: Tuple[str, ...] = ("tag", "folder", "status", "type")
LINT_CONCEPT_TYPES: Tuple[str, ...] = ("doc", "tag", "folder", "status", "type")


def build_atom_docs(universe: Universe) -> Dict[str, Dict[str, Concept]]:
    """Map (atom kind, value) → documentation concept, using concept.type as role."""
    docs: Dict[str, Dict[str, Concept]] = {kind: {} for kind in LINT_ATOM_KINDS}
    for concept in universe.concepts.values():
        kind = concept.type
        if kind in LINT_ATOM_KINDS:
            value = concept.id
            existing = docs[kind].get(value)
            if existing is not None:
                raise SystemExit(
                    f"[lint] Multiple docs for {kind}:{value}:\n"
                    f"  - {existing.path}\n"
                    f"  - {concept.path}"
                )
            docs[kind][value] = concept
    return docs


def _strip_inline_code(line: str) -> str:
    """Remove inline code spans delimited by backticks from a single line."""
    result_chars: List[str] = []
    in_code = False
    for ch in line:
        if ch == "`":
            in_code = not in_code
            continue
        if not in_code:
            result_chars.append(ch)
    return "".join(result_chars)


def lint_concept_math(concept: Concept) -> List[str]:
    """Lint for imbalanced TeX-style math delimiters in concept body."""
    issues: List[str] = []
    text = concept.body_markdown
    in_code_block = False
    paren_open = paren_close = 0
    bracket_open = bracket_close = 0
    unescaped_dollars = 0

    for raw_line in text.splitlines():
        stripped = raw_line.lstrip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        line = _strip_inline_code(raw_line)
        # Ignore escaped dollars used for literal currency.
        line_no_escaped = line.replace("\\$", "")
        paren_open += line_no_escaped.count("\\(")
        paren_close += line_no_escaped.count("\\)")
        bracket_open += line_no_escaped.count("\\[")
        bracket_close += line_no_escaped.count("\\]")
        # Count unescaped dollars; require them to appear in pairs.
        unescaped_dollars += line_no_escaped.count("$")

    if paren_open != paren_close:
        issues.append(
            f"[lint] {concept.id} ({concept.path}) has imbalanced inline math delimiters "
            f"\\( / \\): {paren_open} opening, {paren_close} closing."
        )
    if bracket_open != bracket_close:
        issues.append(
            f"[lint] {concept.id} ({concept.path}) has imbalanced display math delimiters "
            f"\\[ / \\]: {bracket_open} opening, {bracket_close} closing."
        )
    if unescaped_dollars % 2 != 0:
        issues.append(
            f"[lint] {concept.id} ({concept.path}) has an odd number of unescaped '$' characters; "
            "this may indicate malformed $...$ math."
        )

    return issues


def lint_concept_links(universe: Universe, concept: Concept) -> List[str]:
    """Lint for links that point at missing concept IDs."""
    issues: List[str] = []
    if not concept.links:
        return issues
    known_ids: Set[str] = set(universe.concepts.keys())
    missing = sorted({target for target in concept.links if target not in known_ids})
    for target in missing:
        issues.append(
            f"[lint] {concept.id} ({concept.path}) links to missing concept id '{target}'."
        )
    return issues


def lint_universe(universe: Universe) -> None:
    """Perform basic linting: require docs for frequently used atom kinds."""
    atom_docs = build_atom_docs(universe)
    issues: List[str] = []

    for kind in LINT_ATOM_KINDS:
        index = universe.indices.get(kind, {})
        doc_map = atom_docs.get(kind, {})
        for value, concept_ids in sorted(index.items(), key=lambda kv: kv[0]):
            # Restrict linting to concepts whose type we explicitly care about.
            relevant_ids = [
                cid
                for cid in concept_ids
                if cid in universe.concepts and universe.concepts[cid].type in LINT_CONCEPT_TYPES
            ]
            if not relevant_ids:
                continue
            if value not in doc_map:
                issues.append(
                    f"[lint] Missing doc for {kind}:{value} "
                    f"(used by {len(relevant_ids)} linted concept(s))"
                )

    # Lint math delimiters and internal links per concept.
    for concept in universe.concepts.values():
        issues.extend(lint_concept_math(concept))
        issues.extend(lint_concept_links(universe, concept))

    if issues:
        message = "[lint] Semiotic universe validation failed:\n" + "\n".join(issues)
        raise SystemExit(message)


def build_tag_items(universe: Universe) -> List[Dict[str, Any]]:
    """Assemble per-tag concept lists with evaluation-aware ordering."""
    tag_index = universe.indices.get("tag", {})
    atom_docs = build_atom_docs(universe)
    tag_docs = atom_docs.get("tag", {})
    items: List[Dict[str, Any]] = []
    for tag, concept_ids in tag_index.items():
        concepts_for_tag: List[Concept] = []
        for cid in concept_ids:
            if cid in universe.concepts:
                concepts_for_tag.append(universe.concepts[cid])
        # Sort concepts by evaluation score (descending), then title.
        concepts_for_tag.sort(key=lambda c: (-c.evaluation_score, c.title.lower()))
        count = len(concepts_for_tag)
        if concepts_for_tag:
            scores = [c.evaluation_score for c in concepts_for_tag]
            max_score = max(scores)
            min_score = min(scores)
            avg_score = sum(scores) / float(count)
        else:
            max_score = 0.0
            min_score = 0.0
            avg_score = 0.0
        items.append(
            {
                "name": tag,
                "slug": slugify(tag),
                "concepts": concepts_for_tag,
                "count": count,
                "max_score": max_score,
                "min_score": min_score,
                "avg_score": avg_score,
                "doc": tag_docs.get(tag),
            }
        )
    # Alphabetical by tag name for stable browsing.
    items.sort(key=lambda item: item["name"].lower())
    return items


def overview_summary(universe: Universe) -> Dict[str, Any]:
    """Assemble simple overview stats for the homepage."""
    tag_index = universe.indices.get("tag", {})
    folder_index = universe.indices.get("folder", {})
    fact_count = sum(1 for a in universe.atoms.values() if a.kind == "fact")
    temporal_atoms = sum(1 for a in universe.atoms.values() if a.kind in {"created_year", "updated_year"})
    all_tag_items = build_tag_items(universe)
    top_tags = sorted(all_tag_items, key=lambda item: item["count"], reverse=True)[:8]
    top_concepts = sorted(universe.concepts.values(), key=lambda c: c.evaluation_score, reverse=True)[:6]
    return {
        "concepts": len(universe.concepts),
        "atoms": len(universe.atoms),
        "tags": len(tag_index),
        "folders": len(folder_index),
        "facts": fact_count,
        "temporal": temporal_atoms,
        "top_tags": top_tags,
        "top_concepts": top_concepts,
    }


def export_html(
    universe: Universe,
    output_dir: Path,
    dry_run: bool = False,
    publish_statuses: Optional[List[str]] = None,
    draft_statuses: Optional[List[str]] = None,
) -> None:
    """Render HTML site (index + concept pages)."""
    site_dir = output_dir / "site"
    doc_dir = site_dir / "docs"
    tag_dir = site_dir / "tags"
    if not dry_run:
        doc_dir.mkdir(parents=True, exist_ok=True)
        tag_dir.mkdir(parents=True, exist_ok=True)
    env = Environment(
        loader=DictLoader(
            {
                "base.html": BASE_TEMPLATE,
                "concept.html": CONCEPT_TEMPLATE,
                "index.html": INDEX_TEMPLATE,
                "concept_index.html": CONCEPT_INDEX_TEMPLATE,
                "tag_list.html": TAG_LIST_TEMPLATE,
                "tag_detail.html": TAG_DETAIL_TEMPLATE,
            }
        ),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["slugify"] = slugify

    env.filters["slugify"] = slugify

    base_href = "."
    index_template = env.get_template("index.html")
    concept_template = env.get_template("concept.html")
    concept_index_template = env.get_template("concept_index.html")
    tag_list_template = env.get_template("tag_list.html")
    tag_detail_template = env.get_template("tag_detail.html")

    concepts = sorted(universe.concepts.values(), key=lambda c: c.title.lower())
    if publish_statuses:
        allowed = set(publish_statuses)
        concepts = [c for c in concepts if c.status in allowed]
    tag_items = build_tag_items(universe)
    summary = overview_summary(universe)

    index_html = index_template.render(
        title=universe.config.site_title,
        header=universe.config.site_title,
        site_title=universe.config.site_title,
        base_href=base_href,
        concepts=concepts,
        tag_index=tag_items,
        summary=summary,
    )
    if not dry_run:
        (site_dir / "index.html").write_text(index_html, encoding="utf-8")

    # Docs index for /site/docs/index.html
    concepts_index_html = concept_index_template.render(
        title=f"{universe.config.site_title} — Docs",
        header=universe.config.site_title,
        site_title=universe.config.site_title,
        base_href="..",
        concepts=concepts,
    )
    if not dry_run:
        (doc_dir / "index.html").write_text(concepts_index_html, encoding="utf-8")

    # Tag index for /site/tags/index.html
    tag_list_html = tag_list_template.render(
        title=f"{universe.config.site_title} — Tags",
        header=universe.config.site_title,
        site_title=universe.config.site_title,
        base_href="..",
        tags=tag_items,
    )
    if not dry_run:
        (tag_dir / "index.html").write_text(tag_list_html, encoding="utf-8")

    # Per-tag detail pages.
    for tag in tag_items:
        doc_body_html = None
        if tag.get("doc"):
            doc_body_html = render_markdown_to_html(tag["doc"].body_markdown, base_href="..")
        tag_html = tag_detail_template.render(
            title=f"{tag['name']} — {universe.config.site_title}",
            header=universe.config.site_title,
            site_title=universe.config.site_title,
            base_href="..",
            tag=tag,
            doc_body_html=doc_body_html,
        )
        if not dry_run:
            (tag_dir / f"{tag['slug']}.html").write_text(tag_html, encoding="utf-8")

    for concept in concepts:
        body_html = render_markdown_to_html(concept.body_markdown, base_href="..")
        eval_components = evaluation_components(universe, concept)
        eval_label = evaluation_label(eval_components["score"])
        is_draft = False
        if draft_statuses:
            is_draft = concept.status in set(draft_statuses)
        related = [{"id": c.id, "title": c.title, "score": score} for c, score in related_concepts(universe, concept)]
        html = concept_template.render(
            title=concept.title,
            header=universe.config.site_title,
            site_title=universe.config.site_title,
            base_href="..",
            concept=concept,
            body_html=body_html,
             evaluation=eval_components,
             evaluation_label=eval_label,
             is_draft=is_draft,
            related=related,
        )
        if not dry_run:
            (doc_dir / f"{concept.id}.html").write_text(html, encoding="utf-8")


def atoms_as_list(universe: Universe, features: FeatureSet) -> List[Dict[str, Any]]:
    """Render feature set atoms for JSON export."""
    items: List[Dict[str, Any]] = []
    for aid in features:
        atom = universe.atoms[aid]
        items.append({"id": atom.id, "kind": atom.kind, "value": atom.value})
    return sorted(items, key=lambda x: (x["kind"], x["value"]))


def export_json_api(
    universe: Universe,
    output_dir: Path,
    dry_run: bool = False,
    publish_statuses: Optional[List[str]] = None,
) -> None:
    """Emit static JSON API for concepts."""
    api_dir = output_dir / "api" / "concepts"
    if not dry_run:
        api_dir.mkdir(parents=True, exist_ok=True)
    index_payload: List[Dict[str, Any]] = []
    concepts = sorted(universe.concepts.values(), key=lambda c: c.id)
    if publish_statuses:
        allowed = set(publish_statuses)
        concepts = [c for c in concepts if c.status in allowed]
    for concept in concepts:
        payload = {
            "id": concept.id,
            "title": concept.title,
            "path": concept.path.as_posix(),
            "tags": concept.tags,
            "folders": concept.folders,
            "links": concept.links,
            "status": concept.status,
            "type": concept.type,
            "aliases": concept.aliases,
            "created": concept.created,
            "updated": concept.updated,
            "evaluation": concept.evaluation_score,
            "fragment_features": atoms_as_list(universe, concept.fragment),
            "semantic_features": atoms_as_list(universe, concept.semantic),
        }
        if not dry_run:
            (api_dir / f"{concept.id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        index_payload.append(
            {
                "id": concept.id,
                "title": concept.title,
                "tags": concept.tags,
                "folders": concept.folders,
                "status": concept.status,
                "type": concept.type,
                "evaluation": concept.evaluation_score,
            }
        )
    if not dry_run:
        index_path = api_dir / "index.json"
        index_path.write_text(json.dumps(index_payload, indent=2), encoding="utf-8")


def export_rdf(
    universe: Universe,
    output_dir: Path,
    dry_run: bool = False,
    publish_statuses: Optional[List[str]] = None,
) -> None:
    """Serialize universe as RDF (Turtle + optional JSON-LD)."""
    rdf_dir = output_dir / "rdf"
    if not dry_run:
        rdf_dir.mkdir(parents=True, exist_ok=True)
    graph = Graph()
    sem = Namespace("https://example.org/sem#")
    base = Namespace(universe.config.base_url)
    graph.bind("sem", sem)
    graph.bind("base", base)

    for atom in universe.atoms.values():
        atom_uri = base[f"atom/{atom.kind}/{slugify(atom.value)}"]
        graph.add((atom_uri, RDF.type, sem.Atom))
        graph.add((atom_uri, sem.kind, Literal(atom.kind)))
        graph.add((atom_uri, sem.value, Literal(atom.value)))

    concepts = list(universe.concepts.values())
    if publish_statuses:
        allowed = set(publish_statuses)
        concepts = [c for c in concepts if c.status in allowed]
    for concept in concepts:
        subject = base[f"concept/{concept.id}"]
        graph.add((subject, RDF.type, sem.Concept))
        graph.add((subject, sem.title, Literal(concept.title)))
        graph.add((subject, sem.evaluation, Literal(concept.evaluation_score, datatype=XSD.float)))
        for aid in concept.semantic:
            atom = universe.atoms[aid]
            atom_uri = base[f"atom/{atom.kind}/{slugify(atom.value)}"]
            graph.add((subject, sem.semanticFeature, atom_uri))

    if not dry_run:
        (rdf_dir / "graph.ttl").write_text(graph.serialize(format="turtle"), encoding="utf-8")
        try:
            (rdf_dir / "graph.jsonld").write_text(graph.serialize(format="json-ld"), encoding="utf-8")
        except Exception:
            pass


def openapi_schema_example(universe: Universe) -> Dict[str, Any]:
    """Build minimal OpenAPI schema matching the JSON API."""
    api_title = f"{universe.config.site_title} JSON API"
    return {
        "openapi": "3.1.0",
        "info": {"title": api_title, "version": "0.1.0"},
        "servers": [{"url": "."}],
        "paths": {
            "/api/concepts": {
                "get": {
                    "summary": "List concepts",
                    "responses": {
                        "200": {
                            "description": "Concept index",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "array", "items": {"$ref": "#/components/schemas/ConceptSummary"}}
                                }
                            },
                        }
                    },
                }
            },
            "/api/concepts/{id}": {
                "get": {
                    "summary": "Get concept",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {
                            "description": "Concept",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Concept"}}},
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "Atom": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}, "kind": {"type": "string"}, "value": {"type": "string"}},
                },
                "Concept": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "path": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "folders": {"type": "array", "items": {"type": "string"}},
                        "links": {"type": "array", "items": {"type": "string"}},
                        "status": {"type": ["string", "null"]},
                        "type": {"type": ["string", "null"]},
                        "aliases": {"type": "array", "items": {"type": "string"}},
                        "evaluation": {"type": "number"},
                        "fragment_features": {"type": "array", "items": {"$ref": "#/components/schemas/Atom"}},
                        "semantic_features": {"type": "array", "items": {"$ref": "#/components/schemas/Atom"}},
                    },
                },
                "ConceptSummary": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "folders": {"type": "array", "items": {"type": "string"}},
                        "status": {"type": ["string", "null"]},
                        "type": {"type": ["string", "null"]},
                        "evaluation": {"type": "number"},
                    },
                },
            }
        },
    }


def concept_to_pandoc_markdown(universe: Universe, concept: Concept) -> str:
    """Render a concept to markdown with YAML frontmatter and semantic appendix for pandoc."""
    yaml_content = None
    try:
        import yaml  # type: ignore

        meta = {
            "title": concept.title,
            "id": concept.id,
            "tags": concept.tags,
            "type": concept.type,
            "status": concept.status,
            "aliases": concept.aliases,
            "folders": concept.folders,
            "links": concept.links,
        }
        yaml_content = yaml.safe_dump(meta, sort_keys=False).strip()
    except Exception:
        pass
    header = f"---\n{yaml_content}\n---\n\n" if yaml_content else ""
    semantic_lines = "\n".join(
        f"- {universe.atoms[aid].kind}: {universe.atoms[aid].value}"
        for aid in sorted(concept.semantic, key=lambda x: (universe.atoms[x].kind, universe.atoms[x].value))
    )
    appendix = f"\n\n## Semantic features\n{semantic_lines}\n" if semantic_lines else ""
    return f"{header}{concept.body_markdown}{appendix}"


def export_pandoc(
    universe: Universe,
    output_dir: Path,
    dry_run: bool = False,
    allow_pandoc: bool = False,
    concept_id: Optional[str] = None,
) -> None:
    """Use pandoc to publish either a single concept or a combined document."""
    if not allow_pandoc or not universe.config.pandoc_enabled:
        print("[pandoc] Skipping (not enabled).")
        return
    formats = universe.config.pandoc_formats or ["pdf"]
    concepts: List[Concept]
    if concept_id:
        if concept_id not in universe.concepts:
            print(f"[pandoc] Concept {concept_id} not found; skipping.")
            return
        concepts = [universe.concepts[concept_id]]
    else:
        concepts = sorted(universe.concepts.values(), key=lambda c: c.title.lower())
    combined_md = "\n\n".join(concept_to_pandoc_markdown(universe, c) for c in concepts)
    pub_dir = output_dir / "pub"
    if not dry_run:
        pub_dir.mkdir(parents=True, exist_ok=True)
    for fmt in formats:
        output_name = (
            universe.config.pandoc_output_single
            if universe.config.pandoc_output_single
            else (concepts[0].id if concept_id else "book")
        )
        out_path = pub_dir / f"{output_name}.{fmt}"
        cmd = ["pandoc", "-f", "markdown", "-t", fmt]
        if universe.config.pandoc_template:
            cmd.extend(["--template", universe.config.pandoc_template])
        if universe.config.pandoc_filters:
            for flt in universe.config.pandoc_filters:
                cmd.extend(["--filter", flt])
        cmd.extend(["-o", str(out_path)])
        if dry_run:
            print(f"[pandoc] (dry-run) {' '.join(cmd)}")
            continue
        try:
            subprocess.run(cmd, input=combined_md.encode("utf-8"), check=True)
            print(f"[pandoc] wrote {out_path}")
        except FileNotFoundError:
            print("[pandoc] pandoc not installed or not in PATH; skipping.")
            return
        except subprocess.CalledProcessError as exc:
            print(f"[pandoc] pandoc failed: {exc}")


def export_openapi(
    universe: Universe,
    output_dir: Path,
    dry_run: bool = False,
    publish_statuses: Optional[List[str]] = None,
) -> None:
    """Write OpenAPI JSON describing the static API."""
    api_dir = output_dir / "api"
    if not dry_run:
        api_dir.mkdir(parents=True, exist_ok=True)
    schema = openapi_schema_example(universe)
    if not dry_run:
        (api_dir / "openapi.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")


def export_all(
    universe: Universe,
    output_dir: Path,
    targets: List[str],
    dry_run: bool = False,
    allow_pandoc: bool = False,
    concept_id: Optional[str] = None,
    publish_statuses: Optional[List[str]] = None,
    draft_statuses: Optional[List[str]] = None,
) -> None:
    """Run selected exporters."""
    if "html" in targets:
        export_html(universe, output_dir, dry_run=dry_run, publish_statuses=publish_statuses, draft_statuses=draft_statuses)
    if "json" in targets:
        export_json_api(universe, output_dir, dry_run=dry_run, publish_statuses=publish_statuses)
    if "rdf" in targets:
        export_rdf(universe, output_dir, dry_run=dry_run, publish_statuses=publish_statuses)
    if "openapi" in targets:
        export_openapi(universe, output_dir, dry_run=dry_run, publish_statuses=publish_statuses)
    if "pandoc" in targets:
        export_pandoc(universe, output_dir, dry_run=dry_run, allow_pandoc=allow_pandoc, concept_id=concept_id)


def default_targets_for_mode(mode: str) -> List[str]:
    if mode == "doc":
        return ["pandoc"]
    return ["html", "json", "rdf", "openapi"]


def normalize_targets(targets: Any) -> List[str]:
    if isinstance(targets, str):
        return [t.strip() for t in targets.split(",") if t.strip()]
    if isinstance(targets, list):
        return [str(t) for t in targets]
    return []


# ----------------------------
# CLI
# ----------------------------
def build_command(args: argparse.Namespace) -> None:
    config_path = Path(args.config).resolve() if args.config else None
    config = load_config(config_path)
    if args.mode:
        config.mode = args.mode

    vault_arg = args.vault_dir or config.vault_dir
    output_arg = args.output_dir or config.output_dir
    if not vault_arg or not output_arg:
        raise SystemExit("Vault and output directories must be provided via CLI or config.")

    vault_dir = Path(vault_arg).resolve()
    output_dir = Path(output_arg).resolve()

    targets = (
        normalize_targets(args.targets)
        if args.targets
        else (normalize_targets(config.targets) if config.targets else default_targets_for_mode(config.mode))
    )
    allow_pandoc = args.allow_pandoc
    concept_id = args.concept

    # Resolve publish/draft status filters.
    if getattr(args, "status", None):
        publish_statuses = [s.strip() for s in args.status.split(",") if s.strip()]
    else:
        publish_statuses = list(config.publish_statuses or [])
    if getattr(args, "draft_statuses", None):
        draft_statuses = [s.strip() for s in args.draft_statuses.split(",") if s.strip()]
    else:
        draft_statuses = list(config.draft_statuses or [])

    # Optionally clean output directory before building.
    if getattr(args, "clean", False):
        if args.dry_run:
            print(f"[{config.site_title}] --clean requested (dry run; not deleting {output_dir})")
        elif output_dir.exists():
            import shutil

            print(f"[{config.site_title}] Cleaning output directory {output_dir}")
            shutil.rmtree(output_dir)

    universe = build_universe(vault_dir, config, log=(lambda m: print(f"[phase] {m}")))
    print(f"[{config.site_title}] Loaded {len(universe.concepts)} concepts; {len(universe.atoms)} atoms.")

    # Lint the constructed universe before exporting artifacts.
    strict = bool(getattr(args, "strict", False) or config.lint_strict)
    try:
        lint_universe(universe)
    except SystemExit as exc:
        if strict:
            raise
        print(str(exc))

    if args.dry_run:
        print(f"[{config.site_title}] Dry run enabled; no files will be written.")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
    export_all(
        universe,
        output_dir,
        targets=targets,
        dry_run=args.dry_run,
        allow_pandoc=allow_pandoc,
        concept_id=concept_id,
        publish_statuses=publish_statuses,
        draft_statuses=draft_statuses,
    )
    print(
        f"[{config.site_title}] Exported targets {targets} to {output_dir}"
        f"{' (dry run, no files written)' if args.dry_run else ''}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Semiotic publisher")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("publish", help="Publish semiotic site or document")
    build_parser.add_argument("vault_dir", nargs="?", help="Path to markdown vault directory (or set in config)")
    build_parser.add_argument("output_dir", nargs="?", help="Directory for generated site/API (or set in config)")
    build_parser.add_argument("--config", help="Optional YAML config file", default=None)
    build_parser.add_argument("--dry-run", action="store_true", help="Run full pipeline without writing files")
    build_parser.add_argument("--targets", help="Comma-separated targets (html,json,rdf,openapi,pandoc)")
    build_parser.add_argument("--mode", help="Override mode (site or doc)")
    build_parser.add_argument("--allow-pandoc", action="store_true", help="Allow invoking pandoc if configured")
    build_parser.add_argument("--concept", help="Restrict to a single concept for pandoc export")
    build_parser.add_argument(
        "--status",
        help="Comma-separated statuses to publish (overrides publish_statuses in config)",
    )
    build_parser.add_argument(
        "--draft-statuses",
        help="Comma-separated statuses treated as drafts for styling (overrides draft_statuses in config)",
    )
    build_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat lint warnings as fatal and abort export",
    )
    build_parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete output directory before publishing (no-op in dry-run)",
    )
    # Backward compatibility alias
    build_parser_alias = subparsers.add_parser("build", help="Alias for publish")
    for arg in build_parser._actions[1:]:
        build_parser_alias._add_action(arg)
    args = parser.parse_args()

    if args.command in ("build", "publish"):
        build_command(args)


if __name__ == "__main__":
    # Deprecated: prefer `python -m src.cli` or `make publish`.
    from src.cli import main as cli_main

    cli_main()
