#!/usr/bin/env python3
"""extract-formal-definitions.py — Extract formal definitions from triage files via ollama.

For each file, extracts the concept name, formal definition, key formula,
and relevance to method/practice/endeavor theory. Outputs JSON lines.

Usage:
    python3 scripts/extract-formal-definitions.py --dir "collapse dynamics" --limit 20
    python3 scripts/extract-formal-definitions.py --files file1.md file2.md
    python3 scripts/extract-formal-definitions.py --relevance-filter method
"""

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))
import local_llm  # noqa: E402

for candidate in [REPO_ROOT / "content", REPO_ROOT.parent / "content"]:
    if candidate.is_dir() and (candidate / "triage").is_dir():
        CONTENT_DIR = candidate
        break
else:
    print("ERROR: Could not find content/triage/", file=sys.stderr)
    sys.exit(1)

TRIAGE_DIR = CONTENT_DIR / "triage"
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".obsidian", ".trash"}

EXTRACT_PROMPT = """Extract the formal definition from this file as a structured summary. Output ONLY a JSON object with fields:
- "concept": the name of the concept defined
- "definition": the formal definition in 1-2 sentences
- "formula": the key formula if any (as plain text), or "" if none
- "relevance_to_method": one sentence on how this concept could describe an aspect of how organized efforts work — specifically about method (conventions/specifications), practice (doing of work), closure conditions, governance, or organizational structure. If no clear relevance, set to "none".

Output ONLY the JSON object, no markdown fences or explanation.

File content:
{content}
"""


def extract_definition(filepath, model=DEFAULT_MODEL):
    """Ask ollama to extract a formal definition from a file."""
    rel_path = str(filepath.relative_to(CONTENT_DIR))
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")[:4000]
    except Exception:
        return None

    if len(content.strip()) < 20:
        return None

    prompt = EXTRACT_PROMPT.format(content=content)

    result = local_llm.complete(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        temperature=0.1,
        max_tokens=300,
    )

    if result["error"]:
        return {"path": rel_path, "error": result["error"]}

    response_text = result["response"].strip()

    # Parse JSON from response
    try:
        text = response_text
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text.strip())
        parsed["path"] = rel_path
        return parsed
    except (json.JSONDecodeError, ValueError):
        return {"path": rel_path, "error": f"parse: {response_text[:80]}"}


def collect_files(search_dir):
    """Collect all .md files."""
    files = []
    for root, dirs, filenames in os.walk(search_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in sorted(filenames):
            if f.endswith(".md") and f != "index.md":
                files.append(Path(root) / f)
    return files


def main():
    parser = argparse.ArgumentParser(
        description="Extract formal definitions from triage files via ollama"
    )
    parser.add_argument("--dir", default="",
                        help="Subdirectory of triage/ to process")
    parser.add_argument("--files", nargs="*",
                        help="Specific files to process")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max files to process (0=all)")
    parser.add_argument("--relevance-filter", default="",
                        help="Only output entries where relevance contains this word")
    parser.add_argument("--model", default="")
    args = parser.parse_args()

    active_model = args.model or local_llm.suggest_model("extraction")

    if args.files:
        files = [Path(f) for f in args.files]
    elif args.dir:
        search_dir = TRIAGE_DIR / args.dir
        if not search_dir.is_dir():
            print(f"ERROR: Not a directory: {search_dir}", file=sys.stderr)
            sys.exit(1)
        files = collect_files(search_dir)
    else:
        files = collect_files(TRIAGE_DIR)

    if args.limit > 0:
        files = files[:args.limit]

    print(f"Extracting definitions from {len(files)} files", file=sys.stderr)

    results = []
    for i, filepath in enumerate(files):
        result = extract_definition(filepath, model=active_model)
        if result and "error" not in result:
            relevance = result.get("relevance_to_method", "none")
            if args.relevance_filter:
                if args.relevance_filter.lower() not in relevance.lower():
                    continue
            results.append(result)
            print(json.dumps(result))
        if (i + 1) % 10 == 0:
            print(f"  ... {i + 1}/{len(files)}", file=sys.stderr)

    print(f"\n{len(results)} definitions extracted", file=sys.stderr)


if __name__ == "__main__":
    main()
