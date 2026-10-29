#!/usr/bin/env python3
"""Fix broken relative-path markdown links where the target file exists elsewhere.

For each broken markdown link [text](path.md):
1. Extract the filename stem from the target path
2. Search the vault for a file with that stem
3. If exactly one match is found, compute the correct relative path
4. Replace the broken link with the fixed one

Only fixes md-link references (not wikilinks) where:
- The target file exists somewhere in the vault
- There is exactly one file matching the stem (unambiguous)
- The target is not 404.md or index.md
"""

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

VAULT_ROOT = Path("content")
IGNORE_DIRS = {".obsidian", "private", "meta", "slop", "triage"}


def find_all_files(vault_root: Path) -> dict[str, list[Path]]:
    """Build stem -> [paths] index."""
    files_by_stem: dict[str, list[Path]] = defaultdict(list)
    for md_file in vault_root.rglob("*.md"):
        rel = md_file.relative_to(vault_root)
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        stem = md_file.stem.lower()
        files_by_stem[stem].append(md_file)
    return files_by_stem


def compute_relative_path(source: Path, target: Path) -> str:
    """Compute relative path from source file to target file."""
    source_dir = source.parent
    try:
        rel = os.path.relpath(target, source_dir).replace("\\", "/")
        return rel
    except ValueError:
        return None


def fix_file(
    source_path: Path,
    broken_entries: list[dict],
    files_by_stem: dict[str, list[Path]],
    dry_run: bool = False,
) -> list[dict]:
    """Fix broken markdown links in a single source file."""
    fixes = []

    try:
        content = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return fixes

    lines = content.split("\n")
    modified = False

    for entry in broken_entries:
        if entry["link_type"] != "md-link":
            continue

        target = entry["target"]
        line_num = entry["line"]  # 1-indexed

        # Skip special cases
        target_path = Path(target)
        stem = target_path.stem.lower()
        if stem in ("404", "index", "skill"):
            continue

        # Skip mathematical notation false positives
        if any(c in stem for c in "⊢γ"):
            continue

        # Skip ambiguous/generic stems that could match unrelated files
        AMBIGUOUS_STEMS = {
            "path", "set", "process", "target", "source", "value",
            "type", "model", "term", "concept", "relation", "example",
        }
        if stem in AMBIGUOUS_STEMS:
            continue

        # Skip example/placeholder links
        if "relative/" in target or "example" in target.lower():
            continue

        # Find matching files
        matches = files_by_stem.get(stem, [])
        if len(matches) != 1:
            continue  # ambiguous or no match

        target_file = matches[0]

        # Compute correct relative path
        new_rel = compute_relative_path(source_path, target_file)
        if not new_rel:
            continue

        # Build replacement
        line_idx = line_num - 1
        if line_idx >= len(lines):
            continue

        old_line = lines[line_idx]
        # Escape the target for regex (it may contain special chars)
        escaped_target = re.escape(target)
        # Replace the target in markdown link syntax
        pattern = r"(\[[^\]]*\]\()" + escaped_target + r"((?:#[^)]*)?\))"
        new_line = re.sub(pattern, r"\1" + new_rel + r"\2", old_line)

        if new_line != old_line:
            fixes.append({
                "source": str(source_path),
                "line": line_num,
                "old_target": target,
                "new_target": new_rel,
            })
            lines[line_idx] = new_line
            modified = True

    if modified and not dry_run:
        source_path.write_text("\n".join(lines), encoding="utf-8")

    return fixes


def main():
    dry_run = "--dry-run" in sys.argv
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Load audit results
    with open("audit-results.json", encoding="utf-8") as f:
        data = json.load(f)

    # Filter to md-link type only, exclude 404.md
    broken = [
        e for e in data
        if e["link_type"] == "md-link" and e["target"] != "404.md"
    ]

    # Build file index
    files_by_stem = find_all_files(VAULT_ROOT)

    # Group broken entries by source file
    by_source: dict[str, list[dict]] = defaultdict(list)
    for e in broken:
        by_source[e["source"]].append(e)

    all_fixes = []
    for source_slug, entries in sorted(by_source.items()):
        source_path = VAULT_ROOT / (source_slug + ".md")
        if not source_path.exists():
            continue
        fixes = fix_file(source_path, entries, files_by_stem, dry_run)
        all_fixes.extend(fixes)

    # Report
    mode = "DRY RUN" if dry_run else "APPLIED"
    print(f"[{mode}] Fixed {len(all_fixes)} references:")
    for fix in all_fixes:
        print(f"  {fix['source']}:{fix['line']}")
        print(f"    {fix['old_target']}")
        print(f"    → {fix['new_target']}")
    print(f"\nTotal: {len(all_fixes)} fixes")


if __name__ == "__main__":
    main()
