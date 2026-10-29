#!/usr/bin/env python3
"""
Dependency-graph audit for the predication-categories corpus.

Complements tools/validate.py (which checks surface-level correctness — broken
refs, parse errors, orphans). This tool focuses on the dependency-graph
integrity risks that emerge as a corpus matures into hundreds of interlinked
notes:

  1. Cycle detection. Any cycle in the depends-on graph means the
     foundational layering has broken down.

  2. Status consistency. A theorem at status: proved must not depend on a
     theorem at status: draft or sketch. If it does, the "proved" claim is
     conditional on unproved work — usually a labeling honesty issue.

  3. Cross-ref vs depends-on consistency. If a theorem's proof body cites
     another note via [text](slug.md), that note should be in depends-on.
     Conversely, every entry in depends-on should be reachable somewhere in
     the body — orphan entries are usually leftover from refactors.

  4. Load-bearing ranking. The notes with the most descendants are the
     riskiest places for an error: a mistake there propagates farthest.
     Knowing the top 10 helps prioritise re-verification effort.

  5. Foundation-distance. Distance from atoms (notes with empty depends-on)
     to each note. Long chains compound proof-labelling errors.

Outputs:
  - tools/build/dependency-audit.md — human-readable report.
  - Exit code 0 if no critical issues, 1 if cycles or status inconsistencies
    are found.

Critical issues (exit 1):
  - Any cycle in the depends-on graph.
  - Any proved theorem depending on draft/sketch dependencies.

Soft warnings (exit 0):
  - Cross-ref / depends-on mismatches.
  - Especially load-bearing notes (top-10 ranking is informational).
  - Long foundation-to-leaf chains.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
LIB_DIRS = ["concepts", "objects", "morphisms", "theorems",
            "examples", "narratives", "questions", "references"]
OUT = ROOT / "tools" / "build"

FM_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
LINK_RE = re.compile(r"\[[^\]]+\]\((?:\.\./[a-z]+/)?([A-Za-z0-9\-]+)\.md(?:#[A-Za-z0-9\-]+)?\)")
SECTION_RE = re.compile(r"^(#{2,6})\s+(.+?)(?:\s*\{#[^}]+\})?\s*$", re.MULTILINE)

# Headings that introduce informational / forward-pointer sections (not load-
# bearing for proof dependencies). Matched as case-insensitive prefixes so
# "Position in Lineage 5" and "Position in the program" both match "position in".
INFORMATIONAL_HEADING_PATTERNS = [
    r"^position in\b",
    r"^connection(s)? to\b",
    r"^connection(s)? with\b",
    r"^connect(s|ion) to\b",
    r"^comparison with\b",
    r"^comparison to\b",
    r"^reading\b",
    r"^what this gives\b",
    r"^what this proves\b",
    r"^what is established\b",
    r"^what is settled\b",
    r"^what is proved\b",
    r"^what.s actually proved\b",
    r"^what.s open\b",
    r"^what.s still open\b",
    r"^what.s missing\b",
    r"^what.s left\b",
    r"^what is missing\b",
    r"^open question(s)?\b",
    r"^open work\b",
    r"^open(s)? to\b",
    r"^status remarks\b",
    r"^status by regime\b",
    r"^future direction(s)?\b",
    r"^downstream consequence(s)?\b",
    r"^downstream(\s|$)",
    r"^remark(s)?(\s|$)",
    r"^conjecture(s)?(\s|$)",
    r"^open conjecture(s)?\b",
    r"^higher.degree\b",
    r"^higher.cell\b",
    r"^higher dimension(s)?\b",
    r"^cosheaf-side\b",
    r"^cosheaf side\b",
    r"^refined classification\b",
    r"^refinement under\b",
    r"^why\b",  # "Why this might be true", "Why the conjecture is plausible"
    r"^non.degeneracy criterion\b",
    r"^application(s)?\b",
    r"^specialization to\b",
    r"^specialisation to\b",
    r"^when\b",  # "When does fuzziness collapse?"
    r"^a concrete positive case\b",
    r"^side observation\b",
    r"^reading\b",
    r"^cardinality boundary\b",
    r"^the boundary at\b",
]
INFORMATIONAL_HEADING_RE = re.compile("|".join(INFORMATIONAL_HEADING_PATTERNS), re.IGNORECASE)


def load_corpus() -> dict[str, dict]:
    """Parse frontmatter + body for every note. Returns {slug: note}."""
    notes: dict[str, dict] = {}
    for d in LIB_DIRS:
        for p in (ROOT / d).glob("*.md"):
            if p.name == "README.md":
                continue
            text = p.read_text()
            m = FM_RE.match(text)
            if not m:
                continue
            try:
                fm = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError:
                continue
            notes[p.stem] = {
                "slug": p.stem,
                "dir": d,
                "kind": fm.get("kind", d.rstrip("s")),
                "status": fm.get("status"),
                "depends_on": list(fm.get("depends-on") or []),
                "body": m.group(2),
                "path": p.relative_to(ROOT),
            }
    return notes


def detect_cycles(notes: dict[str, dict]) -> list[list[str]]:
    """Tarjan-style SCC detection. Returns the list of SCCs of size > 1.

    Plus any self-loop (a note that lists itself in depends-on).
    """
    cycles: list[list[str]] = []

    # Self-loops first.
    for slug, n in notes.items():
        if slug in n["depends_on"]:
            cycles.append([slug])

    # Iterative Tarjan SCC.
    index_counter = [0]
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    sccs: list[list[str]] = []

    def strong_connect(v: str) -> None:
        # Iterative DFS to avoid recursion depth limits on dense graphs.
        work = [(v, iter(notes[v]["depends_on"]) if v in notes else iter(()))]
        indices[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)

        while work:
            cur, succs = work[-1]
            advanced = False
            for w in succs:
                if w not in notes:
                    continue
                if w not in indices:
                    indices[w] = index_counter[0]
                    lowlink[w] = index_counter[0]
                    index_counter[0] += 1
                    stack.append(w)
                    on_stack.add(w)
                    work.append((w, iter(notes[w]["depends_on"])))
                    advanced = True
                    break
                elif w in on_stack:
                    lowlink[cur] = min(lowlink[cur], indices[w])
            if advanced:
                continue
            if lowlink[cur] == indices[cur]:
                comp: list[str] = []
                while True:
                    x = stack.pop()
                    on_stack.discard(x)
                    comp.append(x)
                    if x == cur:
                        break
                if len(comp) > 1:
                    sccs.append(comp)
            work.pop()
            if work:
                parent_cur, _ = work[-1]
                lowlink[parent_cur] = min(lowlink[parent_cur], lowlink[cur])

    for slug in notes:
        if slug not in indices:
            strong_connect(slug)

    cycles.extend(sccs)
    return cycles


def status_inconsistencies(notes: dict[str, dict]) -> list[tuple[str, str, str]]:
    """For each `proved` note, list any depends-on entries with status in
    {draft, sketch}. Returns list of (proved_slug, dep_slug, dep_status)."""
    issues: list[tuple[str, str, str]] = []
    for slug, n in notes.items():
        if n["status"] != "proved":
            continue
        for dep in n["depends_on"]:
            d = notes.get(dep)
            if d is None:
                continue
            if d["status"] in ("draft", "sketch", "wip"):
                issues.append((slug, dep, d["status"]))
    return issues


def split_into_sections(body: str) -> list[tuple[str, str]]:
    """Split a body into (heading, content) pairs by ## (or deeper) headings.

    The preamble before the first ## heading gets heading "" (empty).
    Sub-headings (### and below) keep their content attached to the parent
    section — they're rarely independent forward-pointers.
    """
    sections: list[tuple[str, str]] = []
    cursor = 0
    last_heading = ""
    for m in SECTION_RE.finditer(body):
        # Only split on top-level ## headings; deeper headings stay attached.
        if len(m.group(1)) != 2:
            continue
        chunk = body[cursor:m.start()]
        sections.append((last_heading, chunk))
        last_heading = m.group(2).strip()
        cursor = m.end()
    sections.append((last_heading, body[cursor:]))
    return sections


def is_informational_heading(heading: str) -> bool:
    """Return True if the heading marks an informational / forward-pointer
    section (Position in, What this gives, etc.) rather than load-bearing
    proof content (Statement, Proof, Setup, etc.)."""
    if not heading:
        return False  # preamble is load-bearing
    return bool(INFORMATIONAL_HEADING_RE.match(heading.strip()))


def load_bearing_links(body: str, self_slug: str) -> set[str]:
    """Extract slug references from sections that are *not* informational.

    Drops references in 'Position in', 'What this gives', etc., which are
    forward-pointers to downstream consequences rather than upstream proof
    dependencies. Also drops references inside the special "Position in
    Lineage X" sections used for example notes."""
    links: set[str] = set()
    for heading, content in split_into_sections(body):
        if is_informational_heading(heading):
            continue
        for m in LINK_RE.finditer(content):
            slug = m.group(1)
            if slug != self_slug:
                links.add(slug)
    return links


def all_body_links(body: str, self_slug: str) -> set[str]:
    """All slug references anywhere in the body (legacy aggressive heuristic)."""
    return {m for m in LINK_RE.findall(body) if m != self_slug}


def crossref_vs_depends_on(notes: dict[str, dict],
                           rev: dict[str, list[str]] | None = None,
                           section_filter: bool = True,
                           drop_descendants: bool = True,
                           drop_siblings: bool = True,
                           drop_kinds: tuple[str, ...] = ("narrative", "question"),
                           skip_citing_kinds: tuple[str, ...] = ("narrative", "question", "reference")) -> dict[str, dict]:
    """For each note, compare body links and depends-on.

    Filters (most-aggressive first):
      - section_filter: only count links in load-bearing sections.
      - drop_descendants: drop body→M where M is a transitive descendant
        of the current note (forward-pointers).
      - drop_siblings: classify body→M where M is in the descendant closure
        of any of N's direct deps (sibling / cousin / specialization
        references) into a separate bucket — these are typically "see also"
        cites, not missing dependencies.

    Returns per-note dict with buckets, in increasing concerning-ness:
      - "body_not_in_deps_ancestor": M is a transitive ancestor reachable
        via depends-on but not listed directly. Low priority.
      - "body_not_in_deps_sibling": M is a sibling/cousin (shares an ancestor
        with N via N's direct deps but is not on N's path). Medium priority —
        usually "see also" cites; occasionally a real missing dep.
      - "body_not_in_deps_unrelated": M is genuinely outside N's dependency
        neighborhood. Highest-priority signal — most likely a real missing
        dependency.
      - "deps_not_in_body": depends-on lists M but body never cites it.
    """
    out: dict[str, dict] = {}
    for slug, n in notes.items():
        if skip_citing_kinds and n["kind"] in skip_citing_kinds:
            continue  # narratives/questions/references aren't proof-load-bearing nodes
        if section_filter:
            body_links = load_bearing_links(n["body"], slug)
        else:
            body_links = all_body_links(n["body"], slug)
        body_links = {b for b in body_links if b in notes}
        # Drop body links to chapter-level positioning notes (narratives,
        # question files) — they're never load-bearing proof dependencies.
        if drop_kinds:
            body_links = {b for b in body_links if notes[b]["kind"] not in drop_kinds}
        deps = set(n["depends_on"]) & set(notes)

        ancestors = ancestors_set(slug, notes) if drop_descendants else set()
        descs = descendants_set(slug, rev) if (drop_descendants and rev is not None) else set()

        # Sibling closure: descendants of any direct dep, minus self & descendants of self.
        sibling_closure: set[str] = set()
        if drop_siblings and rev is not None:
            for d in deps:
                sibling_closure |= descendants_set(d, rev)
            sibling_closure.discard(slug)
            sibling_closure -= descs

        through_ancestor: list[str] = []
        sibling: list[str] = []
        unrelated: list[str] = []

        for m in body_links - deps:
            if drop_descendants and m in descs:
                continue  # forward-pointer, skip
            if m in ancestors:
                through_ancestor.append(m)
            elif drop_siblings and m in sibling_closure:
                sibling.append(m)
            else:
                unrelated.append(m)

        deps_not_in_body = sorted(deps - body_links)
        if unrelated or sibling or through_ancestor or deps_not_in_body:
            out[slug] = {
                "body_not_in_deps_unrelated": sorted(unrelated),
                "body_not_in_deps_sibling": sorted(sibling),
                "body_not_in_deps_ancestor": sorted(through_ancestor),
                "deps_not_in_body": deps_not_in_body,
                "body_not_in_deps": sorted(unrelated + sibling + through_ancestor),
            }
    return out


def reverse_graph(notes: dict[str, dict]) -> dict[str, list[str]]:
    """Returns {slug: [dependents]} — who depends on this note."""
    rev: dict[str, list[str]] = defaultdict(list)
    for slug, n in notes.items():
        for dep in n["depends_on"]:
            if dep in notes:
                rev[dep].append(slug)
    return dict(rev)


def descendant_count(notes: dict[str, dict], rev: dict[str, list[str]]) -> dict[str, int]:
    """For each note, count transitive descendants (notes reachable in the
    reverse graph). High count = load-bearing."""
    counts: dict[str, int] = {}
    for slug in notes:
        seen: set[str] = set()
        queue = deque([slug])
        while queue:
            cur = queue.popleft()
            for nxt in rev.get(cur, ()):
                if nxt in seen:
                    continue
                seen.add(nxt)
                queue.append(nxt)
        counts[slug] = len(seen)
    return counts


def descendants_set(slug: str, rev: dict[str, list[str]]) -> set[str]:
    """Transitive descendants of slug in the depends-on graph."""
    seen: set[str] = set()
    queue = deque([slug])
    while queue:
        cur = queue.popleft()
        for nxt in rev.get(cur, ()):
            if nxt in seen:
                continue
            seen.add(nxt)
            queue.append(nxt)
    return seen


def ancestors_set(slug: str, notes: dict[str, dict]) -> set[str]:
    """Transitive ancestors of slug in the depends-on graph."""
    seen: set[str] = set()
    queue = deque([slug])
    while queue:
        cur = queue.popleft()
        if cur not in notes:
            continue
        for prv in notes[cur]["depends_on"]:
            if prv in seen or prv not in notes:
                continue
            seen.add(prv)
            queue.append(prv)
    return seen


def foundation_distance(notes: dict[str, dict]) -> dict[str, int]:
    """For each note, longest path from a note with empty depends-on."""
    # Topological order via Kahn's algorithm; if cycles exist this will skip
    # the cyclic component, but we report cycles separately so that's OK.
    indeg: dict[str, int] = {slug: 0 for slug in notes}
    for slug, n in notes.items():
        for dep in n["depends_on"]:
            if dep in notes:
                indeg[slug] += 1

    queue = deque([s for s, d in indeg.items() if d == 0])
    dist: dict[str, int] = {s: 0 for s in queue}
    rev = reverse_graph(notes)

    while queue:
        cur = queue.popleft()
        for nxt in rev.get(cur, ()):
            cand = dist[cur] + 1
            if cand > dist.get(nxt, -1):
                dist[nxt] = cand
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)

    return dist


def find_proof_body(note: dict) -> str:
    """Return the substring of body starting from the first '## Proof' heading,
    or the whole body if none. This is what we'd ideally compare against
    depends-on, but for the audit we use the whole body to avoid false
    negatives on theorems whose proof references are scattered."""
    return note["body"]


def report(notes: dict[str, dict],
           cycles: list[list[str]],
           status_issues: list[tuple[str, str, str]],
           crossref: dict[str, dict],
           crossref_aggressive: dict[str, dict],
           descendants: dict[str, int],
           foundation: dict[str, int]) -> str:
    lines: list[str] = []
    lines.append("# Dependency-graph audit\n")
    lines.append(f"Notes scanned: **{len(notes)}**.")
    edges = sum(len([d for d in n["depends_on"] if d in notes]) for n in notes.values())
    lines.append(f"Dependency edges (resolved): **{edges}**.")
    lines.append("")

    # 1. Cycles
    lines.append(f"## 1. Cycles ({len(cycles)})\n")
    if not cycles:
        lines.append("*(none — depends-on graph is acyclic)*")
    else:
        for c in cycles:
            if len(c) == 1:
                lines.append(f"- self-loop: `{c[0]}`")
            else:
                lines.append(f"- SCC of size {len(c)}: " + ", ".join(f"`{s}`" for s in c))
    lines.append("")

    # 2. Status inconsistencies
    lines.append(f"## 2. Status inconsistencies ({len(status_issues)})\n")
    lines.append(
        "Proved theorems whose `depends-on` includes notes still at "
        "draft/sketch/wip status. These should either be upgraded, walked "
        "back, or marked explicitly conditional.\n"
    )
    if not status_issues:
        lines.append("*(none — no proved theorem depends on unproved work)*")
    else:
        by_proved: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for proved, dep, dep_status in status_issues:
            by_proved[proved].append((dep, dep_status))
        for proved, deps in sorted(by_proved.items()):
            lines.append(f"- `{proved}` depends on:")
            for dep, st in deps:
                lines.append(f"  - `{dep}` ({st})")
    lines.append("")

    # 3. Cross-ref vs depends-on (filtered: load-bearing + non-descendant + non-sibling)
    unrelated_pairs = sum(len(v["body_not_in_deps_unrelated"]) for v in crossref.values())
    sibling_pairs = sum(len(v["body_not_in_deps_sibling"]) for v in crossref.values())
    ancestor_pairs = sum(len(v["body_not_in_deps_ancestor"]) for v in crossref.values())
    deps_missing = sum(len(v["deps_not_in_body"]) for v in crossref.values())
    body_missing_aggressive = sum(len(v["body_not_in_deps"]) for v in crossref_aggressive.values())

    lines.append(f"## 3. Cross-ref vs depends-on consistency\n")
    lines.append(
        "Body links classified by their relation to the citing note's `depends-on`:\n"
        "- *direct*: in `depends-on` (good)\n"
        "- *descendant*: M's proof depends on N (forward-pointer, dropped)\n"
        "- *ancestor*: M is a transitive ancestor of N via `depends-on` (dependency implicit)\n"
        "- *sibling*: M is reachable from one of N's direct deps but is neither an ancestor nor descendant (a 'see also' relative)\n"
        "- *unrelated*: none of the above (highest-priority signal)\n"
    )
    lines.append(f"- **Unrelated body references**: **{unrelated_pairs} pairs** "
                 f"across {sum(1 for v in crossref.values() if v['body_not_in_deps_unrelated'])} notes. "
                 f"Most likely real missing dependencies or stray cross-references.")
    lines.append(f"- **Sibling body references**: **{sibling_pairs} pairs** "
                 f"across {sum(1 for v in crossref.values() if v['body_not_in_deps_sibling'])} notes. "
                 f"Mostly 'see also' / specialization cites — usually benign.")
    lines.append(f"- **Ancestor body references**: **{ancestor_pairs} pairs** "
                 f"across {sum(1 for v in crossref.values() if v['body_not_in_deps_ancestor'])} notes. "
                 f"Lower priority — transitive dependency is present.")
    lines.append(f"- `depends-on` lists a note but body never cites it: **{deps_missing} pairs** "
                 f"across {sum(1 for v in crossref.values() if v['deps_not_in_body'])} notes.\n")
    lines.append(f"*Filter context: {body_missing_aggressive} unfiltered → "
                 f"{unrelated_pairs} unrelated + {sibling_pairs} sibling + {ancestor_pairs} ancestor "
                 f"({body_missing_aggressive - unrelated_pairs - sibling_pairs - ancestor_pairs} pairs dropped as forward-pointers/informational).*\n")

    unrelated_notes = [(slug, v) for slug, v in crossref.items() if v["body_not_in_deps_unrelated"]]
    if unrelated_notes:
        unrelated_notes.sort(key=lambda x: (-descendants.get(x[0], 0), x[0]))
        lines.append("### Unrelated body references (highest priority)\n")
        lines.append("Body cites a note that's not in `depends-on`, not a descendant, not a "
                     "transitive ancestor, and not a sibling. Either the note IS a real "
                     "dependency that should be listed, OR it's an arbitrary cross-reference.\n")
        for slug, v in unrelated_notes[:50]:
            n = notes[slug]
            d = descendants.get(slug, 0)
            refs = ", ".join(f"`{r}`" for r in v["body_not_in_deps_unrelated"][:8])
            more = f" (+{len(v['body_not_in_deps_unrelated']) - 8} more)" if len(v["body_not_in_deps_unrelated"]) > 8 else ""
            lines.append(f"- `{slug}` (descendants={d}, kind={n['kind']}, status={n['status'] or '—'}): {refs}{more}")
        if len(unrelated_notes) > 50:
            lines.append(f"\n*(+ {len(unrelated_notes) - 50} more notes with unrelated body refs)*")
        lines.append("")

    # 4. Load-bearing ranking
    lines.append("## 4. Top 20 load-bearing notes (most descendants)\n")
    lines.append("These are the notes with the most transitive dependents — an error in any of them propagates farthest. Worth re-checking the proofs/definitions are tight.\n")
    top = sorted(descendants.items(), key=lambda x: -x[1])[:20]
    lines.append("| Rank | Note | Descendants | Kind | Status |")
    lines.append("|---:|---|---:|---|---|")
    for i, (slug, count) in enumerate(top, 1):
        n = notes[slug]
        st = n["status"] or "—"
        lines.append(f"| {i} | `{slug}` | {count} | {n['kind']} | {st} |")
    lines.append("")

    # 5. Foundation-distance distribution
    if foundation:
        max_dist = max(foundation.values())
        avg_dist = sum(foundation.values()) / len(foundation)
        lines.append(f"## 5. Foundation-distance\n")
        lines.append(f"Longest dependency chain from an atomic note (empty `depends-on`) to a leaf: **{max_dist}** edges.")
        lines.append(f"Average distance: **{avg_dist:.1f}** edges across {len(foundation)} notes.\n")
        far = sorted(foundation.items(), key=lambda x: -x[1])[:10]
        lines.append("### Top 10 deepest notes (longest distance from atoms)\n")
        lines.append("| Note | Distance |")
        lines.append("|---|---:|")
        for slug, d in far:
            lines.append(f"| `{slug}` | {d} |")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="only print the summary line")
    args = ap.parse_args()

    notes = load_corpus()
    cycles = detect_cycles(notes)
    status_issues = status_inconsistencies(notes)
    rev = reverse_graph(notes)
    descendants = descendant_count(notes, rev)
    foundation = foundation_distance(notes)
    crossref = crossref_vs_depends_on(notes, rev=rev, section_filter=True, drop_descendants=True, drop_siblings=True)
    crossref_aggressive = crossref_vs_depends_on(notes, rev=rev, section_filter=False, drop_descendants=False, drop_siblings=False)

    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / "dependency-audit.md"
    out_path.write_text(report(notes, cycles, status_issues, crossref, crossref_aggressive, descendants, foundation))

    unrelated_pairs = sum(len(v['body_not_in_deps_unrelated']) for v in crossref.values())
    sibling_pairs = sum(len(v['body_not_in_deps_sibling']) for v in crossref.values())
    ancestor_pairs = sum(len(v['body_not_in_deps_ancestor']) for v in crossref.values())
    unrelated_notes = sum(1 for v in crossref.values() if v['body_not_in_deps_unrelated'])
    body_missing_aggressive = sum(len(v['body_not_in_deps']) for v in crossref_aggressive.values())
    print(f"dependency-audit: {len(notes)} notes scanned")
    print(f"  cycles: {len(cycles)}")
    print(f"  status inconsistencies: {len(status_issues)}")
    print(f"  body refs not in deps:")
    print(f"    unrelated (highest signal): {unrelated_pairs} pairs across {unrelated_notes} notes")
    print(f"    sibling: {sibling_pairs} pairs (mostly 'see also' cites)")
    print(f"    ancestor: {ancestor_pairs} pairs (transitive deps)")
    print(f"    unfiltered total: {body_missing_aggressive} pairs")
    print(f"  report: tools/build/dependency-audit.md")

    return 1 if (cycles or status_issues) else 0


if __name__ == "__main__":
    sys.exit(main())
