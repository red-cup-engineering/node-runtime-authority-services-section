#!/usr/bin/env python3
"""Audit a markdown vault for broken internal references.

Scans all .md files under a vault root, extracts wikilinks ([[target]])
and markdown links ([text](target.md)), and reports references that do
not resolve to any existing file.

Usage:
    python .claude/skills/audit-vault-references/audit-vault-references.py [--vault-root content/]
                                                                          [--format table|json|csv]
                                                                          [--category]
                                                                          [--ignore GLOB ...]
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


# Patterns
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?\|?[^\]]*\]\]")
MD_LINK_RE = re.compile(r"\[(?:[^\]]*)\]\(([^)#]+\.md)(?:#[^)]*)?\)")


def extract_frontmatter(md_file: Path) -> dict:
    """Extract title and aliases from a markdown file's YAML frontmatter."""
    try:
        content = md_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}

    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}

    fm_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)

    result = {}
    # Simple YAML parsing for title and aliases
    for i, line in enumerate(fm_lines):
        if line.startswith("title:"):
            val = line[len("title:"):].strip().strip('"').strip("'")
            if val:
                result["title"] = val
        elif line.startswith("aliases:"):
            aliases = []
            for alias_line in fm_lines[i + 1:]:
                stripped = alias_line.strip()
                if stripped.startswith("- "):
                    alias = stripped[2:].strip().strip('"').strip("'")
                    if alias:
                        aliases.append(alias)
                elif not stripped or not alias_line.startswith(" "):
                    break
            result["aliases"] = aliases

    return result


def find_all_md_files(vault_root: Path, ignore_patterns: list[str]) -> dict[str, Path]:
    """Build a map of slug -> path for all .md files in the vault."""
    files: dict[str, Path] = {}
    slugs_by_stem: dict[str, list[Path]] = defaultdict(list)
    titles_and_aliases: dict[str, list[Path]] = defaultdict(list)

    for md_file in vault_root.rglob("*.md"):
        rel = md_file.relative_to(vault_root)

        # Check ignore patterns
        skip = False
        for pattern in ignore_patterns:
            if rel.match(pattern) or any(
                part == pattern.rstrip("/") for part in rel.parts
            ):
                skip = True
                break
        if skip:
            continue

        # Store by full relative path (without .md extension)
        slug = str(rel.with_suffix("")).replace("\\", "/")
        files[slug] = md_file

        # Also index by stem for wikilink resolution
        stem = md_file.stem.lower()
        slugs_by_stem[stem].append(md_file)

        # Index by aliases for wikilink resolution
        fm = extract_frontmatter(md_file)
        for alias in fm.get("aliases", []):
            key = alias.lower().replace(" ", "-")
            titles_and_aliases[key].append(md_file)

    return files, slugs_by_stem, titles_and_aliases


def resolve_wikilink(
    target: str,
    source_file: Path,
    vault_root: Path,
    files: dict[str, Path],
    slugs_by_stem: dict[str, list[Path]],
    titles_and_aliases: dict[str, list[Path]] = None,
) -> bool:
    """Check if a wikilink target resolves to an existing file."""
    target_clean = target.strip()
    if not target_clean:
        return True  # empty link, not a broken reference

    # Try exact match by stem (case-insensitive)
    target_lower = target_clean.lower().replace(" ", "-")
    if target_lower in slugs_by_stem:
        return True

    # Try match by title or alias (case-insensitive)
    if titles_and_aliases and target_lower in titles_and_aliases:
        return True

    # Try as a relative path from source
    source_dir = source_file.parent
    candidate = source_dir / (target_clean + ".md")
    if candidate.exists():
        return True
    candidate = source_dir / target_clean / "index.md"
    if candidate.exists():
        return True

    # Try as absolute path from vault root
    candidate = vault_root / (target_clean + ".md")
    if candidate.exists():
        return True
    candidate = vault_root / target_clean / "index.md"
    if candidate.exists():
        return True

    # Try slug match
    target_slug = target_clean.replace(" ", "-").replace("\\", "/")
    if target_slug in files or target_slug.lower() in {
        k.lower() for k in files
    }:
        return True

    return False


def resolve_md_link(
    target: str,
    source_file: Path,
    vault_root: Path,
) -> bool:
    """Check if a markdown link target resolves to an existing file."""
    target_clean = target.strip()
    if not target_clean or target_clean.startswith("http"):
        return True  # external link or empty

    # Resolve relative to source file
    source_dir = source_file.parent
    candidate = (source_dir / target_clean).resolve()
    if candidate.exists():
        return True

    # Try from vault root (strip leading / to avoid absolute path override)
    target_from_root = target_clean.lstrip("/")
    candidate = (vault_root / target_from_root).resolve()
    if candidate.exists():
        return True

    return False


def categorize_target(target: str) -> str:
    """Categorize a broken reference by likely type."""
    target_lower = target.lower().replace(" ", "-")

    # People
    people_indicators = ["people/", "person/"]
    if any(ind in target_lower for ind in people_indicators):
        return "person"

    # Terms
    if "terms/" in target_lower or "term/" in target_lower:
        return "term"

    # Concepts
    if "concepts/" in target_lower or "concept/" in target_lower:
        return "concept"

    # Encyclopedia
    if "encyclopedia/" in target_lower:
        return "encyclopedia"

    # If it looks like a name (capitalized words, no path separators)
    if "/" not in target and all(
        w[0].isupper() for w in target.split() if w
    ):
        return "person-or-concept"

    # Discipline/topic paths
    if "/" in target:
        return "path"

    return "unknown"


def audit_vault(
    vault_root: Path,
    ignore_patterns: list[str],
    categorize: bool = False,
) -> list[dict]:
    """Run the full audit and return broken references."""
    files, slugs_by_stem, titles_and_aliases = find_all_md_files(
        vault_root, ignore_patterns
    )
    broken = []

    for slug, md_file in sorted(files.items()):
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        lines = content.split("\n")

        # Skip frontmatter
        in_frontmatter = False
        start_line = 0
        if lines and lines[0].strip() == "---":
            in_frontmatter = True
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    start_line = i + 1
                    break

        for line_num, line in enumerate(lines[start_line:], start_line + 1):
            # Check wikilinks
            for match in WIKILINK_RE.finditer(line):
                target = match.group(1)
                if not resolve_wikilink(
                    target, md_file, vault_root, files, slugs_by_stem,
                    titles_and_aliases,
                ):
                    entry = {
                        "source": slug,
                        "line": line_num,
                        "target": target,
                        "link_type": "wikilink",
                    }
                    if categorize:
                        entry["category"] = categorize_target(target)
                    broken.append(entry)

            # Check markdown links
            for match in MD_LINK_RE.finditer(line):
                target = match.group(1)
                if not resolve_md_link(target, md_file, vault_root):
                    entry = {
                        "source": slug,
                        "line": line_num,
                        "target": target,
                        "link_type": "md-link",
                    }
                    if categorize:
                        entry["category"] = categorize_target(target)
                    broken.append(entry)

    return broken


def format_table(broken: list[dict], categorize: bool) -> str:
    """Format results as a text table."""
    if not broken:
        return "No broken references found."

    lines = []
    if categorize:
        lines.append(f"{'Source':<60} {'Line':>5}  {'Type':<10} {'Category':<20} Target")
        lines.append("-" * 130)
        for entry in broken:
            lines.append(
                f"{entry['source']:<60} {entry['line']:>5}  "
                f"{entry['link_type']:<10} {entry.get('category', ''):<20} "
                f"{entry['target']}"
            )
    else:
        lines.append(f"{'Source':<60} {'Line':>5}  {'Type':<10} Target")
        lines.append("-" * 110)
        for entry in broken:
            lines.append(
                f"{entry['source']:<60} {entry['line']:>5}  "
                f"{entry['link_type']:<10} {entry['target']}"
            )

    # Summary
    lines.append("")
    lines.append(f"Total broken references: {len(broken)}")

    if categorize:
        by_category = defaultdict(int)
        for entry in broken:
            by_category[entry.get("category", "unknown")] += 1
        lines.append("By category:")
        for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat}: {count}")

    by_source = defaultdict(int)
    for entry in broken:
        by_source[entry["source"]] += 1
    top_sources = sorted(by_source.items(), key=lambda x: -x[1])[:10]
    lines.append("Top 10 sources with broken references:")
    for source, count in top_sources:
        lines.append(f"  {source}: {count}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Audit a markdown vault for broken internal references."
    )
    parser.add_argument(
        "--vault-root",
        default="content",
        help="Root directory of the vault (default: content/)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--category",
        action="store_true",
        help="Categorize broken references by likely type",
    )
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=[".obsidian", "private", "meta"],
        help="Directory names to ignore (default: .obsidian private meta)",
    )
    parser.add_argument(
        "--output",
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()
    vault_root = Path(args.vault_root)

    if not vault_root.is_dir():
        print(f"Error: {vault_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    broken = audit_vault(vault_root, args.ignore, args.category)

    if args.format == "json":
        result = json.dumps(broken, indent=2)
    elif args.format == "csv":
        import csv
        import io

        output = io.StringIO()
        if broken:
            writer = csv.DictWriter(output, fieldnames=broken[0].keys())
            writer.writeheader()
            writer.writerows(broken)
        result = output.getvalue()
    else:
        result = format_table(broken, args.category)

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"Results written to {args.output}")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(result)


if __name__ == "__main__":
    main()
