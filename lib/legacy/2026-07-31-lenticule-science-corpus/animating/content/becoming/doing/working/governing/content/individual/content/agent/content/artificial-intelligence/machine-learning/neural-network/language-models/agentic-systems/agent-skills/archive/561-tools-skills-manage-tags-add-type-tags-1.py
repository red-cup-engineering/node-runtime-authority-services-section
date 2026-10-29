#!/usr/bin/env python3
"""Add type: frontmatter field to documents based on their directory location.

Mapping:
  */terms/         -> type: term
  */people/        -> type: person
  */concepts/      -> type: concept
  */schools/       -> type: school
  */topics/        -> type: topic
  */curricula/     -> type: lesson
  */text/          -> type: text
  */skills/        -> type: skill
  */questions/     -> type: question
  personal/writing/babbles/          -> type: babble
  personal/writing/letters-to-the-web/  -> type: letter
  index.md (any)   -> type: index

When multiple types apply, the most specific wins:
  term > concept > person > school > question > lesson > text > babble > letter > skill > topic > index

Does NOT touch files that already have a type: field.
Does NOT touch files in private/, meta/, .obsidian/.
Preserves all existing frontmatter; only adds the type: field.
"""

import os
import re
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")

# Directories to skip entirely
SKIP_DIRS = {"private", "meta", ".obsidian"}

# Type priority: more specific first
TYPE_PRIORITY = [
    "term", "concept", "person", "school",
    "question", "lesson", "text", "letter", "babble",
    "skill", "topic", "index",
]


def determine_type(filepath, filename):
    """Determine the appropriate type for a file based on its path.

    Returns the most specific type string, or None if no type applies.
    """
    types = []

    # Normalize path
    rel_path = os.path.relpath(filepath, CONTENT_DIR).replace(os.sep, "/")

    # index.md gets type: index
    if filename == "index.md":
        types.append("index")

    # Check for specific personal/writing paths first
    if "personal/writing/babbles" in rel_path:
        types.append("babble")
    elif "personal/writing/letters-to-the-web" in rel_path:
        types.append("letter")

    # Directory-based types
    dir_path = os.path.dirname(filepath)
    dir_parts = dir_path.replace(os.sep, "/").split("/")

    dir_type_map = {
        "terms": "term",
        "people": "person",
        "concepts": "concept",
        "schools": "school",
        "questions": "question",
        "topics": "topic",
        "curricula": "lesson",
        "text": "text",
        "skills": "skill",
    }

    for part in dir_parts:
        if part in dir_type_map:
            t = dir_type_map[part]
            if t not in types:
                types.append(t)

    if not types:
        return None

    # Return the most specific type
    for priority in TYPE_PRIORITY:
        if priority in types:
            return priority
    return types[0]


def has_type_field(content):
    """Check if the file already has a type: frontmatter field."""
    if not content.startswith("---"):
        return True  # No frontmatter, treat as already handled
    end = content.find("\n---", 3)
    if end < 0:
        return True
    fm = content[4:end]
    return bool(re.search(r'^type:\s', fm, re.MULTILINE))


def add_type_field(content, type_value):
    """Add type: field to frontmatter after date-created (or before tags)."""
    if not content.startswith("---"):
        return content, False
    end = content.find("\n---", 3)
    if end < 0:
        return content, False

    fm = content[4:end]
    body = content[end + 4:]

    # Insert after date-created if present
    date_match = re.search(r'^date-created:.*\n', fm, re.MULTILINE)
    if date_match:
        insert_pos = date_match.end()
        new_fm = fm[:insert_pos] + f"type: {type_value}\n" + fm[insert_pos:]
    else:
        # Insert before tags if present
        tags_match = re.search(r'^tags:', fm, re.MULTILINE)
        if tags_match:
            new_fm = fm[:tags_match.start()] + f"type: {type_value}\n" + fm[tags_match.start():]
        else:
            # Append at end
            new_fm = fm.rstrip("\n") + f"\ntype: {type_value}\n"

    return "---\n" + new_fm + "\n---" + body, True


def process_file(filepath, filename):
    """Process a single file. Returns the type added, or None."""
    type_value = determine_type(filepath, filename)
    if not type_value:
        return None

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if has_type_field(content):
        return None

    new_content, changed = add_type_field(content, type_value)
    if not changed:
        return None

    with open(filepath, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)

    return type_value


def main():
    counts = {}
    total_files = 0

    for root, dirs, files in os.walk(CONTENT_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for f in files:
            if not f.endswith(".md"):
                continue
            filepath = os.path.join(root, f)
            added = process_file(filepath, f)
            if added:
                total_files += 1
                counts[added] = counts.get(added, 0) + 1

    print("Type fields added:")
    print(f"{'=' * 50}")
    for t in sorted(counts.keys()):
        print(f"  type: {t} -> {counts[t]} files")
    print(f"{'=' * 50}")
    print(f"Total files updated: {total_files}")


if __name__ == "__main__":
    main()
