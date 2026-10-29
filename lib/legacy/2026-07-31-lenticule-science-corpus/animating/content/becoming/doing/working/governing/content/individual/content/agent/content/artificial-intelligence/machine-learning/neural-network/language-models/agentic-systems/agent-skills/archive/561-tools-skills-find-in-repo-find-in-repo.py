#!/usr/bin/env python3
"""find-in-repo.py — Search the published repo for existing content.

Answers "does this already exist?" by searching titles, filenames,
frontmatter fields, and body text across the published content
(excluding triage/, slop/, private/).

Usage:
    python3 scripts/find-in-repo.py "semiotic markdown"
    python3 scripts/find-in-repo.py --field type --value specification
    python3 scripts/find-in-repo.py --discipline mathematics "heyting algebra"

Output is structured for both human reading and machine parsing.
"""

import argparse
import os
import re
import sys
from pathlib import Path


def find_content_dir():
    """Find the content directory."""
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    for c in [repo_root / "content", repo_root.parent / "content"]:
        if c.is_dir() and (c / "technology").is_dir():
            return c

    print("ERROR: Could not find content/ directory.")
    sys.exit(1)


EXCLUDE_DIRS = {"triage", "slop", "private", ".obsidian", ".trash"}


def parse_frontmatter(content):
    """Extract frontmatter as dict."""
    if not content.startswith("---"):
        return {}

    end = content.find("---", 3)
    if end < 0:
        return {}

    fm_text = content[3:end].strip()
    result = {}
    current_key = None
    current_list = None

    for line in fm_text.split("\n"):
        if not line.strip():
            continue
        if line.startswith("  - ") or line.startswith("    - "):
            if current_key and current_list is not None:
                val = line.strip().lstrip("- ").strip().strip('"').strip("'")
                current_list.append(val)
            continue
        if ":" in line and not line.startswith(" "):
            if current_key and current_list is not None:
                result[current_key] = current_list
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val:
                result[key] = val
                current_key = key
                current_list = None
            else:
                current_key = key
                current_list = []

    if current_key and current_list is not None:
        result[current_key] = current_list

    return result


def search_files(content_dir, query=None, field=None, value=None,
                 discipline=None, content_type=None):
    """Search published content. Returns list of (path, title, match_type, context)."""
    results = []
    query_lower = query.lower() if query else None
    query_words = query_lower.split() if query_lower else []

    for root, dirs, files in os.walk(content_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        rel_root = str(Path(root).relative_to(content_dir))

        # Filter by discipline if specified
        if discipline:
            parts = rel_root.split("/")
            if parts[0] != "." and parts[0] != discipline:
                continue

        for f in files:
            if not f.endswith(".md"):
                continue

            filepath = Path(root) / f
            rel_path = str(filepath.relative_to(content_dir))

            try:
                content = filepath.read_text(errors="replace")[:6000]
            except Exception:
                continue

            fm = parse_frontmatter(content)

            # Filter by content type
            if content_type and fm.get("type") != content_type:
                continue

            # Field-value search
            if field and value:
                fm_val = fm.get(field, "")
                if isinstance(fm_val, list):
                    if any(value.lower() in v.lower() for v in fm_val):
                        results.append((rel_path, fm.get("title", f),
                                        f"field:{field}", str(fm_val)))
                elif value.lower() in str(fm_val).lower():
                    results.append((rel_path, fm.get("title", f),
                                    f"field:{field}", str(fm_val)))
                continue

            # Text query search
            if not query_lower:
                continue

            title = fm.get("title", "").lower()
            aliases = fm.get("aliases", [])
            if isinstance(aliases, str):
                aliases = [aliases]
            aliases_lower = [a.lower() for a in aliases]
            filename_lower = Path(f).stem.lower().replace("-", " ")

            # Exact title match
            if query_lower in title:
                results.append((rel_path, fm.get("title", f),
                                "title", title))
                continue

            # Alias match
            if any(query_lower in a for a in aliases_lower):
                matched = [a for a in aliases if query_lower in a.lower()]
                results.append((rel_path, fm.get("title", f),
                                "alias", ", ".join(matched)))
                continue

            # Filename match
            if query_lower in filename_lower:
                results.append((rel_path, fm.get("title", f),
                                "filename", filename_lower))
                continue

            # All query words in title/filename/aliases
            all_text = f"{title} {filename_lower} {' '.join(aliases_lower)}"
            if all(w in all_text for w in query_words):
                results.append((rel_path, fm.get("title", f),
                                "words", all_text[:80]))
                continue

            # Body text match (first 4000 chars)
            body = content
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    body = content[end + 3:]

            if query_lower in body.lower():
                # Find context
                idx = body.lower().index(query_lower)
                start = max(0, idx - 40)
                end_ctx = min(len(body), idx + len(query) + 40)
                context = body[start:end_ctx].replace("\n", " ").strip()
                results.append((rel_path, fm.get("title", f),
                                "body", f"...{context}..."))

    # Sort: title matches first, then alias, filename, words, body
    priority = {"title": 0, "alias": 1, "filename": 2, "words": 3}
    results.sort(key=lambda r: (
        priority.get(r[2], 4),
        r[0]
    ))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Search published repo for existing content")
    parser.add_argument("query", nargs="?", help="Text to search for")
    parser.add_argument("--field", help="Frontmatter field to search")
    parser.add_argument("--value", help="Value to match in field")
    parser.add_argument("--discipline", help="Limit to discipline")
    parser.add_argument("--type", dest="content_type",
                        help="Limit to content type")
    parser.add_argument("--limit", type=int, default=20,
                        help="Max results (default 20)")
    args = parser.parse_args()

    if not args.query and not (args.field and args.value):
        parser.error("Provide a query or --field/--value pair")

    content_dir = find_content_dir()
    results = search_files(content_dir, query=args.query, field=args.field,
                           value=args.value, discipline=args.discipline,
                           content_type=args.content_type)

    if not results:
        print("No matches found.")
        return

    print(f"Found {len(results)} match{'es' if len(results) != 1 else ''}:\n")
    for i, (path, title, match_type, context) in enumerate(results[:args.limit]):
        print(f"  [{match_type}] {title}")
        print(f"         {path}")
        if context and match_type not in ("title", "filename"):
            print(f"         {context}")
        print()

    if len(results) > args.limit:
        print(f"  ... and {len(results) - args.limit} more")


if __name__ == "__main__":
    main()
