#!/usr/bin/env python3
"""
Compose the predication-categories library into a single-file mathematical
monograph.

Model: a math monograph is a hierarchical document.
  - Chapter (H1): a major division, framed by a `position: chapter` narrative.
  - Inline content (H2): definitions, theorems, examples, lemmas, etc., each
    rendered as a kind-prefixed heading (e.g. "Definition: Pre-bilattice").
  - Connecting prose (H2): non-chapter narratives, rendered with their own
    H1 demoted to H2.

Pipeline:
  1. Parse YAML frontmatter from every note in the library.
  2. Topologically sort by `depends-on`.
  3. Place narratives by their positioning tags (introduces / recaps /
     discusses) and examples by `instantiates:`.
  4. Walk the order; emit chapter H1 when a `position: chapter` narrative is
     hit, and H2-headed content blocks for everything else.
  5. Pandoc-process the composed Markdown to expand `[@key]` citations
     against references.bib and append the bibliography. Output Markdown.

Output: tools/build/{manifest.txt, composed.md, book.md}.

Requires: pandoc on PATH.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LIB_DIRS = ["concepts", "objects", "morphisms", "theorems",
            "examples", "narratives", "questions", "references"]
OUT = ROOT / "tools" / "build"

FM_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
LINK_RE = re.compile(r"\[([^\]]+)\]\((?:\.\./[a-z]+/)?([A-Za-z0-9\-]+)\.md(#[A-Za-z0-9\-]+)?\)")
H1_RE = re.compile(r"^# (.+?)(?:\s*\{#[^}]+\})?\s*$", re.MULTILINE)


# ---------------------------------------------------------------- corpus IO

def parse_note(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    m = FM_RE.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    return fm, m.group(2)


def load_corpus() -> dict[str, dict]:
    notes: dict[str, dict] = {}
    for d in LIB_DIRS:
        for p in sorted((ROOT / d).glob("*.md")):
            if p.name == "README.md":
                continue
            slug = p.stem
            if slug in notes:
                raise RuntimeError(f"slug collision: {slug}")
            fm, body = parse_note(p)
            notes[slug] = {
                "slug": slug,
                "dir": d,
                "kind": fm.get("kind", d.rstrip("s")),
                "fm": fm,
                "body": body,
                "path": p,
            }
    return notes


# ----------------------------------------------------------------- ordering

def topo_sort(items: set[str], deps: dict[str, list[str]]) -> list[str]:
    """As-late-as-possible (just-in-time) topological sort.

    Each item is placed at the latest position consistent with the dep
    graph — immediately before its earliest dependent in the final order.
    A primitive used only by one theorem appears right before that theorem,
    not at the top of the book.

    Algorithm:
      1. Process items in reverse-topological order (items with no
         dependents first; iteratively, items whose all dependents
         have already been processed).
      2. Maintain a partial final order. For each processed item s, find
         the minimum position among s's dependents already in the order;
         insert s just before that position. If s has no placed dependents
         (a leaf with no users), append at the end.
    """
    dependents: dict[str, set[str]] = {s: set() for s in items}
    for s in items:
        for d in deps.get(s, []) or []:
            if d in dependents:
                dependents[d].add(s)

    # Kahn's on the reverse graph: in-degree(v) = number of v's dependents.
    # Start with v whose in-degree-in-reverse is 0 (no dependents at all).
    remaining_dependents = {s: set(dependents[s]) for s in items}
    queue = sorted(s for s in items if not remaining_dependents[s])
    process_order: list[str] = []
    while queue:
        # Take alphabetically smallest from the ready set
        s = queue.pop(0)
        process_order.append(s)
        for d in deps.get(s, []) or []:
            if d in remaining_dependents:
                remaining_dependents[d].discard(s)
                if not remaining_dependents[d]:
                    # All of d's dependents have been processed
                    # Insert d into queue alphabetically
                    import bisect
                    bisect.insort(queue, d)

    # Cycle handling: any item not in process_order forms a cycle. Append.
    for s in sorted(items):
        if s not in process_order:
            process_order.append(s)

    # Build final order by inserting each item at its latest valid position.
    final: list[str] = []
    pos: dict[str, int] = {}
    for s in process_order:
        # Find minimum position among s's dependents already placed
        min_dep_pos = None
        for u in dependents[s]:
            if u in pos and (min_dep_pos is None or pos[u] < min_dep_pos):
                min_dep_pos = pos[u]
        if min_dep_pos is None:
            final.append(s)
            pos[s] = len(final) - 1
        else:
            final.insert(min_dep_pos, s)
            # Shift positions of items at or after the insertion point
            for k, v in pos.items():
                if v >= min_dep_pos:
                    pos[k] = v + 1
            pos[s] = min_dep_pos

    return final


def order_corpus(notes: dict[str, dict]) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    # Primary content (definitions, theorems, concepts, examples) is topologically
    # ordered together. Narratives are placed afterward by their positioning
    # relations. Questions are pulled out of the spine entirely and rendered in
    # a dedicated appendix — they are inquiries, not load-bearing content.
    # Reference notes (kind: reference) likewise go to the Further reading
    # appendix; they are bibliographic resources, not content of the program.
    primary, narratives = [], []
    for slug, n in notes.items():
        if n["kind"] == "narrative":
            narratives.append(slug)
        elif n["kind"] in ("question", "reference"):
            continue
        else:
            primary.append(slug)

    deps = {s: (notes[s]["fm"].get("depends-on") or []) for s in notes}
    primary_set = set(primary)
    order = topo_sort(primary_set, deps)

    # Narratives: introduces (before first), recaps/discusses (after last)
    for narr in sorted(narratives):
        fm = notes[narr]["fm"]
        for role, key in (("introduces", "introduces"),
                          ("recaps", "recaps"),
                          ("discusses", "discusses")):
            targets = fm.get(key) or []
            in_order = [t for t in targets if t in order]
            if not in_order:
                continue
            if role == "introduces":
                idx = min(order.index(t) for t in in_order)
            else:
                idx = max(order.index(t) for t in in_order) + 1
            order.insert(idx, narr)
            break
        else:
            order.append(narr)

    return order, warnings


# ----------------------------------------------------------------- rendering

KIND_LABEL = {
    "concept": "Concept",
    "definition": "Definition",
    "morphism": "Definition",
    "theorem": "Theorem",
    "lemma": "Lemma",
    "proposition": "Proposition",
    "corollary": "Corollary",
    "example": "Example",
    "question": "Open problem",
    "conjecture": "Conjecture",
}


def rewrite_links(body: str, all_slugs: set[str]) -> str:
    def sub(m: re.Match) -> str:
        text, target, frag = m.group(1), m.group(2), m.group(3) or ""
        if target in all_slugs:
            return f"[{text}](#{target}{frag})"
        return m.group(0)
    return LINK_RE.sub(sub, body)


def extract_title_and_body(body: str) -> tuple[str, str]:
    """Strip the leading H1 from a note body. Return (title, remaining_body).
    Also strip H2 sections whose heading starts with "Lean" (e.g. "Lean
    coverage", "Lean mechanization scope") — Lean mechanization is internal
    bookkeeping and is excluded from the published book."""
    m = H1_RE.search(body)
    if not m:
        return "", strip_lean_sections(body).strip()
    title = m.group(1).strip()
    rest = body[: m.start()] + body[m.end():]
    return title, strip_lean_sections(rest).strip()


HEADING_RE = re.compile(r"^(#+)(?=\s)", re.MULTILINE)

LEAN_SECTION_RE = re.compile(
    r"^## +Lean\b.*?(?=^#{1,2} |\Z)",
    re.MULTILINE | re.DOTALL,
)


def strip_lean_sections(body: str) -> str:
    """Remove H2 sections whose heading starts with "Lean" (e.g. "Lean
    coverage", "Lean mechanization scope"). Lean mechanization is internal
    bookkeeping and shouldn't surface in the published book."""
    return LEAN_SECTION_RE.sub("", body).rstrip() + "\n"


def demote_headings(body: str, by: int) -> str:
    """Increase every heading's level by `by`. A note's title is rendered at
    some level X; its body's internal headings — `## Proof`, `## Remark`, etc.
    — must be deeper than X to read as subsections of the note rather than
    siblings of its containing chapter or part."""
    if by <= 0:
        return body
    return HEADING_RE.sub(lambda m: "#" * (len(m.group(1)) + by), body)


def chapter_anchors(notes: dict[str, dict]) -> set[str]:
    """A chapter anchor is the target of a `closes:` edge."""
    anchors = set()
    for n in notes.values():
        target = n["fm"].get("closes")
        if target and target in notes:
            anchors.add(target)
    return anchors


def transitive_deps(slug: str, notes: dict[str, dict]) -> set[str]:
    seen: set[str] = set()
    stack = list(notes[slug]["fm"].get("depends-on") or [])
    while stack:
        d = stack.pop()
        if d in seen or d not in notes:
            continue
        seen.add(d)
        stack.extend(notes[d]["fm"].get("depends-on") or [])
    return seen


def part_assignments(notes: dict[str, dict]) -> tuple[dict[str, int], list[str]]:
    """Each part-narrative declares its chapters via `chapters: [...]`.
    Returns (chapter_slug → part_number, list of part-narrative slugs in book order).
    """
    part_narratives = []
    chapter_to_part: dict[str, int] = {}
    for slug, n in notes.items():
        if n["kind"] != "narrative":
            continue
        chapters = n["fm"].get("chapters") or []
        if chapters:
            part_narratives.append(slug)
    # Order part-narratives by 1, 2, … from their slugs (e.g. "part-1-…", "part-2-…")
    part_narratives.sort(key=lambda s: int(re.search(r"part-(\d+)", s).group(1)) if re.search(r"part-(\d+)", s) else 999)
    for slug in part_narratives:
        m = re.search(r"part-(\d+)", slug)
        part_num = int(m.group(1)) if m else 0
        for ch in notes[slug]["fm"].get("chapters") or []:
            chapter_to_part[ch] = part_num
    return chapter_to_part, part_narratives


def render_preface(narr: dict, all_slugs: set[str]) -> str:
    """Preface section narrative: H2 (title is the document H1, set via
    pandoc YAML metadata). Demote body subsections by 1 (## → ###)."""
    title, rest = extract_title_and_body(narr["body"])
    rest = demote_headings(rest, 1)
    rest = rewrite_links(rest, all_slugs)
    return f"## {title} {{#{narr['slug']}}}\n\n{rest}\n"


def render_part(narr: dict, all_slugs: set[str]) -> str:
    """Top section narrative (Derivation, Study and use): H2. Demote body
    subsections by 1 (## → ###) so they read as siblings of chapters."""
    title, rest = extract_title_and_body(narr["body"])
    rest = demote_headings(rest, 1)
    rest = rewrite_links(rest, all_slugs)
    return f"## {title} {{#{narr['slug']}}}\n\n{rest}\n"


def render_chapter(narr: dict, all_slugs: set[str]) -> str:
    """Chapter narrative: H3 inside a top section. Demote body subsections
    by 2 (## → ####) so they read as subsections of the chapter, peer to
    note blocks at H4."""
    title, rest = extract_title_and_body(narr["body"])
    rest = demote_headings(rest, 2)
    rest = rewrite_links(rest, all_slugs)
    return f"### {title} {{#{narr['slug']}}}\n\n{rest}\n"


def render_question(note: dict, all_slugs: set[str]) -> str:
    """Question appendix entry: H4 inside the Open questions H3 inside
    Supplements H2. Body demoted by 3 (## → #####)."""
    title, rest = extract_title_and_body(note["body"])
    rest = demote_headings(rest, 3)
    rest = rewrite_links(rest, all_slugs)
    label = KIND_LABEL["question"]
    status = note["fm"].get("status", "open")
    badge = f" [{status.upper()}]" if status != "open" else ""
    explores = note["fm"].get("explores") or []
    explores_links = ", ".join(f"[{e}](#{e})" for e in explores if e in all_slugs)
    explores_line = f"*Explores: {explores_links}*\n\n" if explores_links else ""
    heading = f"#### {label}{badge}: {title} {{#{note['slug']}}}"
    return f"{heading}\n\n{explores_line}{rest}\n"


CITE_RE = re.compile(r"\[@([a-z][a-z0-9-]*\d{4}[a-z]?)\]")


def render_appendix_further_reading(notes: dict[str, dict], all_slugs: set[str]) -> str:
    """Further reading appendix: reference notes that aren't directly cited
    via [@key] in the body. Each is rendered with its annotation as an H3
    block under an H1. The cited works appear in the auto-generated
    References section produced by citeproc — Further reading lists works
    that situate the program but aren't load-bearing on a specific claim."""
    cited: set[str] = set()
    for s, n in notes.items():
        if n["dir"] == "references":
            continue
        cited.update(CITE_RE.findall(n["body"]))
    refs = [(s, n) for s, n in sorted(notes.items())
            if n["dir"] == "references" and s not in cited]
    if not refs:
        return ""
    parts = ["### Further reading {#appendix-further-reading}", ""]
    parts.append(
        "Works in the program's intellectual environment that situate the "
        "machinery but aren't directly cited on any specific claim. Each "
        "entry summarises the work and its relevance.\n"
    )
    for s, n in refs:
        title, rest = extract_title_and_body(n["body"])
        rest = demote_headings(rest, 3)
        rest = rewrite_links(rest, all_slugs)
        fm = n["fm"]
        authors = fm.get("authors") or []
        year = fm.get("year") or ""
        ref_title = fm.get("title") or title or s
        if isinstance(authors, list) and authors:
            author_str = ", ".join(authors)
            display = f"{author_str} ({year}) — *{ref_title}*" if year else f"{author_str} — *{ref_title}*"
        else:
            display = title or s
        parts.append(f"#### {display} {{#{s}}}")
        parts.append("")
        parts.append(rest)
        parts.append("")
    return "\n".join(parts)


def render_appendix_questions(notes: dict[str, dict], all_slugs: set[str]) -> str:
    """Open-questions appendix: H3 inside Supplements H2, then each question as
    an H4 entry."""
    questions = sorted(s for s, n in notes.items() if n["kind"] == "question"
                       and s.lower() != "readme"
                       and n["fm"].get("status") in (None, "open", "partial"))
    if not questions:
        return ""
    parts = ["### Open questions {#appendix-open-questions}", ""]
    parts.append(
        "Open mathematical and program-shaping questions, indexed by the "
        "entities they explore. Each question's `explores:` list points to "
        "the objects, concepts, or theorems that situate the inquiry.\n"
    )
    for s in questions:
        parts.append(render_question(notes[s], all_slugs))
        parts.append("")
    return "\n".join(parts)


def render_block(note: dict, all_slugs: set[str]) -> str:
    """Content block: H4 with kind-prefixed title + anchor (H4 because chapters
    sit at H3 under top sections at H2). Theorems/conjectures with non-`proved`
    status get a status badge. Body's internal `## …` headings demote by 3
    (## Proof → ##### Proof) so they read as subsections of the block."""
    title, rest = extract_title_and_body(note["body"])
    rest = demote_headings(rest, 3)
    rest = rewrite_links(rest, all_slugs)
    label = KIND_LABEL.get(note["kind"], note["kind"].capitalize())
    badge = ""
    status = note["fm"].get("status")
    if note["kind"] in ("theorem", "lemma", "proposition", "corollary",
                       "conjecture") and status and status != "proved":
        badge = f" [{status.upper()}]"
    if note["kind"] == "narrative":
        heading = f"#### {title} {{#{note['slug']}}}"
    else:
        heading = f"#### {label}{badge}: {title} {{#{note['slug']}}}"
    return f"{heading}\n\n{rest}\n"


def build_composed(order: list[str], notes: dict[str, dict]) -> str:
    """Assign each note to a chapter by its transitive dep relationship to
    chapter anchors, then emit by Part > chapter, preserving topo order
    within each chapter.

    Each chapter narrative declares (via `introduces:`) one anchor object.
    A non-narrative note belongs to the LATEST chapter (in the part-narrative
    declared order) whose anchor it transitively depends on. Notes with no
    chapter anchor in their deps are preliminaries — emitted before Part 1.

    Hierarchy: H1 = Part, H2 = chapter, H3 = inline content.
    """
    all_slugs = set(notes.keys())
    anchors_set = chapter_anchors(notes)
    chapter_to_part, part_narrative_slugs = part_assignments(notes)
    part_num_to_narrative = {}
    for slug in part_narrative_slugs:
        m = re.search(r"part-(\d+)", slug)
        if m:
            part_num_to_narrative[int(m.group(1))] = slug

    # Anchor → chapter narrative slug mapping, and chapter ordering by part declaration.
    # The chapters: list on the part-narrative gives the canonical ordering.
    chapter_order: list[str] = []  # narrative slugs, in declared order
    for pn_slug in sorted(part_num_to_narrative.values(),
                          key=lambda s: int(re.search(r"part-(\d+)", s).group(1))):
        for ch in notes[pn_slug]["fm"].get("chapters") or []:
            chapter_order.append(ch)
    chapter_rank = {s: i for i, s in enumerate(chapter_order)}

    # Each chapter narrative declares its scope via `introduces:`. Definitions,
    # concepts, and morphisms in that list are chapter anchors — structural
    # objects the chapter is about, used to attribute downstream slugs. Theorems
    # in the introduces list are kept for narrative positioning (the narrative
    # is placed before the first introduced item) but are NOT treated as
    # anchors: a theorem is a statement ABOUT structural objects, not an object
    # itself, and using theorems as anchors over-attributes their dependencies
    # to the theorem's chapter.
    _anchor_kinds = {"definition", "concept", "morphism"}
    anchor_to_chapter: dict[str, str] = {}
    for ch in chapter_order:
        for t in (notes[ch]["fm"].get("introduces") or []):
            if t in notes and t not in anchor_to_chapter \
                    and notes[t]["kind"] in _anchor_kinds:
                anchor_to_chapter[t] = ch
    chapter_intros: set[str] = set(anchor_to_chapter.keys())

    # Cache of transitive deps
    tdeps_cache: dict[str, set[str]] = {}
    def tdeps(s: str) -> set[str]:
        if s not in tdeps_cache:
            tdeps_cache[s] = transitive_deps(s, notes)
        return tdeps_cache[s]

    # Pre-compute transitive deps of each chapter-introduced anchor.
    anchor_tdeps = {a: tdeps(a) for a in chapter_intros}

    # Reverse dep graph for downstream-recursion fallback
    dependents: dict[str, set[str]] = {s: set() for s in notes}
    for s in notes:
        for d in (notes[s]["fm"].get("depends-on") or []):
            if d in dependents:
                dependents[d].add(s)

    chapter_cache: dict[str, str | None] = {}

    def assign_chapter(slug: str, _stack: tuple[str, ...] = ()) -> str | None:
        if slug in chapter_cache:
            return chapter_cache[slug]
        if slug in _stack:
            return None
        if slug in chapter_rank:
            chapter_cache[slug] = slug
            return slug
        if slug in anchor_to_chapter:
            chapter_cache[slug] = anchor_to_chapter[slug]
            return anchor_to_chapter[slug]

        n = notes[slug]
        # If slug is itself a closer (its `closes:` target is an anchor), it
        # belongs in that target's chapter — slug is the closure proof for X,
        # so it's part of X's chapter.
        closes_target = n["fm"].get("closes")
        if closes_target in anchor_to_chapter:
            ch = anchor_to_chapter[closes_target]
            chapter_cache[slug] = ch
            return ch

        if n["kind"] == "narrative":
            for key in ("introduces", "recaps", "discusses"):
                targets = n["fm"].get(key) or []
                tc = [assign_chapter(t, _stack + (slug,)) for t in targets if t in notes]
                tc = [c for c in tc if c is not None]
                if tc:
                    pick = (min if key == "introduces" else max)(
                        tc, key=lambda c: chapter_rank.get(c, len(chapter_rank) if key == "introduces" else -1)
                    )
                    chapter_cache[slug] = pick
                    return pick
            chapter_cache[slug] = None
            return None

        # Upstream rule (preferred): chapter-introduced anchors whose transitive
        # deps include slug — i.e., anchors that USE slug. The earliest such
        # anchor is the "first user" of slug in book order; slug is introduced
        # just-in-time as a preliminary for that anchor's chapter.
        used_by = [a for a in chapter_intros if slug in anchor_tdeps[a]]
        if used_by:
            ch = min((anchor_to_chapter[a] for a in used_by),
                     key=lambda c: chapter_rank.get(c, len(chapter_rank)))
            chapter_cache[slug] = ch
            return ch
        # Downstream rule: chapter-introduced anchors in slug's transitive deps.
        # Pick the CLOSEST anchor (BFS distance via deps); on tie, the LATEST
        # chapter — slug is conceptually attributable to the latest structure
        # it builds on, since that's the chapter whose machinery it consumes.
        # (Earlier this used "earliest chapter" tie-break, which pulled too much
        # content into Ch1 by ties through deeply-shared early structure.)
        uses = [a for a in tdeps(slug) if a in anchor_to_chapter]
        if uses:
            dist: dict[str, int] = {slug: 0}
            queue = [slug]
            while queue:
                next_q = []
                for s in queue:
                    for d in (notes[s]["fm"].get("depends-on") or []):
                        if d in notes and d not in dist:
                            dist[d] = dist[s] + 1
                            next_q.append(d)
                queue = next_q
            anchor_dist = {a: dist[a] for a in uses if a in dist}
            min_d = min(anchor_dist.values())
            closest = [a for a, d in anchor_dist.items() if d == min_d]
            ch = max((anchor_to_chapter[a] for a in closest),
                     key=lambda c: chapter_rank.get(c, -1))
            chapter_cache[slug] = ch
            return ch
        # Fallback 1: recurse via deps
        for d in (n["fm"].get("depends-on") or []):
            if d in notes:
                ch = assign_chapter(d, _stack + (slug,))
                if ch is not None:
                    chapter_cache[slug] = ch
                    return ch
        # Fallback 2: recurse via dependents (slug is upstream of them — earliest wins)
        dep_chapters = []
        for d in dependents.get(slug, ()):
            ch = assign_chapter(d, _stack + (slug,))
            if ch is not None:
                dep_chapters.append(ch)
        if dep_chapters:
            ch = min(dep_chapters, key=lambda c: chapter_rank.get(c, len(chapter_rank)))
            chapter_cache[slug] = ch
            return ch
        chapter_cache[slug] = None
        return None

    # Group notes by chapter, preserving topo order
    skip_slugs = set(part_narrative_slugs)
    chapter_content: dict[str | None, list[str]] = {None: []}
    for ch in chapter_order:
        chapter_content[ch] = []
    for s in order:
        if s in skip_slugs:
            continue
        if s in chapter_rank:
            # chapter narrative — handled separately at chapter emission
            continue
        ch = assign_chapter(s)
        chapter_content.setdefault(ch, []).append(s)

    parts = [
        "---",
        "title: Spatiotemporal Knowledge",
        "subtitle: A monograph on bilattice hyperdoctrines, cascade cohomology, and moduli",
        "bibliography: ../../references.bib",
        "link-citations: true",
        "reference-section-title: References",
        "reference-section-level: 3",
        "---",
        "",
    ]

    # Preliminaries: notes with no chapter assignment. Narratives in this
    # bucket are positionless overviews — render as Preface H1. Other notes
    # are foundational content used across the book — render as H3 blocks.
    for s in chapter_content.get(None, []):
        if notes[s]["kind"] == "narrative":
            parts.append(render_preface(notes[s], all_slugs))
        else:
            parts.append(render_block(notes[s], all_slugs))
        parts.append("")

    # Each Part, then its chapters in declared order
    for part_num in sorted(part_num_to_narrative):
        pn_slug = part_num_to_narrative[part_num]
        parts.append(render_part(notes[pn_slug], all_slugs))
        parts.append("")
        for ch in notes[pn_slug]["fm"].get("chapters") or []:
            parts.append(render_chapter(notes[ch], all_slugs))
            parts.append("")
            for s in chapter_content.get(ch, []):
                parts.append(render_block(notes[s], all_slugs))
                parts.append("")

    # Supplements section (H2): wraps Open questions, Further reading, and
    # the auto-generated References (citeproc renders `### References` at the
    # end of the document because reference-section-level is 3, and the body
    # has no further H2 after Supplements).
    appendix = render_appendix_questions(notes, all_slugs)
    further = render_appendix_further_reading(notes, all_slugs)
    if appendix or further:
        parts.append("## Supplements {#supplements}")
        parts.append("")
    if appendix:
        parts.append(appendix)
        parts.append("")
    if further:
        parts.append(further)
        parts.append("")

    return "\n".join(parts)


# ------------------------------------------------------------------- pandoc

def run_pandoc(composed: Path, book: Path) -> None:
    """Use commonmark_x output so citeproc expands [@key] citations and
    emits the bibliography section. Pandoc-flavored markdown round-trips
    citations as-is, which is not what we want for a publication."""
    cmd = [
        "pandoc", str(composed),
        # Disable auto-id generation on both input and output so internal
        # block headings ("Proof", "Remark", a body's "Closure ordinal"
        # sub-section, etc.) don't auto-slugify into the same identifier as
        # a real anchored note — which would shadow the explicit `{#slug}`
        # anchor of the canonical definition. Explicit `{#anchor}` still works.
        "--from", "markdown-auto_identifiers",
        "--to", "commonmark_x-gfm_auto_identifiers",
        "--citeproc",
        "--bibliography", str(ROOT / "references.bib"),
        "--wrap=preserve",
        "-o", str(book),
    ]
    subprocess.run(cmd, check=True)
    # Pandoc 3.1 doesn't honor `reference-section-level` — citeproc emits the
    # bibliography heading at H1 regardless. Demote it to H3 so it nests inside
    # the Supplements H2 (sibling of Open questions and Further reading).
    text = book.read_text()
    text = text.replace(
        "# References {#bibliography .unnumbered}",
        "### References {#bibliography .unnumbered}",
    )
    book.write_text(text)


# --------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnose", action="store_true",
                    help="print the linear order with chapter boundaries marked")
    ap.add_argument("--no-lean", action="store_true",
                    help="skip Lean proof validation in the validator pre-step")
    args = ap.parse_args()

    if subprocess.run(["which", "pandoc"], capture_output=True).returncode != 0:
        print("error: pandoc not found on PATH. Install with: sudo apt install pandoc",
              file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)

    # Run validator first; refuse to build if it returns non-zero (hard failures
    # like broken cross-references or Lean proof failures).
    validator = ROOT / "tools" / "validate.py"
    if validator.exists():
        print("--- validating corpus ---")
        validator_cmd = [sys.executable, str(validator)]
        if args.no_lean:
            validator_cmd.append("--no-lean")
        v = subprocess.run(validator_cmd)
        if v.returncode != 0:
            print("\nbuild aborted: see tools/build/wip-report.md for issues",
                  file=sys.stderr)
            return 1
    print("--- composing book ---")

    notes = load_corpus()
    order, warnings = order_corpus(notes)

    # Manifest with chapter markers
    manifest_lines = []
    for s in order:
        n = notes[s]
        marker = " "
        if n["kind"] == "narrative" and n["fm"].get("position") == "chapter":
            marker = "C"
        manifest_lines.append(f"{marker} {n['dir']}/{s}\t{n['kind']}")
    (OUT / "manifest.txt").write_text("\n".join(manifest_lines) + "\n")

    composed = build_composed(order, notes)
    (OUT / "composed.md").write_text(composed)

    print(f"manifest:    {OUT/'manifest.txt'}  ({len(order)} entries)")
    print(f"composed.md: {OUT/'composed.md'}  ({len(composed):,} chars)")

    if args.diagnose:
        print()
        print("ORDER (C = chapter):")
        for line in manifest_lines:
            print("  " + line)

    run_pandoc(OUT / "composed.md", OUT / "book.md")
    print(f"book.md:     {OUT/'book.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
