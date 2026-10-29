#!/usr/bin/env python3
"""Check that a skill meets ASR quality standards.

Validates a SKILL.md against:
  1. Signal-dispatch manifest (required fields, types)
  2. Semantic frontmatter (defines, requires, part-of, etc.)
  3. Colocated code (scripts alongside SKILL.md)
  4. Registry entry (skill appears in registry.md)
  5. Body references (does the body reference concrete files/commands?)

Usage:
  python check-skill.py improve-skill          # check by skill id
  python check-skill.py .claude/skills/stabilize/SKILL.md  # check by path
  python check-skill.py --all                  # check all skills
  python check-skill.py --json improve-skill   # output as JSON
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent

MANIFEST_REQUIRED = {"name", "description", "kind"}
MANIFEST_OPTIONAL = {"version", "runtime", "triggers", "inputs",
                     "outputs", "region", "dependencies", "scopes"}
VALID_KINDS = {"operational", "learn", "meta"}
SEMANTIC_FIELDS = {"defines", "requires", "part-of", "extends",
                   "questions", "addresses", "cites", "teaches"}
CODE_EXTENSIONS = {".py", ".sh", ".ts", ".js"}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract frontmatter fields and body from a SKILL.md."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text

    fm = {}
    for line in lines[1:end]:
        match = re.match(r'^([a-zA-Z_-]+)\s*:', line)
        if match and not line.startswith(" ") and not line.startswith("\t"):
            fm[match.group(1)] = line[match.end():].strip()

    body = "\n".join(lines[end + 1:])
    return fm, body


def find_skill(skill_ref: str) -> Path | None:
    """Resolve a skill reference to a SKILL.md path."""
    # Direct path
    p = Path(skill_ref)
    if p.exists() and p.name == "SKILL.md":
        return p

    # Search content for skill by id
    content = REPO_ROOT / "content"
    for match in content.rglob(f"**/skills/{skill_ref}/SKILL.md"):
        return match

    return None


def check_skill(skill_path: Path) -> dict:
    """Run all checks on a single skill."""
    result = {
        "path": str(skill_path.relative_to(REPO_ROOT)),
        "checks": [],
        "passed": 0,
        "failed": 0,
        "warnings": 0,
    }

    text = skill_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    skill_dir = skill_path.parent
    skill_id = skill_dir.name

    # --- Check 1: Manifest required fields ---
    missing_required = MANIFEST_REQUIRED - set(fm.keys())
    if missing_required:
        result["checks"].append({
            "name": "manifest-required",
            "status": "FAIL",
            "message": f"Missing required fields: {', '.join(sorted(missing_required))}"
        })
        result["failed"] += 1
    else:
        result["checks"].append({
            "name": "manifest-required",
            "status": "PASS",
            "message": "All required manifest fields present"
        })
        result["passed"] += 1

    # --- Check 1b: Kind enum validation ---
    kind_val = fm.get("kind", "")
    if kind_val and kind_val not in VALID_KINDS:
        result["checks"].append({
            "name": "kind-enum",
            "status": "FAIL",
            "message": f"kind '{kind_val}' not in {{operational, learn, meta}}"
        })
        result["failed"] += 1
    elif kind_val:
        result["checks"].append({
            "name": "kind-enum",
            "status": "PASS",
            "message": f"kind: {kind_val}"
        })
        result["passed"] += 1

    # --- Check 2: Manifest optional fields ---
    present_optional = MANIFEST_OPTIONAL & set(fm.keys())
    missing_optional = MANIFEST_OPTIONAL - set(fm.keys())
    if missing_optional:
        result["checks"].append({
            "name": "manifest-optional",
            "status": "WARN",
            "message": f"Missing optional fields: {', '.join(sorted(missing_optional))}"
        })
        result["warnings"] += 1
    else:
        result["checks"].append({
            "name": "manifest-optional",
            "status": "PASS",
            "message": "All optional manifest fields present"
        })
        result["passed"] += 1

    # --- Check 3: Semantic frontmatter ---
    present_semantic = SEMANTIC_FIELDS & set(fm.keys())
    if not present_semantic:
        result["checks"].append({
            "name": "semantic-frontmatter",
            "status": "FAIL",
            "message": "No semantic relation fields (defines, requires, part-of, extends, questions, addresses)"
        })
        result["failed"] += 1
    else:
        missing_semantic = SEMANTIC_FIELDS - present_semantic
        result["checks"].append({
            "name": "semantic-frontmatter",
            "status": "PASS",
            "message": f"Has: {', '.join(sorted(present_semantic))}. Missing: {', '.join(sorted(missing_semantic)) if missing_semantic else 'none'}"
        })
        result["passed"] += 1

    # --- Check 4: Colocated code ---
    code_files = []
    for f in skill_dir.iterdir():
        if f.is_file() and f.suffix in CODE_EXTENSIONS and f.name != "SKILL.md":
            code_files.append(f.name)
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        for f in scripts_dir.iterdir():
            if f.is_file() and f.suffix in CODE_EXTENSIONS:
                code_files.append(f"scripts/{f.name}")

    runtime = fm.get("runtime", "inference")
    if runtime == "script" and not code_files:
        result["checks"].append({
            "name": "colocated-code",
            "status": "FAIL",
            "message": "runtime: script but no code files found alongside SKILL.md"
        })
        result["failed"] += 1
    elif code_files:
        result["checks"].append({
            "name": "colocated-code",
            "status": "PASS",
            "message": f"Code files: {', '.join(code_files)}"
        })
        result["passed"] += 1
    else:
        result["checks"].append({
            "name": "colocated-code",
            "status": "WARN",
            "message": "No colocated code. Consider whether this skill should have scripts."
        })
        result["warnings"] += 1

    # --- Check 5: Registry entry ---
    registry_path = REPO_ROOT / ".claude" / "skills" / "registry.md"
    if registry_path.exists():
        registry_text = registry_path.read_text(encoding="utf-8")
        if skill_id in registry_text:
            result["checks"].append({
                "name": "registry-entry",
                "status": "PASS",
                "message": f"'{skill_id}' found in registry.md"
            })
            result["passed"] += 1
        else:
            result["checks"].append({
                "name": "registry-entry",
                "status": "WARN",
                "message": f"'{skill_id}' not found in registry.md"
            })
            result["warnings"] += 1
    else:
        result["checks"].append({
            "name": "registry-entry",
            "status": "WARN",
            "message": "registry.md not found"
        })
        result["warnings"] += 1

    # --- Check 6: Body references concrete operations ---
    has_command = bool(re.search(r'`[a-z].*\.(py|sh|ts)`|`python |`node |`bash ', body))
    has_file_ref = bool(re.search(r'`[a-zA-Z._/]+\.(md|py|ts|ttl|lean|json)`', body))
    has_skill_ref = bool(re.search(r'`/[a-z]', body))

    if has_command or has_file_ref or has_skill_ref:
        refs = []
        if has_command:
            refs.append("commands")
        if has_file_ref:
            refs.append("file paths")
        if has_skill_ref:
            refs.append("skill invocations")
        result["checks"].append({
            "name": "body-concreteness",
            "status": "PASS",
            "message": f"Body references: {', '.join(refs)}"
        })
        result["passed"] += 1
    else:
        result["checks"].append({
            "name": "body-concreteness",
            "status": "WARN",
            "message": "Body has no references to concrete files, commands, or skills"
        })
        result["warnings"] += 1

    return result


def main():
    parser = argparse.ArgumentParser(description="Check skill quality")
    parser.add_argument("skill", nargs="?", help="Skill id or path")
    parser.add_argument("--all", action="store_true", help="Check all core skills")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if not args.skill and not args.all:
        parser.print_help()
        sys.exit(1)

    results = []

    if args.all:
        content_dir = REPO_ROOT / "content"
        for skill_file in sorted(content_dir.rglob("**/skills/*/SKILL.md")):
            results.append(check_skill(skill_file))
    else:
        path = find_skill(args.skill)
        if path is None:
            print(f"Skill not found: {args.skill}", file=sys.stderr)
            sys.exit(1)
        results.append(check_skill(path))

    if args.json:
        print(json.dumps({"results": results}, indent=2))
    else:
        for r in results:
            total = r["passed"] + r["failed"] + r["warnings"]
            print(f"\n  {r['path']}  [{r['passed']}/{total} pass, {r['failed']} fail, {r['warnings']} warn]")
            for c in r["checks"]:
                marker = {"PASS": "+", "FAIL": "x", "WARN": "!"}[c["status"]]
                print(f"    {marker} {c['name']}: {c['message']}")

        total_pass = sum(r["passed"] for r in results)
        total_fail = sum(r["failed"] for r in results)
        total_warn = sum(r["warnings"] for r in results)
        print(f"\n  Summary: {total_pass} pass, {total_fail} fail, {total_warn} warn across {len(results)} skills")


if __name__ == "__main__":
    main()
