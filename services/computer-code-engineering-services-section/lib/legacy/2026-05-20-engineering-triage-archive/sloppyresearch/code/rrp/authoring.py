"""
Authoring utilities for RRPR papers.

These functions operationalize the thesis-centered workflow documented in
research/docs/RESEARCH_PAPER_PROCEDURE.md, helping agents scaffold new papers,
lint frontmatter/structure, and bootstrap drafts from research notes.

Interfaces are one-shot, composable, and kept thin per AGENTS.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import date

from .frontmatter_parser import (
    parse_markdown_file,
    FrontmatterParseError,
    FrontmatterValidationError,
)


TEMPLATE_PATH = Path("research/docs/templates/rrpr_paper_template.md")


@dataclass
class LintResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


def _read_template() -> str:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Template not found at {TEMPLATE_PATH}. Ensure docs are present."
        )
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def scaffold_paper(
    out_dir: Path,
    doc_id: str,
    title: str,
    *,
    status: str = "draft",
    document_type: str = "paper",
    authors: Optional[List[str]] = None,
    topics: Optional[List[str]] = None,
    disciplines: Optional[List[str]] = None,
) -> Path:
    """
    Create a new paper from the RRPR template with frontmatter populated.

    Returns the created file path.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{doc_id}.md"
    if target.exists():
        raise FileExistsError(f"Target already exists: {target}")

    template = _read_template()

    today = date.today().isoformat()
    fm_lines = [
        "+++",
        f"id = \"{doc_id}\"",
        f"title = \"{title}\"",
        f"status = \"{status}\"",
        f"document_type = \"{document_type}\"",
        f"date_created = \"{today}\"",
        f"date_modified = \"{today}\"",
    ]
    if authors:
        fm_lines.append("authors = [" + ", ".join(f"\"{a}\"" for a in authors) + "]")
    if topics:
        fm_lines.append("topics = [" + ", ".join(f"\"{t}\"" for t in topics) + "]")
    if disciplines:
        fm_lines.append(
            "disciplines = [" + ", ".join(f"\"{d}\"" for d in disciplines) + "]"
        )
    fm_lines.append("+++")

    content = "\n".join(fm_lines) + "\n\n" + template
    target.write_text(content, encoding="utf-8")
    return target


def lint_paper(path: Path) -> LintResult:
    """
    Validate TOML frontmatter and check for required structural sections.

    Structure checks are intentionally lightweight and encourage the thesis-centered
    workflow without being overly prescriptive.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not path.exists():
        return LintResult(False, [f"File not found: {path}"], [])

    text = path.read_text(encoding="utf-8")

    # Frontmatter validation
    try:
        meta, body = parse_markdown_file(path)
        if meta is None:
            errors.append("Missing TOML frontmatter delimited by +++ ... +++")
            body = text  # fall back
    except (FrontmatterParseError, FrontmatterValidationError) as e:
        errors.append(f"Frontmatter invalid: {e}")
        # try to still run body checks
        body = text

    # Section presence checks (coarse)
    lowered = body.lower()
    required_markers = [
        ("thesis", ["0. thesis", "thesis (centered)"]),
        ("foundations", ["foundations", "critical foundations", "domain foundations"]),
        ("synthesis", ["synthesis", "theory→model", "theory->model"]),
        ("lemma", ["lemma ", "lemmas", "proof."]),
        ("measurement", ["measurement", "appendix: measurement"]),
    ]

    for label, variants in required_markers:
        if not any(v in lowered for v in variants):
            warnings.append(f"Section likely missing or unmarked: {label}")

    # Gentle checks on tables/demonstrations
    if "|" not in body and "table" not in lowered:
        warnings.append("No obvious demonstration table found (consider a 6-row contrast)")

    ok = not errors
    return LintResult(ok, errors, warnings)


def draft_from_note(
    note_path: Path,
    out_dir: Path,
    doc_id: str,
    title: Optional[str] = None,
    *,
    include_source_as_appendix: bool = True,
) -> Tuple[Path, Optional[Path]]:
    """
    Turn a research note into a structured draft using the RRPR template.

    - Creates a new paper with basic frontmatter and placeholders
    - Optionally writes a sibling `.source.org` with verbatim note content

    Returns (paper_path, source_path or None).
    """
    if not note_path.exists():
        raise FileNotFoundError(f"Note not found: {note_path}")

    # Scaffold paper
    target = scaffold_paper(
        out_dir=out_dir,
        doc_id=doc_id,
        title=title or note_path.stem.replace("-", " ").title(),
        status="draft",
        document_type="draft",
    )

    # Append a provenance note and optional appendix hook
    content = target.read_text(encoding="utf-8")
    prov = [
        "\n\n---\n",
        "Note: This draft originates from a research note and follows the thesis-centered RRPR procedure.",
        f"Source note: {note_path.as_posix()}",
    ]
    if include_source_as_appendix:
        prov.append(
            "See sibling .source.org file for verbatim content (for traceability)."
        )
    target.write_text(content + "\n" + "\n".join(prov) + "\n", encoding="utf-8")

    source_written: Optional[Path] = None
    if include_source_as_appendix:
        source_written = target.with_suffix(".source.org")
        source_written.write_text(note_path.read_text(encoding="utf-8"), encoding="utf-8")

    return target, source_written
