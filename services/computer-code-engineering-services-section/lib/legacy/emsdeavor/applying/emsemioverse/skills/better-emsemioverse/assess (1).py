#!/usr/bin/env python3
"""Assess how well the repository implements the ASR specification.

Produces a structured gap report comparing the actual repository state
against what the ASR specs require. Each check maps to a specific ASR
specification section.

Usage:
  python assess.py                    # full assessment
  python assess.py --json             # output as JSON
  python assess.py --check manifests  # run one check only
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent

# ---------------------------------------------------------------------------
# Check 1: Directory Organization
# Spec: content/technology/specifications/agential-semioverse-repository/directory-organization/
# Every directory with content files should have an index.md.
# ---------------------------------------------------------------------------

def check_directory_organization(content_root: Path) -> dict:
    """Find published content directories missing an index.md."""
    missing = []
    # Directories that are not published or are special
    skip = {"private", "meta", "slop", "triage", ".obsidian", "assets", "tags"}

    for dirpath, dirnames, filenames in os.walk(content_root):
        rel = Path(dirpath).relative_to(content_root)
        parts = rel.parts

        # Skip special directories
        if parts and parts[0] in skip:
            dirnames.clear()
            continue

        # Skip hidden directories
        if any(p.startswith(".") for p in parts):
            dirnames.clear()
            continue

        # A directory with .md files (other than index.md) but no index.md
        md_files = [f for f in filenames if f.endswith(".md") and f != "index.md"]
        has_index = "index.md" in filenames
        has_subdirs = len(dirnames) > 0

        if (md_files or has_subdirs) and not has_index and str(rel) != ".":
            missing.append(str(rel))

    return {
        "check": "directory-organization",
        "spec": "directory-organization/index.md",
        "description": "Published directories with content but no index.md",
        "count": len(missing),
        "items": sorted(missing),
    }


# ---------------------------------------------------------------------------
# Check 2: Skill Manifests
# Spec: theory/skill-manifests.md, theory/signal-dispatch.md Section 5
# All SKILL.md files should have valid signal-dispatch frontmatter.
# ---------------------------------------------------------------------------

def check_skill_manifests(repo_root: Path) -> dict:
    """Check skill manifest coverage and validity."""
    required_fields = {"id", "description", "region"}
    core_skills_dir = repo_root / ".claude" / "skills"
    content_dir = repo_root / "content"

    results = {"core": {"total": 0, "valid": 0, "missing_fields": []},
               "embedded": {"total": 0, "valid": 0, "missing_fields": []}}

    def check_skill(skill_path: Path, category: str):
        results[category]["total"] += 1
        try:
            text = skill_path.read_text(encoding="utf-8")
        except Exception:
            return

        # Extract frontmatter
        lines = text.split("\n")
        if not lines or lines[0].strip() != "---":
            results[category]["missing_fields"].append(
                {"path": str(skill_path.relative_to(repo_root)), "missing": list(required_fields)})
            return

        end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end = i
                break
        if end is None:
            return

        fm_text = "\n".join(lines[1:end])
        present = set()
        for field in required_fields:
            if re.search(rf"^{field}\s*:", fm_text, re.MULTILINE):
                present.add(field)

        missing = required_fields - present
        if not missing:
            results[category]["valid"] += 1
        else:
            results[category]["missing_fields"].append(
                {"path": str(skill_path.relative_to(repo_root)),
                 "missing": sorted(missing)})

    # Core skills
    if core_skills_dir.exists():
        for d in sorted(core_skills_dir.iterdir()):
            skill_file = d / "SKILL.md"
            if d.is_dir() and skill_file.exists():
                check_skill(skill_file, "core")

    # Content-embedded skills
    if content_dir.exists():
        for skill_file in sorted(content_dir.rglob("**/skills/*/SKILL.md")):
            check_skill(skill_file, "embedded")

    return {
        "check": "skill-manifests",
        "spec": "theory/skill-manifests.md",
        "description": "SKILL.md files with valid signal-dispatch frontmatter",
        "core_total": results["core"]["total"],
        "core_valid": results["core"]["valid"],
        "embedded_total": results["embedded"]["total"],
        "embedded_valid": results["embedded"]["valid"],
        "invalid_skills": results["core"]["missing_fields"] + results["embedded"]["missing_fields"],
    }


# ---------------------------------------------------------------------------
# Check 3: Semantic Frontmatter
# Spec: semantic-frontmatter.md
# Files should have typed relation fields (defines, requires, etc.)
# ---------------------------------------------------------------------------

RELATION_FIELDS = {"defines", "cites", "teaches", "requires", "part-of",
                   "extends", "questions", "addresses"}

def check_semantic_frontmatter(content_root: Path) -> dict:
    """Count files with typed semantic relation fields."""
    skip = {"private", "meta", "slop", "triage", ".obsidian"}
    total_files = 0
    files_with_relations = 0
    field_counts = {f: 0 for f in RELATION_FIELDS}
    files_with_type = 0

    for md_file in content_root.rglob("*.md"):
        rel = md_file.relative_to(content_root)
        if any(p in skip for p in rel.parts):
            continue
        if any(p.startswith(".") for p in rel.parts):
            continue

        total_files += 1
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        lines = text.split("\n")
        if not lines or lines[0].strip() != "---":
            continue

        end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end = i
                break
        if end is None:
            continue

        fm_text = "\n".join(lines[1:end])

        has_relation = False
        for field in RELATION_FIELDS:
            if re.search(rf"^{field}\s*:", fm_text, re.MULTILINE):
                field_counts[field] += 1
                has_relation = True

        if has_relation:
            files_with_relations += 1

        if re.search(r"^type\s*:", fm_text, re.MULTILINE):
            files_with_type += 1

    return {
        "check": "semantic-frontmatter",
        "spec": "semantic-frontmatter.md",
        "description": "Published files with typed semantic relation fields",
        "total_published_files": total_files,
        "files_with_type_field": files_with_type,
        "files_with_any_relation": files_with_relations,
        "relation_coverage_pct": round(100 * files_with_relations / max(total_files, 1), 1),
        "field_counts": field_counts,
    }


# ---------------------------------------------------------------------------
# Check 4: Colocated Formal Artifacts
# CLAUDE.md: files may have .ttl, .shapes.ttl, .lean, .py, .json
# ---------------------------------------------------------------------------

ARTIFACT_EXTENSIONS = {".ttl", ".shapes.ttl", ".lean", ".py", ".json"}

def check_formal_artifacts(content_root: Path) -> dict:
    """Count files with colocated formal artifacts."""
    skip = {"private", "meta", "slop", "triage", ".obsidian"}
    dirs_with_md = 0
    dirs_with_artifacts = 0
    artifact_counts = {ext: 0 for ext in sorted(ARTIFACT_EXTENSIONS)}

    for dirpath, dirnames, filenames in os.walk(content_root):
        rel = Path(dirpath).relative_to(content_root)
        if any(p in skip for p in rel.parts):
            dirnames.clear()
            continue
        if any(p.startswith(".") for p in rel.parts):
            dirnames.clear()
            continue

        has_md = any(f.endswith(".md") for f in filenames)
        if not has_md:
            continue

        dirs_with_md += 1
        has_artifact = False
        for f in filenames:
            for ext in ARTIFACT_EXTENSIONS:
                if f.endswith(ext) and not f.endswith(".md"):
                    artifact_counts[ext] += 1
                    has_artifact = True
        if has_artifact:
            dirs_with_artifacts += 1

    return {
        "check": "formal-artifacts",
        "spec": "CLAUDE.md (Colocated Formal Artifacts)",
        "description": "Content directories with colocated formal artifacts (.ttl, .lean, .py, .json)",
        "dirs_with_content": dirs_with_md,
        "dirs_with_artifacts": dirs_with_artifacts,
        "artifact_coverage_pct": round(100 * dirs_with_artifacts / max(dirs_with_md, 1), 1),
        "by_type": artifact_counts,
    }


# ---------------------------------------------------------------------------
# Check 5: Wikilink Inventory
# Wikilinks are emsenn's flags for pages that need to be created.
# Each [[target]] represents a thing that should exist but doesn't yet.
# This check counts them as pending creation tasks, not errors.
# ---------------------------------------------------------------------------

def check_linking(content_root: Path) -> dict:
    """Count wikilinks (pending page creation flags) in published content."""
    skip = {"private", "meta", "slop", "triage", ".obsidian"}
    wikilink_pattern = re.compile(r"\[\[([^\]]+)\]\]")
    mdlink_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+\.md[^)]*)\)")

    total_wikilinks = 0
    total_mdlinks = 0
    files_with_wikilinks = []

    for md_file in content_root.rglob("*.md"):
        rel = md_file.relative_to(content_root)
        if any(p in skip for p in rel.parts):
            continue
        if any(p.startswith(".") for p in rel.parts):
            continue

        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # Skip frontmatter
        lines = text.split("\n")
        if lines and lines[0].strip() == "---":
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    text = "\n".join(lines[i+1:])
                    break

        wikilinks = wikilink_pattern.findall(text)
        mdlinks = mdlink_pattern.findall(text)

        if wikilinks:
            total_wikilinks += len(wikilinks)
            files_with_wikilinks.append({
                "path": str(rel),
                "count": len(wikilinks),
            })
        total_mdlinks += len(mdlinks)

    return {
        "check": "wikilinks",
        "spec": "CLAUDE.md (Linking)",
        "description": "Wikilinks are emsenn's flags for pages that need creation. Each is a pending thing.",
        "total_markdown_links": total_mdlinks,
        "total_wikilinks": total_wikilinks,
        "files_with_wikilinks": len(files_with_wikilinks),
        "pending_creations": sorted(files_with_wikilinks, key=lambda x: -x["count"])[:10],
    }


# ---------------------------------------------------------------------------
# Check 6: Domain ASR Coverage
# Which discipline directories have domain-specific ASR specs?
# Pattern: {discipline}/specifications/{discipline}-agential-semioverse-repository/
# ---------------------------------------------------------------------------

# Directories that are not discipline modules
NON_DISCIPLINE = {
    "assets", "general", "personal", "private", "meta", "slop", "triage",
    "tags", "writing", ".obsidian",
}

def check_domain_asr_coverage(content_root: Path) -> dict:
    """Check which discipline directories have domain-specific ASR specs."""
    disciplines = []

    for entry in sorted(content_root.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name in NON_DISCIPLINE or name.startswith("."):
            continue
        # Count published .md files in the discipline
        md_count = sum(1 for _ in entry.rglob("*.md"))
        disciplines.append({"name": name, "files": md_count})

    covered = []
    uncovered = []
    for d in disciplines:
        name = d["name"]
        spec_dir = content_root / name / "specifications"
        has_asr = False
        if spec_dir.exists():
            for sub in spec_dir.iterdir():
                if sub.is_dir() and sub.name.endswith("-agential-semioverse-repository"):
                    index = sub / "index.md"
                    ontology = sub / "ontology.ttl"
                    shapes = sub / "shapes.ttl"
                    has_asr = index.exists()
                    d["has_ontology"] = ontology.exists()
                    d["has_shapes"] = shapes.exists()
                    break
        if has_asr:
            covered.append(d)
        else:
            uncovered.append(d)

    # Sort uncovered by file count descending — prioritize larger disciplines
    uncovered.sort(key=lambda x: -x["files"])

    return {
        "check": "domain-asr-coverage",
        "spec": "Domain-specific ASR specifications",
        "description": "Discipline directories with domain-specific ASR specs (ontology + shapes + spec)",
        "total_disciplines": len(disciplines),
        "covered": len(covered),
        "uncovered": len(uncovered),
        "coverage_pct": round(100 * len(covered) / max(len(disciplines), 1), 1),
        "covered_disciplines": covered,
        "uncovered_disciplines": uncovered,
    }


# ---------------------------------------------------------------------------
# Check 7: Validation Rule Coverage
# Which domain ASR specs have corresponding rules in validate-content.py?
# ---------------------------------------------------------------------------

def check_validation_coverage(content_root: Path) -> dict:
    """Check which domain ASR specs have validation rules in validate-content.py."""
    validate_script = (
        content_root / "technology" / "specifications"
        / "agential-semioverse-repository" / "scripts" / "validate-content.py"
    )
    if not validate_script.exists():
        return {
            "check": "validation-coverage",
            "spec": "scripts/validate-content.py",
            "description": "validate-content.py not found",
            "total_domain_specs": 0,
            "with_validation_rules": 0,
        }

    script_text = validate_script.read_text(encoding="utf-8")

    # Find domain ASR specs
    specs = []
    for entry in sorted(content_root.iterdir()):
        if not entry.is_dir() or entry.name in NON_DISCIPLINE or entry.name.startswith("."):
            continue
        spec_dir = entry / "specifications"
        if not spec_dir.exists():
            continue
        for sub in spec_dir.iterdir():
            if sub.is_dir() and sub.name.endswith("-agential-semioverse-repository"):
                if (sub / "index.md").exists():
                    specs.append(entry.name)
                break

    # Check which have rules in validate-content.py
    # Rules follow pattern: {PREFIX}_RULES = { ... }
    covered = []
    uncovered = []
    for name in specs:
        # Look for a rules dict referencing this domain
        # Known patterns: MATH_RULES, PHIL_RULES, SOC_RULES
        prefix = name[:4].upper()
        if re.search(rf"{prefix}_RULES\s*=", script_text):
            covered.append(name)
        elif re.search(rf'"{name}"', script_text) or re.search(rf"'{name}'", script_text):
            covered.append(name)
        else:
            uncovered.append(name)

    return {
        "check": "validation-coverage",
        "spec": "scripts/validate-content.py",
        "description": "Domain ASR specs with corresponding validation rules",
        "total_domain_specs": len(specs),
        "with_validation_rules": len(covered),
        "covered": covered,
        "uncovered": uncovered,
    }


# ---------------------------------------------------------------------------
# Check 8: Fragment Health
# Operationalizes the fragment calculus: F = <A, K, P> where A is assumptions,
# K is claims, P is provenance. Reports how many pages have well-formed
# fragments, grounded assumptions, and provenance records.
# ---------------------------------------------------------------------------

def check_fragment_health(content_root: Path) -> dict:
    """Assess fragment health across the repository."""
    skip = {"private", "meta", "slop", "triage", ".obsidian"}

    total = 0
    well_formed = 0  # has at least one claim (defines: or teaches:)
    grounded = 0     # all requires:/extends: paths resolve
    with_provenance = 0  # has cites: or authors:
    broken_links = 0
    typed_but_no_claims = 0  # has type: but no claims — the enrichment gap

    # Per-discipline breakdown
    discipline_stats = {}

    for md_file in content_root.rglob("*.md"):
        rel = md_file.relative_to(content_root)
        parts = rel.parts
        if any(p in skip for p in parts):
            continue
        if any(p.startswith(".") for p in parts):
            continue

        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        lines = text.split("\n")
        if not lines or lines[0].strip() != "---":
            continue

        end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end = i
                break
        if end is None:
            continue

        fm_text = "\n".join(lines[1:end])
        total += 1

        # Extract key fields
        has_type = bool(re.search(r"^type\s*:", fm_text, re.MULTILINE))
        has_defines = bool(re.search(r"^defines\s*:", fm_text, re.MULTILINE))
        has_teaches = bool(re.search(r"^teaches\s*:", fm_text, re.MULTILINE))
        has_cites = bool(re.search(r"^cites\s*:", fm_text, re.MULTILINE))
        has_authors = bool(re.search(r"^authors\s*:", fm_text, re.MULTILINE))
        has_requires = bool(re.search(r"^requires\s*:", fm_text, re.MULTILINE))

        # Check for empty lists (defines: [] counts as not having claims)
        defines_empty = bool(re.search(r"^defines\s*:\s*\[\s*\]", fm_text, re.MULTILINE))
        teaches_empty = bool(re.search(r"^teaches\s*:\s*\[\s*\]", fm_text, re.MULTILINE))
        cites_empty = bool(re.search(r"^cites\s*:\s*\[\s*\]", fm_text, re.MULTILINE))

        has_claims = (has_defines and not defines_empty) or (has_teaches and not teaches_empty)
        has_prov = (has_cites and not cites_empty) or has_authors

        if has_claims:
            well_formed += 1
        if has_prov:
            with_provenance += 1
        if has_type and not has_claims:
            # Get the type value
            type_match = re.search(r"^type\s*:\s*(\S+)", fm_text, re.MULTILINE)
            if type_match and type_match.group(1) not in ("index", "topic", ""):
                typed_but_no_claims += 1

        # Track broken requires: links
        if has_requires:
            file_dir = md_file.parent
            for line in lines[1:end]:
                stripped = line.strip()
                if stripped.startswith("- ") and ("/" in stripped or stripped.endswith(".md")):
                    ref = stripped[2:].strip().strip('"').strip("'")
                    if ref.startswith("/"):
                        resolved = (content_root / ref.lstrip("/")).resolve()
                    elif ref.endswith(".md"):
                        resolved = (file_dir / ref).resolve()
                    else:
                        continue
                    if not resolved.exists():
                        broken_links += 1
                    else:
                        grounded += 1

        # Per-discipline tracking
        if len(parts) > 1:
            disc = parts[0]
            if disc not in skip and disc != "tags" and not disc.startswith("."):
                if disc not in discipline_stats:
                    discipline_stats[disc] = {
                        "total": 0, "well_formed": 0, "provenance": 0}
                discipline_stats[disc]["total"] += 1
                if has_claims:
                    discipline_stats[disc]["well_formed"] += 1
                if has_prov:
                    discipline_stats[disc]["provenance"] += 1

    # Sort disciplines by well-formed percentage (ascending = worst first)
    disc_sorted = sorted(
        discipline_stats.items(),
        key=lambda x: x[1]["well_formed"] / max(x[1]["total"], 1))

    return {
        "check": "fragment-health",
        "spec": "mathematics/texts/fragment-calculus.md",
        "description": "Fragment calculus health: F = <A, K, P> -- "
                       "well-formedness (K), groundedness (A), provenance (P)",
        "total_pages": total,
        "well_formed": well_formed,
        "well_formed_pct": round(100 * well_formed / max(total, 1), 1),
        "with_provenance": with_provenance,
        "provenance_pct": round(100 * with_provenance / max(total, 1), 1),
        "broken_assumption_links": broken_links,
        "typed_but_no_claims": typed_but_no_claims,
        "worst_disciplines": [
            {"name": name, **stats,
             "well_formed_pct": round(
                 100 * stats["well_formed"] / max(stats["total"], 1), 1)}
            for name, stats in disc_sorted[:5]
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CHECKS = {
    "directories": check_directory_organization,
    "manifests": check_skill_manifests,
    "frontmatter": check_semantic_frontmatter,
    "artifacts": check_formal_artifacts,
    "linking": check_linking,
    "domain-asr": check_domain_asr_coverage,
    "validation": check_validation_coverage,
    "fragments": check_fragment_health,
}

def main():
    parser = argparse.ArgumentParser(description="Assess ASR implementation")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--check", choices=list(CHECKS.keys()),
                        help="Run a single check")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT,
                        help="Repository root")
    args = parser.parse_args()

    content_root = args.repo_root / "content"

    if args.check:
        checks_to_run = {args.check: CHECKS[args.check]}
    else:
        checks_to_run = CHECKS

    results = []
    for name, check_fn in checks_to_run.items():
        if name == "manifests":
            results.append(check_fn(args.repo_root))
        else:
            results.append(check_fn(content_root))

    if args.json:
        print(json.dumps({"assessment": results}, indent=2))
    else:
        for r in results:
            print(f"\n== {r['check']} ==")
            print(f"   Spec: {r['spec']}")
            print(f"   {r['description']}")
            for k, v in r.items():
                if k in ("check", "spec", "description"):
                    continue
                if isinstance(v, list) and len(v) > 5:
                    print(f"   {k}: [{len(v)} items]")
                else:
                    print(f"   {k}: {v}")
        print()

if __name__ == "__main__":
    main()
