"""Application state and lifecycle management.

This module provides minimal application state focused on loading the library
skill manifest and exposing it to API surfaces.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

LIBRARY_ROOT = Path(__file__).resolve().parents[2] / "library"
MANIFEST_PATH = LIBRARY_ROOT / "skill-manifest.json"
MANIFEST_BUILDER = (
    LIBRARY_ROOT
    / "mathematics"
    / "objects"
    / "agential-semioverse"
    / "tools"
    / "skill-manifest"
    / "scripts"
    / "build-skill-manifest.py"
)


@dataclass
class AppState:
    """Centralized application state initialized at startup."""

    manifest: dict[str, Any] = field(default_factory=dict)
    is_ready: bool = False
    startup_error: Optional[str] = None

    def get_skill_count(self) -> int:
        return self.manifest.get("skill_count", 0)

    def get_skills(self) -> list[dict[str, Any]]:
        return self.manifest.get("skills", [])

    def get_skill_by_id(self, skill_id: str) -> Optional[dict[str, Any]]:
        for skill in self.get_skills():
            if skill.get("id") == skill_id:
                return skill
        return None


def load_manifest() -> dict[str, Any]:
    """Load the skill manifest from disk.

    Returns empty manifest if file doesn't exist.
    Raises if file exists but is invalid.
    """
    if not MANIFEST_PATH.exists():
        logger.warning("Manifest not found at %s, attempting to build", MANIFEST_PATH)
        try:
            subprocess.run(
                [sys.executable, str(MANIFEST_BUILDER), "--output", str(MANIFEST_PATH)],
                check=True,
                cwd=str(LIBRARY_ROOT.parent),
            )
        except Exception as exc:
            logger.error("Failed to build manifest: %s", exc)
            return {"version": "1.0.0", "skill_count": 0, "skills": []}

    try:
        manifest = json.loads(MANIFEST_PATH.read_text())
        logger.info("Loaded manifest with %s skills", manifest.get("skill_count", 0))
        return manifest
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid manifest JSON: {exc}")


def validate_manifest_hygiene(manifest: dict[str, Any]) -> None:
    """Validate manifest for duplicates; warn on missing runtime."""
    skills = manifest.get("skills", [])
    seen: set[str] = set()
    duplicates: list[str] = []

    for skill in skills:
        skill_id = skill.get("id")
        if not skill_id:
            continue
        if skill_id in seen and skill_id not in duplicates:
            duplicates.append(skill_id)
        seen.add(skill_id)

    errors = []
    if duplicates:
        errors.append(f"Duplicate skill ids: {', '.join(sorted(duplicates))}")
    if errors:
        raise RuntimeError("; ".join(errors))

    missing_runtime = [s.get("id") for s in skills if not s.get("runtime")]
    if missing_runtime:
        logger.warning(
            "Skills missing runtime (non-fatal): %s",
            ", ".join(sorted(missing_runtime)),
        )


def deduplicate_manifest_skills(manifest: dict[str, Any]) -> dict[str, Any]:
    """Ensure manifest skill ids are unique; keep first occurrence."""
    skills = manifest.get("skills", []) or []
    seen: set[str] = set()
    unique_skills: list[dict[str, Any]] = []

    for skill in skills:
        skill_id = skill.get("id")
        if not skill_id:
            continue
        if skill_id in seen:
            logger.warning("Dropping duplicate skill id in manifest: %s", skill_id)
            continue
        seen.add(skill_id)
        unique_skills.append(skill)

    if len(unique_skills) != len(skills):
        manifest = manifest.copy()
        manifest["skills"] = unique_skills
        manifest["skill_count"] = len(unique_skills)

    return manifest


def scan_skills() -> list[dict[str, Any]]:
    """Scan library for SKILL.md files and return manifest entries."""
    try:
        import yaml
    except Exception:
        logger.warning("PyYAML not available; cannot scan skills")
        return []

    skills: list[dict[str, Any]] = []
    for skill_file in LIBRARY_ROOT.rglob("SKILL.md"):
        try:
            text = skill_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if not text.startswith("---"):
            continue
        lines = text.splitlines()
        fm_end = None
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                fm_end = index
                break
        if fm_end is None:
            continue
        fm_text = "\n".join(lines[1:fm_end]).strip()
        try:
            frontmatter = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError:
            continue

        skill_id = frontmatter.get("id")
        name = frontmatter.get("name")
        if not skill_id or not name:
            continue

        skill_dir = skill_file.parent
        relative_path = skill_dir.relative_to(LIBRARY_ROOT)
        entry: dict[str, Any] = {
            "id": skill_id,
            "name": name,
            "path": str(relative_path),
            "skill_file": str(skill_file.relative_to(LIBRARY_ROOT)),
            "kind": frontmatter.get("kind"),
            "skill_kind": frontmatter.get("skill_kind"),
            "version": frontmatter.get("version"),
            "tags": frontmatter.get("tags", []),
            "inputs": frontmatter.get("inputs", []),
            "outputs": frontmatter.get("outputs", []),
            "capabilities": frontmatter.get("capabilities", {}),
        }
        if "skill_spec_version" in frontmatter:
            entry["skill_spec_version"] = frontmatter["skill_spec_version"]

        summary = frontmatter.get("summary") or frontmatter.get("description")
        if summary:
            entry["summary"] = summary if isinstance(summary, str) else None

        runtime = frontmatter.get("runtime")
        if isinstance(runtime, dict) and runtime.get("entrypoint"):
            entry["runtime"] = {
                "entrypoint": str(relative_path / runtime.get("entrypoint", "")),
                "language": runtime.get("language"),
                "invocation": runtime.get("invocation", "cli"),
            }
            if "env_vars" in runtime:
                entry["runtime"]["env_vars"] = runtime["env_vars"]

        skills.append(entry)

    return skills


def build_manifest_if_needed(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build the skill manifest if it is missing or empty."""
    skill_count = manifest.get("skill_count", 0)
    if skill_count:
        return deduplicate_manifest_skills(manifest)
    if not MANIFEST_BUILDER.exists():
        logger.warning("Manifest builder not found; scanning skills instead")
        scanned = scan_skills()
        return deduplicate_manifest_skills({
            "version": "1.0.0",
            "skill_count": len(scanned),
            "skills": scanned,
        })
    logger.info("Rebuilding skill manifest")
    try:
        result = subprocess.run(
            [sys.executable, str(MANIFEST_BUILDER), "--output", str(MANIFEST_PATH)],
            cwd=str(LIBRARY_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.error("Manifest build failed: %s", result.stderr)
            return manifest
        if result.stdout:
            logger.info("Manifest build output: %s", result.stdout.strip())
    except Exception as exc:
        logger.error("Manifest build error: %s", exc)
        scanned = scan_skills()
        return {
            "version": "1.0.0",
            "skill_count": len(scanned),
            "skills": scanned,
        }
    try:
        rebuilt = json.loads(MANIFEST_PATH.read_text())
        logger.info("Rebuilt manifest with %s skills", rebuilt.get("skill_count", 0))
        return deduplicate_manifest_skills(rebuilt)
    except Exception as exc:
        logger.error("Failed to read rebuilt manifest: %s", exc)
        scanned = scan_skills()
        return deduplicate_manifest_skills({
            "version": "1.0.0",
            "skill_count": len(scanned),
            "skills": scanned,
        })


async def create_app_state() -> AppState:
    """Create and initialize application state.

    Initializes the skill manifest cache. If initialization fails, is_ready
    remains False and startup_error is set.
    """
    state = AppState()

    logger.info("Library root: %s", LIBRARY_ROOT)
    logger.info("Manifest path: %s", MANIFEST_PATH)
    logger.info("Manifest builder: %s", MANIFEST_BUILDER)

    try:
        manifest = build_manifest_if_needed(load_manifest())
        validate_manifest_hygiene(manifest)
        state.manifest = manifest
    except Exception as exc:
        logger.error("Manifest loading failed: %s", exc)
        state.startup_error = str(exc)
        return state

    state.is_ready = True
    logger.info("Application state initialized successfully")
    return state


async def shutdown_app_state(state: AppState) -> None:
    """Clean up application state on shutdown."""
    state.is_ready = False
