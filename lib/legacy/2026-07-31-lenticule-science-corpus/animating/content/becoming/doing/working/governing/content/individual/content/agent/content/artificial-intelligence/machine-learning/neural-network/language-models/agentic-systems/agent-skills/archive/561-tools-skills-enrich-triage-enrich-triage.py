#!/usr/bin/env python3
"""enrich-triage.py — Mechanically enrich triage file frontmatter.

Adds missing frontmatter fields that can be derived without inference:
- title: from first heading or filename
- date-created: from git history or file mtime
- Fixes deprecated fields (date → date-created, author → authors)
- Normalizes existing frontmatter formatting

Does NOT:
- Guess type, tags, or description (those need inference)
- Modify body content
- Delete or move files
- Overwrite existing correct values

Usage:
    python3 scripts/enrich-triage.py [--dry-run] [--batch N] [path_filter]

Examples:
    python3 scripts/enrich-triage.py --dry-run          # Preview all changes
    python3 scripts/enrich-triage.py --batch 50          # Enrich 50 files
    python3 scripts/enrich-triage.py specifications/     # Enrich specs only
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def find_content_dir():
    """Find the content directory."""
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    for c in [repo_root / "content", repo_root.parent / "content"]:
        if (c / "triage").is_dir():
            return c

    print("ERROR: Could not find content/triage/")
    sys.exit(1)


def git_creation_date(filepath, content_dir):
    """Get the file's first commit date from git."""
    try:
        result = subprocess.run(
            ["git", "log", "--diff-filter=A", "--follow", "--format=%aI",
             "--", str(filepath.relative_to(content_dir))],
            capture_output=True, text=True, cwd=content_dir, timeout=5,
        )
        if result.stdout.strip():
            # Return just the date part
            return result.stdout.strip().split("\n")[-1][:10]
    except Exception:
        pass
    return None


def title_from_filename(filename):
    """Derive a title from filename."""
    stem = Path(filename).stem
    return stem.replace("-", " ").replace("_", " ").title()


def extract_first_heading(content):
    """Get the first markdown heading from body (after frontmatter)."""
    text = content
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            text = text[end + 3:]

    match = re.search(r"^#+ +(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def parse_frontmatter_raw(content):
    """Return (fm_text, body) or (None, content) if no frontmatter."""
    if not content.startswith("---"):
        return None, content

    end = content.find("---", 3)
    if end < 0:
        return None, content

    return content[3:end], content[end + 3:]


def parse_fm_dict(fm_text):
    """Simple YAML-ish parser for frontmatter."""
    result = {}
    current_key = None
    current_list = None

    for line in fm_text.strip().split("\n"):
        if not line.strip():
            continue

        if (line.startswith("  - ") or line.startswith("    - ")):
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


def rebuild_frontmatter(fm_dict):
    """Rebuild frontmatter YAML from dict."""
    lines = []
    # Preferred field order
    order = ["title", "aliases", "date-created", "date-updated",
             "type", "authors", "tags", "description",
             "triage-status", "target-discipline"]

    written = set()
    for key in order:
        if key not in fm_dict:
            continue
        val = fm_dict[key]
        written.add(key)
        if isinstance(val, list):
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {item}")
        else:
            # Quote strings that need it
            if isinstance(val, str) and (":" in val or val.startswith("[")):
                lines.append(f'{key}: "{val}"')
            else:
                lines.append(f"{key}: {val}")

    # Write remaining fields in original order
    for key, val in fm_dict.items():
        if key in written:
            continue
        if isinstance(val, list):
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {item}")
        else:
            if isinstance(val, str) and (":" in val or val.startswith("[")):
                lines.append(f'{key}: "{val}"')
            else:
                lines.append(f"{key}: {val}")

    return "\n".join(lines)


def enrich_file(filepath, content_dir, dry_run=False):
    """Enrich one file. Returns (changes_made, change_descriptions)."""
    try:
        content = filepath.read_text(errors="replace")
    except Exception:
        return 0, []

    fm_text, body = parse_frontmatter_raw(content)
    changes = []

    if fm_text is None:
        # No frontmatter at all — add minimal
        heading = extract_first_heading(content)
        title = heading or title_from_filename(filepath.name)
        git_date = git_creation_date(filepath, content_dir)
        date = git_date or datetime.now().strftime("%Y-%m-%d")

        new_fm = f'title: "{title}"\ndate-created: {date}T00:00:00'
        new_content = f"---\n{new_fm}\n---\n{content}"
        changes.append(f"added frontmatter (title, date-created)")
    else:
        fm = parse_fm_dict(fm_text)
        original_fm = dict(fm)

        # Fix: add title if missing
        if "title" not in fm:
            heading = extract_first_heading(content)
            fm["title"] = heading or title_from_filename(filepath.name)
            changes.append(f"added title: {fm['title']}")

        # Fix: deprecated date → date-created
        if "date" in fm and "date-created" not in fm:
            fm["date-created"] = fm.pop("date")
            changes.append("renamed date → date-created")
        elif "created" in fm and "date-created" not in fm:
            fm["date-created"] = fm.pop("created")
            changes.append("renamed created → date-created")

        # Fix: add date-created if still missing
        if "date-created" not in fm:
            git_date = git_creation_date(filepath, content_dir)
            if git_date:
                fm["date-created"] = f"{git_date}T00:00:00"
                changes.append(f"added date-created from git: {git_date}")

        # Fix: deprecated author → authors
        if "author" in fm and "authors" not in fm:
            author = fm.pop("author")
            fm["authors"] = [author] if isinstance(author, str) else author
            changes.append("renamed author → authors")

        # Fix: deprecated updated → date-updated
        if "updated" in fm and "date-updated" not in fm:
            fm["date-updated"] = fm.pop("updated")
            changes.append("renamed updated → date-updated")

        # Fix: deprecated kind → type
        if "kind" in fm and "type" not in fm:
            fm["type"] = fm.pop("kind")
            changes.append("renamed kind → type")

        # Fix: deprecated id field
        if "id" in fm:
            fm.pop("id")
            changes.append("removed deprecated id field")

        if not changes:
            return 0, []

        new_fm_text = rebuild_frontmatter(fm)
        new_content = f"---\n{new_fm_text}\n---\n{body}"

    if not dry_run:
        filepath.write_text(new_content)

    return len(changes), changes


def main():
    parser = argparse.ArgumentParser(description="Enrich triage frontmatter")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing")
    parser.add_argument("--batch", type=int, default=0,
                        help="Limit to N files (0 = unlimited)")
    parser.add_argument("path_filter", nargs="?", default="",
                        help="Only process files matching this path prefix")
    args = parser.parse_args()

    content_dir = find_content_dir()
    triage_dir = content_dir / "triage"
    print(f"Enriching triage at: {triage_dir}")
    if args.dry_run:
        print("DRY RUN — no files will be modified\n")

    skip_dirs = {".trash", ".obsidian"}
    files_changed = 0
    total_changes = 0
    files_processed = 0

    for root, dirs, files in os.walk(triage_dir):
        dirs[:] = sorted(d for d in dirs if d not in skip_dirs)
        for f in sorted(files):
            if not f.endswith(".md"):
                continue

            filepath = Path(root) / f
            rel = str(filepath.relative_to(triage_dir))

            if args.path_filter and not rel.startswith(args.path_filter):
                continue

            if args.batch and files_processed >= args.batch:
                break

            n_changes, descriptions = enrich_file(filepath, content_dir,
                                                   dry_run=args.dry_run)
            files_processed += 1

            if n_changes > 0:
                files_changed += 1
                total_changes += n_changes
                prefix = "[DRY] " if args.dry_run else ""
                print(f"  {prefix}{rel}:")
                for d in descriptions:
                    print(f"    - {d}")

        if args.batch and files_processed >= args.batch:
            break

    print(f"\n{'Would change' if args.dry_run else 'Changed'}: "
          f"{files_changed} files, {total_changes} total changes "
          f"(processed {files_processed} files)")


if __name__ == "__main__":
    main()
