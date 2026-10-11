from __future__ import annotations

"""
Linting utilities.

These helpers validate the internal consistency of a semiotic universe:
missing atom docs, malformed math, and links to non‑existent concepts.
"""

from typing import Dict, List, Set, Tuple

from .model import Concept, Universe

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


__all__ = [
    "build_atom_docs",
    "lint_concept_math",
    "lint_concept_links",
    "lint_universe",
]

