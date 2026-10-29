#!/usr/bin/env python3
"""index-triage.py — Build a queryable JSON index of all triage files.

Source of truth: content/triage/
Output: content/triage/.triage-index.json

Extracts frontmatter, first heading, file stats, and path-based
classification for every .md file in triage. The index enables
mine-triage and enrich-triage to work without re-reading every file.

Usage:
    python3 scripts/index-triage.py [content_dir]

If content_dir is not specified, tries content/ as submodule then
as sibling directory.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def find_content_dir():
    """Find the content directory."""
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    candidates = [
        repo_root / "content",
        repo_root.parent / "content",
    ]

    if len(sys.argv) > 1:
        candidates.insert(0, Path(sys.argv[1]))

    for c in candidates:
        if (c / "triage").is_dir():
            return c

    print("ERROR: Could not find content/triage/ directory.")
    print(f"Tried: {[str(c) for c in candidates]}")
    sys.exit(1)


def parse_frontmatter(content):
    """Extract YAML frontmatter as a dict of strings."""
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
        # Skip empty lines
        if not line.strip():
            continue

        # List item
        if line.startswith("  - ") or line.startswith("    - "):
            if current_key and current_list is not None:
                val = line.strip().lstrip("- ").strip().strip('"').strip("'")
                current_list.append(val)
            continue

        # Key-value pair
        if ":" in line and not line.startswith(" "):
            # Save previous list
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

    # Save final list
    if current_key and current_list is not None:
        result[current_key] = current_list

    return result


def extract_first_heading(content):
    """Get the first markdown heading."""
    # Skip frontmatter
    text = content
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            text = text[end + 3:]

    match = re.search(r"^#+ +(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def classify_by_path(rel_path):
    """Guess target discipline and type from the file's path in triage."""
    parts = rel_path.lower().split("/")

    # Path-based discipline hints
    discipline_hints = {
        "engine": "technology",
        "contracts": "technology",
        "specifications": "technology",
        "theorem": "mathematics",
        "library": None,  # varies
        "relationality": "mathematics",
        "relational derivatives": "mathematics",
        "old-notes": None,
        "delta register": "personal",
        "groundhog": "domesticity",
        "texts": None,
        "triage-materials": None,
    }

    discipline = None
    for hint, disc in discipline_hints.items():
        if hint in parts:
            discipline = disc
            break

    # Path-based type hints
    type_hints = {
        "specifications": "specification",
        "spec": "specification",
        "contracts": "specification",
        "theorem": "theorem",
        "texts": "text",
        "derivations": "derivation",
        "curricula": "lesson",
        "log": "babble",
    }

    content_type = None
    for hint, ct in type_hints.items():
        if hint in parts:
            content_type = ct
            break

    return discipline, content_type


def title_from_filename(filename):
    """Derive a title from a filename."""
    stem = Path(filename).stem
    # Handle kebab-case and snake_case
    title = stem.replace("-", " ").replace("_", " ")
    # Title case
    return title.title()


def index_file(filepath, content_dir):
    """Build an index entry for one file."""
    rel_path = str(filepath.relative_to(content_dir / "triage"))

    try:
        content = filepath.read_text(errors="replace")[:4000]
    except Exception as e:
        return {"path": rel_path, "error": str(e)}

    fm = parse_frontmatter(content)
    heading = extract_first_heading(content)
    discipline_guess, type_guess = classify_by_path(rel_path)

    # Word count (rough)
    body = content
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            body = content[end + 3:]
    word_count = len(body.split())

    entry = {
        "path": rel_path,
        "title": fm.get("title") or heading or title_from_filename(filepath.name),
        "title_source": (
            "frontmatter" if "title" in fm
            else "heading" if heading
            else "filename"
        ),
        "has_frontmatter": bool(fm),
        "word_count": word_count,
    }

    # Include existing frontmatter fields
    for key in ["type", "tags", "description", "date", "date-created",
                 "authors", "author", "aliases", "triage-status",
                 "target-discipline"]:
        if key in fm:
            entry[key] = fm[key]

    # Add guesses where no explicit value exists
    if "type" not in entry and type_guess:
        entry["type_guess"] = type_guess
    if "target-discipline" not in entry and discipline_guess:
        entry["discipline_guess"] = discipline_guess

    # Enrichment status
    has_required = all(k in fm for k in ["title", "type", "date-created"])
    has_recommended = all(k in fm for k in ["tags", "description"])
    if has_required and has_recommended:
        entry["enrichment"] = "complete"
    elif has_required:
        entry["enrichment"] = "partial"
    elif fm:
        entry["enrichment"] = "minimal"
    else:
        entry["enrichment"] = "none"

    return entry


def main():
    content_dir = find_content_dir()
    triage_dir = content_dir / "triage"
    print(f"Indexing triage at: {triage_dir}")

    entries = []
    skip_dirs = {".trash", ".obsidian"}

    for root, dirs, files in os.walk(triage_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if not f.endswith(".md"):
                continue
            filepath = Path(root) / f
            entry = index_file(filepath, content_dir)
            entries.append(entry)

    # Sort by path for stable output
    entries.sort(key=lambda e: e["path"])

    # Summary stats
    stats = {
        "total_files": len(entries),
        "with_frontmatter": sum(1 for e in entries if e.get("has_frontmatter")),
        "without_frontmatter": sum(1 for e in entries if not e.get("has_frontmatter")),
        "enrichment_complete": sum(1 for e in entries if e.get("enrichment") == "complete"),
        "enrichment_partial": sum(1 for e in entries if e.get("enrichment") == "partial"),
        "enrichment_minimal": sum(1 for e in entries if e.get("enrichment") == "minimal"),
        "enrichment_none": sum(1 for e in entries if e.get("enrichment") == "none"),
        "indexed_at": datetime.now().isoformat(),
    }

    index = {
        "stats": stats,
        "entries": entries,
    }

    output_path = triage_dir / ".triage-index.json"
    with open(output_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"\nStats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"\nIndex written to: {output_path}")


if __name__ == "__main__":
    main()
