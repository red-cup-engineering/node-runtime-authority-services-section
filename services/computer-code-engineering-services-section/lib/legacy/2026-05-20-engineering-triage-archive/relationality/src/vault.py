from __future__ import annotations

"""
Vault parsing and universe construction.

This module knows how to:
- read markdown files with YAML frontmatter,
- derive concepts and annotations from paths, tags, and subjects/facts,
- apply configuration to build j‑relations, and
- assemble a fully evaluated `Universe`.
"""

import fnmatch
import re
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from .model import AnnotationTerm, Concept, Config, Universe
from .semantics import (
    build_concept_fragment,
    build_concept_semantics,
    evaluate_concept,
    intern_atom,
    interpret_annotations,
)

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
        start: Optional[int] = None
        for idx, line in enumerate(lines):
            if line.strip() == "---":
                start = idx
                break
        if start is not None:
            fm_lines: List[str] = []
            end: Optional[int] = None
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


def build_universe_from_paths(
    paths: Iterable[Path],
    vault_root: Path,
    config: Config,
    log: Callable[[str], None] | None = None,
) -> Universe:
    """Build universe from an explicit set of markdown paths."""
    logger = log or (lambda msg: None)
    universe = Universe(config=config)

    logger("Collecting markdown concepts")
    for path in paths:
        concept = load_markdown_concept(path, vault_root)
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


def build_universe(vault_dir: Path, config: Config, log: Callable[[str], None] | None = None) -> Universe:
    """Build universe for an entire vault directory."""
    def iter_markdown() -> Iterable[Path]:
        for path in vault_dir.rglob("*.md"):
            rel = path.relative_to(vault_dir)
            rel_str = rel.as_posix()
            if any(fnmatch.fnmatch(rel_str, pattern) for pattern in config.ignore):
                continue
            return_path = path
            yield return_path

    return build_universe_from_paths(iter_markdown(), vault_dir, config, log)


def build_universe_for_file(
    file_path: Path,
    vault_root: Path,
    config: Config,
    log: Callable[[str], None] | None = None,
) -> Universe:
    """Build a universe containing only a single markdown file.

    This is useful for single‑file publishing flows while still
    applying the same semantic and evaluation machinery.
    """
    return build_universe_from_paths([file_path], vault_root, config, log)


__all__ = [
    "WIKILINK_RE",
    "MARKDOWN_LINK_RE",
    "load_markdown_with_frontmatter",
    "slugify",
    "extract_links",
    "collect_folders",
    "load_markdown_concept",
    "load_config",
    "configure_j_relations",
    "build_indices",
    "build_universe_from_paths",
    "build_universe",
    "build_universe_for_file",
]
