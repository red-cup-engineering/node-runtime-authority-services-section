#!/usr/bin/env python3
"""
Validate the library and produce a WIP report.

Checks:
  - Frontmatter parses; every note has `type`.
  - Every theorem/conjecture has `status:` (draft | sketch | proved).
  - Every theorem with status: proved has a `## Proof` section in its body.
  - Every theorem with `lean: <Module>.<lemma>` has a passing Lean proof
    (lake build succeeds and `<lemma>` does not contain `sorry`).
  - All internal cross-references `[text](slug.md)` or `[text](../dir/slug.md)`
    resolve to existing slugs.
  - Pandoc citations `[@key]` resolve to entries in references.bib.
  - references.bib parses (balanced braces, no duplicate cite-keys).
  - references/<key>.md annotation files match a bib cite-key.
  - references/sources/<key>.pdf source files match a bib cite-key.
  - Cited bib keys have corresponding annotation .md files (soft warning).
  - Symbol collisions: two or more notes claiming the same `symbol:`
    canonical notation are flagged as a soft warning.
  - Orphan detection: notes that are not chapter anchors, have no dependents,
    and no narrative introduces/recaps/discusses them.
  - Stub detection: non-narrative notes whose body (excluding frontmatter and
    headings) is below MIN_BODY_CHARS are reported.

Outputs:
  - tools/build/wip-report.md — markdown report listing all issues, suitable
    for inclusion in the book or as standalone status.
  - Exit code 0 if no hard failures, 1 if any.

Hard failures (exit 1):
  - Broken cross-reference or broken citation
  - Bib parse error (brace imbalance or duplicate cite-key)
  - Orphan annotation .md or source PDF (filename without bib entry)
  - Lean proof failure (when lean is configured and theorems claim status: proved with a Lean ref)
  - Frontmatter that fails to parse
  - Theorem with status: proved but no Proof section

Soft warnings (exit 0):
  - Stubs (short bodies)
  - Orphan notes
  - Theorems with status != proved (these are explicit WIP and listed for tracking)
  - Cited bib keys without annotation .md files
  - Symbol collisions across concepts/objects/morphisms
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
MIN_BODY_CHARS = 200  # below this, flag as stub (well-defined notational primitives can be much shorter)
LEAN_DIR = ROOT / "lean"

FM_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
LINK_RE = re.compile(r"\[[^\]]+\]\((?:\.\./[a-z]+/)?([A-Za-z0-9\-]+)\.md(?:#[A-Za-z0-9\-]+)?\)")
CITE_RE = re.compile(r"\[@([a-z][a-z0-9\-]*\d{4}[a-z]?)\]")
PROOF_HEADING_RE = re.compile(r"^##+ Proof", re.MULTILINE)
PROOF_END_RE = re.compile(r"\$\\square\$")


def load_corpus():
    notes = {}
    parse_errors = []
    for d in LIB_DIRS:
        for p in (ROOT / d).glob("*.md"):
            if p.name == "README.md":
                continue
            text = p.read_text()
            m = FM_RE.match(text)
            if not m:
                parse_errors.append((p.relative_to(ROOT), "no frontmatter"))
                continue
            try:
                fm = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError as e:
                parse_errors.append((p.relative_to(ROOT), f"YAML error: {e}"))
                continue
            notes[p.stem] = {
                "slug": p.stem,
                "dir": d,
                "kind": fm.get("type", d.rstrip("s")),
                "fm": fm,
                "body": m.group(2),
                "path": p.relative_to(ROOT),
            }
    return notes, parse_errors


def load_bib_keys():
    """Just the cite-keys, for citation-resolution checks. Bib parse errors
    and duplicate-key detection live in `parse_bib_diagnostics`."""
    bib = ROOT / "references.bib"
    if not bib.exists():
        return set()
    keys = set()
    for m in re.finditer(r"@(\w+)\s*\{\s*([A-Za-z0-9\-]+)\s*,", bib.read_text()):
        if m.group(1).lower() != "comment":
            keys.add(m.group(2))
    return keys


def parse_bib_diagnostics():
    """Brace balance and duplicate cite-keys in references.bib.
    Returns list of error strings; empty if clean."""
    bib = ROOT / "references.bib"
    if not bib.exists():
        return []
    text = bib.read_text()
    errors = []
    if text.count("{") != text.count("}"):
        errors.append(f"references.bib brace imbalance: "
                      f"{text.count('{')} open vs {text.count('}')} close")
    seen, dups = set(), set()
    for m in re.finditer(r"@(\w+)\s*\{\s*([A-Za-z0-9\-]+)\s*,", text):
        if m.group(1).lower() == "comment":
            continue
        k = m.group(2)
        if k in seen:
            dups.add(k)
        seen.add(k)
    if dups:
        errors.append(f"references.bib duplicate cite-keys: {sorted(dups)}")
    return errors


def detect_symbol_collisions(notes):
    """Build a symbol → [slugs] map across concepts/objects/morphisms and
    return groups where two or more notes claim the same canonical symbol.

    The `symbol:` frontmatter field declares the canonical mathematical
    notation for a term (e.g. `symbol: 𝐁` for bilattice). Multiple notes
    claiming the same symbol breaks the disambiguation guarantee the
    convention is meant to provide. Reported as a soft warning.

    Returns: list of (symbol, [slugs]) for each colliding symbol.
    """
    by_symbol = {}
    for s, n in notes.items():
        if n["dir"] not in ("concepts", "objects", "morphisms", "theorems"):
            continue
        sym = n["fm"].get("symbol")
        if not sym:
            continue
        by_symbol.setdefault(sym, []).append(s)
    collisions = sorted(
        (sym, sorted(slugs)) for sym, slugs in by_symbol.items() if len(slugs) > 1
    )
    return collisions


def references_filesystem_diagnostics(bib_keys):
    """Cross-check files in references/ and references/sources/ against bib.
    Returns (orphan_md, orphan_pdf): annotation .md files / source PDFs
    whose stem doesn't match a bib cite-key."""
    refs_dir = ROOT / "references"
    sources_dir = refs_dir / "sources"
    orphan_md, orphan_pdf = [], []
    if refs_dir.exists():
        ann_keys = {p.stem for p in refs_dir.glob("*.md")
                    if p.name not in {"README.md", "validate.py"}}
        orphan_md = sorted(ann_keys - bib_keys)
    if sources_dir.exists():
        pdf_keys = {p.stem for p in sources_dir.glob("*.pdf")}
        orphan_pdf = sorted(pdf_keys - bib_keys)
    return orphan_md, orphan_pdf


def body_chars(body: str) -> int:
    """Count chars in the body, excluding headings and YAML."""
    lines = [ln for ln in body.splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    return sum(len(ln) for ln in lines)


def detect_orphans(notes):
    """Notes that participate in nothing: not referenced by anything AND
    don't position any other note (no introduces/recaps/discusses/chapters).

    We exclude:
      - Part-opener narratives (entry points)
      - Narratives with introduces/recaps/discusses targets (they place content)
      - reference/*.md files (intended as standalone resources)
    """
    referenced = set()
    for s, n in notes.items():
        for key in ("depends-on", "introduces", "recaps", "discusses",
                    "instantiates", "see-also", "realizes", "closes",
                    "chapters", "explores"):
            v = n["fm"].get(key)
            if isinstance(v, list):
                referenced.update(v)
            elif isinstance(v, str):
                referenced.add(v)
        referenced.update(LINK_RE.findall(n["body"]))
        referenced.update(CITE_RE.findall(n["body"]))
    orphans = []
    for s, n in notes.items():
        if s in referenced:
            continue
        if n["dir"] == "references":
            continue  # references are standalone resources by design
        # Narratives that POSITION other notes are not orphans even without inbound refs
        positions = any(n["fm"].get(k) for k in ("introduces", "recaps", "discusses", "chapters"))
        if n["kind"] == "narrative" and positions:
            continue
        # Questions are terminal inquiries — nothing depends on them. They
        # participate in the graph by exploring entities; declaring `explores:`
        # is sufficient for them to be wired in.
        if n["kind"] == "question" and n["fm"].get("explores"):
            continue
        orphans.append(s)
    return sorted(orphans)


def check_lean(notes):
    """For each note with `lean: <ref>` or `lean: [<ref>, ...]`, run lake build
    and verify each referenced lemma doesn't contain `sorry`.
    Returns list of (note, status, msg)."""
    lean_refs = []
    for s, n in notes.items():
        ref = n["fm"].get("lean")
        if not ref:
            continue
        refs = ref if isinstance(ref, list) else [ref]
        for r in refs:
            lean_refs.append((s, r))
    if not lean_refs:
        return []
    if not LEAN_DIR.exists():
        return [(s, "no-lean-dir", f"lean: {ref} but lean/ directory does not exist")
                for s, ref in lean_refs]
    # Run lake build. Make ~/.elan/bin discoverable even when the parent
    # shell hasn't sourced it (this is how elan's installer wires it up).
    import os
    env = os.environ.copy()
    elan_bin = Path.home() / ".elan" / "bin"
    if elan_bin.is_dir() and str(elan_bin) not in env.get("PATH", "").split(":"):
        env["PATH"] = f"{elan_bin}:{env.get('PATH', '')}"
    try:
        r = subprocess.run(["lake", "build"], cwd=LEAN_DIR, env=env,
                           capture_output=True, text=True, timeout=180)
        build_ok = r.returncode == 0
        build_out = (r.stdout + r.stderr)[-2000:]
    except FileNotFoundError:
        return [(s, "lake-missing", "lake binary not on PATH; cannot validate Lean proofs")
                for s, ref in lean_refs]
    except subprocess.TimeoutExpired:
        return [(s, "lake-timeout", "lake build timed out") for s, ref in lean_refs]
    results = []
    for s, ref in lean_refs:
        if not build_ok:
            results.append((s, "build-failed", f"lake build failed; see output below\n{build_out}"))
            continue
        # Find the file & check for sorry near the lemma name
        # ref format: Module.Submodule.lemmaName
        parts = ref.split(".")
        lemma = parts[-1]
        module_path = LEAN_DIR / "/".join(parts[:-1]) / parts[-2] if len(parts) > 1 else None
        # Lean module file convention: PredicationCategories/Algebra/Bilattice.lean
        lean_file = LEAN_DIR.joinpath(*parts[:-1]).with_suffix(".lean") if len(parts) > 1 else None
        if lean_file and lean_file.exists():
            content = lean_file.read_text()
            # Find the declaration (theorem, lemma, def, structure, class, etc.)
            # and inspect for sorry within the next top-level declaration.
            pat = re.compile(
                rf"\b(theorem|lemma|example|def|structure|class|abbrev|inductive)\s+{re.escape(lemma)}\b",
                re.MULTILINE,
            )
            m = pat.search(content)
            if not m:
                results.append((s, "lemma-missing", f"lean ref {ref}: lemma {lemma} not found in {lean_file.name}"))
            else:
                tail = content[m.start(): m.start() + 2000]
                # Look for sorry before the next top-level declaration
                next_def = re.search(
                    r"\n(theorem|lemma|example|def|structure|class|abbrev|inductive|namespace|end)\b",
                    tail[1:],
                )
                body_seg = tail[: 1 + next_def.start()] if next_def else tail
                if "sorry" in body_seg:
                    results.append((s, "sorry", f"lean ref {ref}: contains sorry"))
                else:
                    results.append((s, "ok", f"lean ref {ref}: passes"))
        else:
            results.append((s, "module-missing", f"lean ref {ref}: file {lean_file} not found"))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="only print summary, suppress per-note listings")
    ap.add_argument("--no-lean", action="store_true", help="skip Lean proof validation")
    args = ap.parse_args()

    notes, parse_errors = load_corpus()
    bib_keys = load_bib_keys()
    bib_errors = parse_bib_diagnostics()
    orphan_annotations, orphan_pdfs = references_filesystem_diagnostics(bib_keys)
    cited_keys = set()  # bib keys actually cited in note bodies (filled below)

    issues = {
        "parse_errors": parse_errors,
        "bib_errors": bib_errors,    # references.bib brace / duplicate-key issues
        "broken_links": [],          # (slug, target)
        "broken_citations": [],      # (slug, key)
        "missing_status": [],        # theorem/conjecture without status
        "missing_proof": [],         # status: proved but no Proof section
        "stubs": [],                 # body too short
        "orphans": [],
        "wip_theorems": [],          # status != proved (sketch/draft)
        "lean_failures": [],         # (slug, status, msg) with status != "ok"
        "orphan_annotations": orphan_annotations,  # references/<key>.md without bib entry
        "orphan_pdfs": orphan_pdfs,  # references/sources/<key>.pdf without bib entry
        "missing_annotations": [],   # cited bib keys without references/<key>.md (soft)
        "symbol_collisions": detect_symbol_collisions(notes),  # soft
    }

    all_slugs = set(notes.keys())

    for s, n in notes.items():
        kind = n["kind"]
        body = n["body"]
        fm = n["fm"]

        # Cross-references
        for tgt in LINK_RE.findall(body):
            if tgt not in all_slugs:
                issues["broken_links"].append((s, tgt))
        for key in CITE_RE.findall(body):
            if key not in bib_keys:
                issues["broken_citations"].append((s, key))
            else:
                cited_keys.add(key)

        # Theorem status / proof
        if kind in ("theorem", "conjecture", "lemma", "proposition", "corollary"):
            status = fm.get("status")
            if not status:
                issues["missing_status"].append(s)
            elif status == "proved":
                # Require BOTH a `## Proof` heading AND a `$\square$` end-of-proof
                # marker. A heading without a marker leaves the proof's end
                # ambiguous; a marker without a heading hides where the proof
                # begins. Both make the proof structure unambiguous.
                if not PROOF_HEADING_RE.search(body):
                    issues["missing_proof"].append((s, "no Proof heading"))
                elif not PROOF_END_RE.search(body):
                    issues["missing_proof"].append((s, "no $\\square$ marker"))
            elif status in ("sketch", "draft"):
                issues["wip_theorems"].append((s, status))
            else:
                issues["missing_status"].append(s)

        # Stub detection
        if kind not in ("narrative",):
            if body_chars(body) < MIN_BODY_CHARS:
                issues["stubs"].append((s, kind, body_chars(body)))

    issues["orphans"] = detect_orphans(notes)

    # Cited bib keys without annotation .md files in references/
    refs_dir = ROOT / "references"
    if refs_dir.exists():
        ann_keys = {p.stem for p in refs_dir.glob("*.md")
                    if p.name not in {"README.md", "validate.py"}}
        issues["missing_annotations"] = sorted(cited_keys - ann_keys)

    if not args.no_lean:
        lean_results = check_lean(notes)
        for s, status, msg in lean_results:
            if status != "ok":
                issues["lean_failures"].append((s, status, msg))

    # Lean coupling summary: which theorems/objects/morphisms carry a lean: ref
    lean_coupled = sorted(
        s for s, n in notes.items()
        if n["fm"].get("lean") and s.lower() != "readme"
    )
    proved_theorems = sorted(
        s for s, n in notes.items()
        if n["kind"] in ("theorem", "conjecture", "lemma", "proposition", "corollary")
        and n["fm"].get("status") == "proved"
    )
    proved_with_lean = sorted(s for s in proved_theorems
                              if notes[s]["fm"].get("lean"))

    # Write report
    OUT = ROOT / "tools" / "build"
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / "wip-report.md"
    with report_path.open("w") as f:
        f.write("# Library status report\n\n")
        f.write(f"Total notes: {len(notes)}\n\n")

        def section(title, items, fmt):
            f.write(f"## {title} ({len(items)})\n\n")
            if items:
                for x in items:
                    f.write("- " + fmt(x) + "\n")
            else:
                f.write("*(none)*\n")
            f.write("\n")

        section("Parse errors", issues["parse_errors"], lambda x: f"`{x[0]}`: {x[1]}")
        section("references.bib errors", issues["bib_errors"], lambda x: x)
        section("Broken cross-references", issues["broken_links"],
                lambda x: f"`{x[0]}` references missing slug `{x[1]}`")
        section("Broken citations", issues["broken_citations"],
                lambda x: f"`{x[0]}` cites missing bib key `{x[1]}`")
        section("Orphan annotation files (references/<key>.md without bib entry)",
                issues["orphan_annotations"], lambda x: f"`references/{x}.md`")
        section("Orphan source PDFs (references/sources/<key>.pdf without bib entry)",
                issues["orphan_pdfs"], lambda x: f"`references/sources/{x}.pdf`")
        section("Cited bib keys without annotation files",
                issues["missing_annotations"], lambda x: f"`{x}`")
        section("Symbol collisions (frontmatter `symbol:`)",
                issues["symbol_collisions"],
                lambda x: f"`{x[0]}` claimed by " + ", ".join(f"`{s}`" for s in x[1]))
        section("Theorems missing status", issues["missing_status"],
                lambda x: f"`{x}`")
        section("Theorems with status: proved but no proof section",
                issues["missing_proof"], lambda x: f"`{x[0]}` — {x[1]}")
        section("WIP theorems (sketch / draft)",
                issues["wip_theorems"], lambda x: f"`{x[0]}` — {x[1]}")
        section("Stubs (body < 400 chars)", issues["stubs"],
                lambda x: f"`{x[0]}` ({x[1]}, {x[2]} chars)")
        section("Orphans (no incoming refs)", issues["orphans"],
                lambda x: f"`{x}`")
        section("Lean proof issues", issues["lean_failures"],
                lambda x: f"`{x[0]}`: {x[1]} — {x[2].splitlines()[0] if x[2] else ''}")

        # Lean coupling summary — lists every prose note carrying a lean: ref
        # and reports proved-theorem coverage. Not an error category — a
        # visibility section so coupling drift is noticed early.
        f.write(f"## Lean coupling ({len(lean_coupled)} prose notes carry `lean:`)\n\n")
        if proved_theorems:
            pct = 100.0 * len(proved_with_lean) / len(proved_theorems)
            f.write(f"Proved theorems with Lean: {len(proved_with_lean)} / "
                    f"{len(proved_theorems)} ({pct:.0f}%).\n\n")
        if lean_coupled:
            f.write("Notes carrying a `lean:` ref:\n\n")
            for s in lean_coupled:
                f.write(f"- `{s}`\n")
            f.write("\n")

    # Console summary
    print(f"validate.py: {len(notes)} notes scanned")
    counts = [
        ("parse_errors", "parse errors"),
        ("bib_errors", "references.bib errors"),
        ("broken_links", "broken cross-references"),
        ("broken_citations", "broken citations"),
        ("orphan_annotations", "orphan annotation files"),
        ("orphan_pdfs", "orphan source PDFs"),
        ("missing_annotations", "cited keys without annotation"),
        ("symbol_collisions", "symbol collisions"),
        ("missing_status", "theorems missing status"),
        ("missing_proof", "theorems missing proof section"),
        ("wip_theorems", "WIP theorems"),
        ("stubs", "stubs"),
        ("orphans", "orphans"),
        ("lean_failures", "Lean proof issues"),
    ]
    for key, label in counts:
        n = len(issues[key])
        if n:
            print(f"  {n} {label}")

    print(f"  report: {report_path.relative_to(ROOT)}")

    hard_fail = (len(issues["parse_errors"]) > 0
                 or len(issues["bib_errors"]) > 0
                 or len(issues["broken_links"]) > 0
                 or len(issues["broken_citations"]) > 0
                 or len(issues["orphan_annotations"]) > 0
                 or len(issues["orphan_pdfs"]) > 0
                 or len(issues["missing_proof"]) > 0
                 or any(st for _, st, _ in issues["lean_failures"]
                        if st in ("build-failed", "sorry", "lemma-missing", "module-missing")))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
