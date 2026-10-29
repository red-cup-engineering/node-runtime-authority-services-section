#!/usr/bin/env python3
"""Move a file within the vault and update all internal references to it.

Handles both markdown links [text](relative/path.md) and wikilinks [[stem]].

Usage:
    python relocate-file.py <source> <destination>
    python relocate-file.py <source> <destination> --dry-run
    python relocate-file.py <source> <destination> --vault-root content/

Examples:
    python relocate-file.py content/math/old-topic.md content/math/topics/new-topic.md
    python relocate-file.py content/bio/cell.md content/biology/topics/cell.md --dry-run
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(#[^\]|]*)?(\|[^\]]*)?\]\]")
MD_LINK_RE = re.compile(r"(\[[^\]]*\]\()([^)#]+\.md)(#[^)]*)?\)")

IGNORE_DIRS = {".obsidian", "private", ".git", "node_modules"}


def find_all_md_files(vault_root: Path) -> list[Path]:
    """Collect every .md file in the vault, skipping ignored directories."""
    results = []
    for md_file in vault_root.rglob("*.md"):
        rel = md_file.relative_to(vault_root)
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        results.append(md_file)
    return results


def resolve_md_link_target(link_target: str, source_file: Path) -> Path | None:
    """Resolve a relative markdown link target to an absolute path."""
    try:
        resolved = (source_file.parent / link_target).resolve()
        return resolved
    except (ValueError, OSError):
        return None


def compute_relative_path(from_file: Path, to_file: Path) -> str:
    """Compute the relative path from one file's directory to another file."""
    from_dir = from_file.parent
    return os.path.relpath(to_file, from_dir).replace("\\", "/")


def update_md_links(
    content: str,
    source_file: Path,
    old_abs: Path,
    new_abs: Path,
) -> tuple[str, int]:
    """Rewrite markdown links whose resolved target matches old_abs."""
    count = 0

    def replacer(match: re.Match) -> str:
        nonlocal count
        prefix = match.group(1)
        link_target = match.group(2)
        fragment = match.group(3) or ""

        resolved = resolve_md_link_target(link_target, source_file)
        if resolved is None:
            return match.group(0)

        try:
            if resolved.resolve() == old_abs.resolve():
                new_rel = compute_relative_path(source_file, new_abs)
                count += 1
                return f"{prefix}{new_rel}{fragment})"
        except (ValueError, OSError):
            pass

        return match.group(0)

    updated = MD_LINK_RE.sub(replacer, content)
    return updated, count


def update_wikilinks(
    content: str,
    old_stem: str,
    new_stem: str,
) -> tuple[str, int]:
    """Rewrite wikilinks that reference the old stem to use the new stem."""
    if old_stem == new_stem:
        return content, 0

    count = 0

    def replacer(match: re.Match) -> str:
        nonlocal count
        target = match.group(1)
        fragment = match.group(2) or ""
        display = match.group(3) or ""

        if target.strip().lower() == old_stem.lower():
            count += 1
            return f"[[{new_stem}{fragment}{display}]]"

        return match.group(0)

    updated = WIKILINK_RE.sub(replacer, content)
    return updated, count


def relocate_file(
    source: Path,
    destination: Path,
    vault_root: Path,
    dry_run: bool = False,
) -> dict:
    """Move source to destination and update all vault references."""
    source = source.resolve()
    destination = destination.resolve()
    vault_root = vault_root.resolve()

    if not source.exists():
        print(f"Error: source file does not exist: {source}", file=sys.stderr)
        sys.exit(1)

    if not source.suffix == ".md":
        print(f"Error: source is not a markdown file: {source}", file=sys.stderr)
        sys.exit(1)

    if destination.exists():
        print(f"Error: destination already exists: {destination}", file=sys.stderr)
        sys.exit(1)

    old_stem = source.stem
    new_stem = destination.stem

    # Collect all md files before moving
    all_md = find_all_md_files(vault_root)

    # Move the file
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))

    files_modified = 0
    links_updated = 0

    # Update references in every other markdown file
    for md_file in all_md:
        md_abs = md_file.resolve()
        if md_abs == source:
            continue  # skip the file being moved

        try:
            content = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        new_content = content
        file_link_count = 0

        # Update markdown links
        updated, count = update_md_links(new_content, md_file, source, destination)
        new_content = updated
        file_link_count += count

        # Update wikilinks if the stem changed
        if old_stem != new_stem:
            updated, count = update_wikilinks(new_content, old_stem, new_stem)
            new_content = updated
            file_link_count += count

        if new_content != content:
            files_modified += 1
            links_updated += file_link_count
            if not dry_run:
                md_file.write_text(new_content, encoding="utf-8")

    # Also update internal links within the moved file itself
    if destination.exists() or dry_run:
        moved_file = destination if not dry_run else source
        try:
            content = moved_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            content = None

        if content is not None:
            new_content = content
            internal_count = 0

            # Rewrite relative links inside the moved file to account for
            # its new directory location
            def rewrite_internal(match: re.Match) -> str:
                nonlocal internal_count
                prefix = match.group(1)
                link_target = match.group(2)
                fragment = match.group(3) or ""

                # Resolve relative to OLD location
                resolved = resolve_md_link_target(link_target, source)
                if resolved is None or not resolved.exists():
                    return match.group(0)

                # Compute new relative path from new location
                new_rel = compute_relative_path(destination, resolved)
                if new_rel != link_target:
                    internal_count += 1
                    return f"{prefix}{new_rel}{fragment})"

                return match.group(0)

            new_content = MD_LINK_RE.sub(rewrite_internal, new_content)

            if new_content != content:
                files_modified += 1
                links_updated += internal_count
                if not dry_run:
                    destination.write_text(new_content, encoding="utf-8")

    return {
        "source": str(source),
        "destination": str(destination),
        "files_modified": files_modified,
        "links_updated": links_updated,
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Move a file and update all vault references to it."
    )
    parser.add_argument("source", help="Current path of the file to move")
    parser.add_argument("destination", help="New path for the file")
    parser.add_argument(
        "--vault-root",
        default="content",
        help="Root directory of the vault (default: content/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing any files",
    )

    args = parser.parse_args()

    source = Path(args.source)
    destination = Path(args.destination)
    vault_root = Path(args.vault_root)

    if not vault_root.is_dir():
        print(f"Error: vault root is not a directory: {vault_root}", file=sys.stderr)
        sys.exit(1)

    result = relocate_file(source, destination, vault_root, args.dry_run)

    mode = "DRY RUN" if result["dry_run"] else "APPLIED"
    print(f"[{mode}] Relocated file:")
    print(f"  From: {result['source']}")
    print(f"  To:   {result['destination']}")
    print(f"  Files modified: {result['files_modified']}")
    print(f"  Links updated:  {result['links_updated']}")


if __name__ == "__main__":
    main()
