#!/usr/bin/env python3
"""infer-triage-frontmatter.py — Enrich triage frontmatter via local LLM.

Picks triage files (oldest-modified first), passes content to a local
model via Ollama with the frontmatter spec as context, and replaces the
frontmatter. Verifies that the body content is byte-identical before
writing.

Complements enrich-triage.py (mechanical fixes) with inference-based
enrichment: guessing type, tags, description, discipline, and defines.

Usage:
    python3 scripts/infer-triage-frontmatter.py [--dry-run] [--batch N] [--model MODEL]

Examples:
    python3 scripts/infer-triage-frontmatter.py --dry-run              # Preview with default model
    python3 scripts/infer-triage-frontmatter.py --batch 5              # Enrich 5 files
    python3 scripts/infer-triage-frontmatter.py --file path            # One specific file
    python3 scripts/infer-triage-frontmatter.py --model qwen3:4b       # Use a different model
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
# Walk up to find the content root (directory containing triage/)
_d = SCRIPT_DIR
CONTENT_DIR = None
for _ in range(10):
    if (_d / "triage").is_dir():
        CONTENT_DIR = _d
        break
    if _d.parent == _d:
        break
    _d = _d.parent

if CONTENT_DIR is None:
    print("ERROR: Could not find content/triage/")
    sys.exit(1)

sys.path.insert(0, str(CONTENT_DIR / "scripts"))
import local_llm  # noqa: E402
from tag_normalize import (  # noqa: E402
    normalize_tag, deduplicate_tags, CAMELCASE_RE, DISCIPLINE_ECHO,
)

TRIAGE_DIR = CONTENT_DIR / "triage"
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

SCRIPT_VERSION = "4"

# Token threshold for large-file summarization.
# Files above this approximate token count are summarized before enrichment
# using a long-context model, rather than truncated at a fixed char limit.
SUMMARY_THRESHOLD_TOKENS = 2000  # ≈ 8000 chars
SUMMARY_MODEL = "phi-3-mini-128k"  # long-context model for summarization

# Model trust ordering — higher index = more trusted for enrichment.
# When a file was enriched by a model at or above the current model's
# trust level, we skip it. When enriched by a lower-trust model, we
# re-enrich. Models not in this list get trust level 0 (lowest).
MODEL_TRUST_ORDER = [
    # Tiny/fast — acceptable for rapid first-pass
    "qwen2.5-0.5b",     # also matches qwen2.5-0.5b-instruct-vitis-npu:3
    "qwen3:1.7b",
    # Small — good general classification
    "qwen2.5:3b",
    "llama3.2:3b",
    # Mid — balanced quality/speed
    "qwen3:4b",
    "phi4-mini",        # also matches phi-4-mini-instruct-vitis-npu:2
    "gemma3:4b",
    "mistral-7b",       # also matches Mistral-7B-Instruct-v0-2-vitis-npu:1
    # 7B — solid quality
    "qwen2.5:7b",       # also matches qwen2.5-7b-instruct-vitis-npu:2
    "qwen3:8b",
    "deepseek-r1-7b",   # also matches DeepSeek-R1-Distill-Qwen-7B-vitis-npu:1
    # Large — high quality
    "gemma3:12b",
    "qwen2.5:14b",
    "qwen2.5:32b",
    "llama3.1:8b",
    "llama3.1:70b",
    # Cloud — highest trust (human-reviewed output)
    "claude-haiku-4",
    "claude-sonnet-4",
    "claude-opus-4",
]


def _normalize_model_name(model_name: str) -> str:
    """Normalize a model name for trust lookup.

    Handles colon-tags: size tags like ':7b' are kept (part of identity),
    but metadata tags like ':latest' and Foundry versions like ':2' are
    stripped. Then strips Foundry suffixes and collapses separators.
    """
    s = model_name.lower()
    # Handle colon-tag: keep size tags (e.g. :7b, :0.5b), strip others
    if ":" in s:
        base, tag = s.rsplit(":", 1)
        if re.match(r"^\d+\.?\d*b$", tag):
            s = f"{base}-{tag}"
        else:
            s = base
    # Strip Foundry-specific suffixes
    for suffix in ["-vitis", "-npu", "-qnn", "-instruct", "-generic"]:
        if suffix in s:
            s = s[:s.index(suffix)]
    # Strip -distill-<vendor> patterns
    s = re.sub(r"-distill-\w+", "", s)
    # Collapse separators for fuzzy matching
    return s.replace("-", "").replace(".", "")


def get_model_trust_level(model_name: str) -> int:
    """Return the trust level for a model (index in MODEL_TRUST_ORDER).

    Models not in the list get trust level 0. Models in the list get
    their 1-based index (so even the lowest listed model outranks
    unlisted models). Foundry model names are normalized before lookup.
    """
    # Try exact match first
    try:
        return MODEL_TRUST_ORDER.index(model_name) + 1
    except ValueError:
        pass
    # Try normalized (handles Foundry names like phi-4-mini-instruct-vitis-npu:2)
    normalized = _normalize_model_name(model_name)
    for i, known in enumerate(MODEL_TRUST_ORDER):
        if _normalize_model_name(known) == normalized:
            return i + 1
    return 0


def parse_enrichment_provenance(fm_text: str) -> tuple[str, int, int]:
    """Extract the enriching model name, trust level, and script version.

    Parses triage-enriched-by field which has format:
      infer-triage-frontmatter-v<N>-by-<model>

    Returns (model_name, trust_level, script_version).
    Returns ("", -1, 0) if never enriched.
    """
    match = re.search(
        r'^triage-enriched-by:\s*["\']?infer-triage-frontmatter-v(\d+)-by-(.+?)["\']?\s*$',
        fm_text, re.MULTILINE
    )
    if match:
        version = int(match.group(1))
        model_name = match.group(2).strip()
        return model_name, get_model_trust_level(model_name), version
    # Legacy: old-style "triage-status: enriched" has no model info → trust 0
    if re.search(r'^triage-status:\s*enriched', fm_text, re.MULTILINE):
        return "unknown", 0, 0
    return "", -1, 0  # -1 trust means never enriched


# Valid type values from the semantic-frontmatter spec
VALID_TYPES = [
    "term", "topic", "index", "lesson", "person", "concept",
    "school", "text", "babble", "letter", "skill", "question",
]

# Common synonyms that models generate — auto-correct to valid types
TYPE_SYNONYMS = {
    "essay": "text",
    "article": "text",
    "blog": "text",
    "post": "text",
    "note": "babble",
    "definition": "term",
    "glossary": "term",
    "specification": "text",
    "spec": "text",
    "tutorial": "lesson",
    "guide": "lesson",
    "course": "lesson",
    "reference": "topic",
    "overview": "topic",
    "biography": "person",
    "faq": "question",
}

# Fallback system prompt used when SKILL.md LLM Context section is missing
FALLBACK_SYSTEM_PROMPT = """You are a frontmatter enrichment tool. Given a markdown file, produce improved YAML frontmatter for it.

Output ONLY the frontmatter block: start with --- and end with ---. Do NOT output any body text or explanation.

Fields to produce:
- title: a clear, concise title (required)
- type: one of: {valid_types}
- tags: 3-5 CamelCase tags, most-specific first, cross-cutting (not duplicating directory info)
- description: one sentence summarizing what this file is about
- defines: list of terms/concepts this file defines (if applicable)
- target-discipline: which discipline this content belongs to

Tag conventions:
- Tags MUST be CamelCase with no spaces or hyphens: Anarchism, PoliticalTheory, SettlerColonialism
- 3-5 tags per file, maximum 10. No duplicates.
- Most-specific to least-specific ordering.
- Do NOT echo the discipline as a tag.

Preservation rules:
- Keep existing date-created, date-updated, authors, aliases fields exactly
- Do NOT invent a date-created value
- Do NOT add triage-status, triage-enriched-by, or date-triage-enriched fields
- Field names MUST NOT contain spaces"""


def _load_llm_context() -> str:
    """Load the LLM context section from SKILL.md.

    The SKILL.md contains a section delimited by BEGIN_LLM_CONTEXT /
    END_LLM_CONTEXT markers. This section is designed to be the system
    prompt for the local model, kept in the same file as the skill's
    human documentation so both stay in sync.
    """
    skill_md = SCRIPT_DIR / "SKILL.md"
    if not skill_md.exists():
        return ""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except Exception:
        return ""
    start_marker = "<!-- BEGIN_LLM_CONTEXT -->"
    end_marker = "<!-- END_LLM_CONTEXT -->"
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start < 0 or end < 0:
        return ""
    return text[start + len(start_marker):end].strip()


def _load_tag_vocabulary() -> list[str]:
    """Read the controlled vocabulary from content/tags/*.md."""
    tags_dir = CONTENT_DIR / "tags"
    if not tags_dir.is_dir():
        return []
    return sorted(
        p.stem for p in tags_dir.glob("*.md")
        if p.stem not in ("index", "README", "_index")
    )


def _build_system_prompt() -> str:
    """Build the system prompt from SKILL.md context + controlled vocabulary."""
    context = _load_llm_context()
    if not context:
        context = FALLBACK_SYSTEM_PROMPT.format(
            valid_types=", ".join(VALID_TYPES)
        )

    vocab = _load_tag_vocabulary()
    if vocab:
        context += (
            "\n\n### Controlled vocabulary\n\n"
            "Prefer these existing tags when applicable: "
            + ", ".join(vocab) + "\n"
        )

    context += (
        "\n\n### Valid type values\n\n"
        + ", ".join(VALID_TYPES) + "\n"
    )

    return context


def count_tokens(text: str) -> int:
    """Approximate token count (4 chars per token)."""
    return len(text) // 4


def parse_frontmatter_and_body(content: str) -> tuple[str | None, str]:
    """Split content into (frontmatter_text, body).

    Returns (None, content) if no frontmatter block exists.
    """
    if not content.startswith("---"):
        return None, content

    end = content.find("---", 3)
    if end < 0:
        return None, content

    # Include the newline after closing ---
    fm_text = content[3:end].strip()
    body = content[end + 3:]
    return fm_text, body


def call_llm(
    system: str, user: str, model: str = "", temperature: float = 0.3,
) -> tuple[str, str]:
    """Call local LLM with system + user messages.

    Returns (response_text, actual_model_used).
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    result = local_llm.complete(
        messages=messages,
        model=model or DEFAULT_MODEL,
        temperature=temperature,
    )
    if result["error"]:
        raise RuntimeError(result["error"])
    return result["response"], result["model"]


def _clean_yaml_keys(fm_text: str) -> str:
    """Remove lines where the YAML key portion contains whitespace.

    Catches model errors like 'date- created: ...' where the key has a
    space inserted. Only applies to top-level key lines (not list items).
    """
    lines = fm_text.split("\n")
    clean = []
    for line in lines:
        # Top-level key lines look like: word-or-words: ...
        # List items start with "  - " and are fine
        m = re.match(r'^([^:\n#]+):', line)
        if m:
            key = m.group(1)
            if re.search(r'\s', key):
                # Key has whitespace — drop this line
                continue
        clean.append(line)
    return "\n".join(clean)


def extract_frontmatter_from_response(response: str) -> str | None:
    """Extract the YAML frontmatter block from the model's response.

    The model should return a block starting with --- and ending with ---.
    """
    # Find the frontmatter block in the response
    match = re.search(r"^---\s*\n(.*?)\n---", response, re.DOTALL | re.MULTILINE)
    if match:
        return _clean_yaml_keys(match.group(1).strip())

    # Try without leading ---
    lines = response.strip().split("\n")
    # Filter out lines that are clearly not YAML
    yaml_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            continue
        if stripped.startswith("```"):
            continue
        if not stripped:
            continue
        # Looks like YAML if it has key: value or is a list item
        if ":" in stripped or stripped.startswith("- "):
            yaml_lines.append(line)

    if yaml_lines:
        return _clean_yaml_keys("\n".join(yaml_lines))

    return None


def validate_frontmatter(fm_text: str) -> tuple[list[str], list[str]]:
    """Check the generated frontmatter for problems.

    Returns (warnings, errors). Errors should block the write;
    warnings are informational.
    """
    warnings = []
    errors = []

    if "title" not in fm_text:
        warnings.append("missing title field")

    # Check for whitespace in YAML keys
    for line in fm_text.split("\n"):
        m = re.match(r'^([^:\n#]+):', line)
        if m:
            key = m.group(1)
            if re.search(r'\s', key):
                errors.append(f"whitespace in key: {repr(key)}")

    # Check for invalid type values
    type_match = re.search(r"^type:\s*(.+)$", fm_text, re.MULTILINE)
    if type_match:
        type_val = type_match.group(1).strip().strip('"').strip("'")
        if type_val not in VALID_TYPES:
            errors.append(f"invalid type: {type_val}")

    # Check tags are CamelCase (after post-processing, violations are errors)
    tag_count = 0
    tag_section = False
    for line in fm_text.split("\n"):
        if line.strip().startswith("tags:"):
            tag_section = True
            continue
        if tag_section and line.strip().startswith("- "):
            tag = line.strip().lstrip("- ").strip().strip('"').strip("'")
            tag_count += 1
            if not CAMELCASE_RE.match(tag):
                errors.append(f"tag not CamelCase after normalization: {tag}")
        elif tag_section and not line.startswith(" "):
            tag_section = False

    if tag_count > 10:
        errors.append(f"too many tags: {tag_count} (max 10)")
    elif tag_count > 5:
        warnings.append(f"{tag_count} tags (prefer 3-5)")
    if tag_count == 0:
        warnings.append("no tags generated")

    return warnings, errors


def normalize_type_in_frontmatter(fm_text: str) -> tuple[str, list[str]]:
    """Auto-correct invalid type values using TYPE_SYNONYMS.

    Returns (corrected_fm_text, list_of_changes).
    """
    changes: list[str] = []
    type_match = re.search(r"^(type:\s*)(.+)$", fm_text, re.MULTILINE)
    if not type_match:
        return fm_text, changes

    type_val = type_match.group(2).strip().strip('"').strip("'")
    if type_val in VALID_TYPES:
        return fm_text, changes

    corrected = TYPE_SYNONYMS.get(type_val.lower())
    if corrected:
        changes.append(f"type corrected: \"{type_val}\" -> \"{corrected}\"")
        fm_text = fm_text[:type_match.start()] + f"type: {corrected}" + fm_text[type_match.end():]

    return fm_text, changes


def _extract_target_discipline(fm_text: str) -> str | None:
    """Extract target-discipline from frontmatter for discipline-echo removal."""
    match = re.search(r'^target-discipline:\s*(.+)$', fm_text, re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"').strip("'").lower()
    return None


def normalize_tags_in_frontmatter(fm_text: str) -> tuple[str, list[str]]:
    """Post-process tags in generated frontmatter: normalize, dedupe, cap count.

    Returns (cleaned_fm_text, list_of_changes).
    """
    lines = fm_text.split("\n")
    changes: list[str] = []

    # Find the tags section
    tag_start = None
    tag_end = None
    raw_tags = []
    in_tags = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("tags:"):
            tag_start = i
            in_tags = True
            # Handle inline tags: `tags: [Foo, Bar]`
            rest = stripped[5:].strip()
            if rest.startswith("["):
                inner = rest.strip("[]")
                if inner:
                    raw_tags = [t.strip().strip('"').strip("'") for t in inner.split(",")]
                tag_end = i + 1
                in_tags = False
            continue
        if in_tags:
            if stripped.startswith("- "):
                tag_val = stripped[2:].strip().strip('"').strip("'")
                raw_tags.append(tag_val)
            elif stripped == "" or stripped.startswith("#"):
                continue
            else:
                tag_end = i
                in_tags = False

    if tag_start is None:
        return fm_text, changes

    if tag_end is None:
        tag_end = len(lines)

    if not raw_tags:
        return fm_text, changes

    # Get discipline for echo removal (from LLM-generated target-discipline)
    discipline = _extract_target_discipline(fm_text)

    # Normalize each tag
    normalized = []
    for tag in raw_tags:
        result, reason = normalize_tag(tag, discipline)
        if result is None:
            changes.append(f"removed: \"{tag}\" ({reason})")
            continue
        if reason:
            changes.append(f"normalized: \"{tag}\" -> \"{result}\"")
        normalized.append(result)

    # Deduplicate
    unique, dupes = deduplicate_tags(normalized)
    for d in dupes:
        changes.append(f"removed duplicate: \"{d}\"")

    # Cap at 10 tags
    if len(unique) > 10:
        dropped = unique[10:]
        unique = unique[:10]
        for d in dropped:
            changes.append(f"trimmed excess tag: \"{d}\"")

    # Rebuild the tags section in the YAML
    if not unique:
        new_tag_lines = ["tags: []"]
    else:
        new_tag_lines = ["tags:"]
        for tag in unique:
            new_tag_lines.append(f"  - {tag}")

    # Reconstruct frontmatter
    result_lines = lines[:tag_start] + new_tag_lines + lines[tag_end:]
    return "\n".join(result_lines), changes


def stamp_provenance(fm_text: str, model: str) -> str:
    """Add provenance fields and strip any model-generated triage-status.

    Injects triage-enriched-by and date-triage-enriched into the
    frontmatter. Strips triage-status if the model included it despite
    being told not to.
    """
    # Strip any triage-status, triage-enriched-by, or date-triage-enriched
    # the model may have generated (we control these, not the model)
    lines = fm_text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("triage-status:"):
            continue
        if stripped.startswith("triage-enriched-by:"):
            continue
        if stripped.startswith("date-triage-enriched:"):
            continue
        cleaned.append(line)

    # Append provenance fields
    # Note: model may be a Foundry name like "phi-4-mini-instruct-vitis-npu:2"
    # We use whatever name was actually used for inference
    provenance_tag = f"infer-triage-frontmatter-v{SCRIPT_VERSION}-by-{model}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    cleaned.append(f'triage-enriched-by: "{provenance_tag}"')
    cleaned.append(f"date-triage-enriched: {now}")

    return "\n".join(cleaned)


def summarize_for_enrichment(content: str, filepath_hint: str = "") -> str:
    """Summarize a large file using a long-context model.

    Used when a file is too large to send directly to the enrichment model.
    Falls back to truncation if the summary model is unavailable or fails.
    """
    hint = f" (file: {filepath_hint})" if filepath_hint else ""
    try:
        result = local_llm.complete(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Summarize the following document in 200-300 words{hint}. "
                        "Preserve key topics, named entities, vocabulary, and structure. "
                        "Output only the summary, no preamble.\n\n"
                        f"{content}"
                    ),
                }
            ],
            model=SUMMARY_MODEL,
            max_tokens=512,
            temperature=0.2,
        )
        if not result["error"] and result["response"]:
            token_count = count_tokens(content)
            return f"[Summary of ~{token_count}-token file]\n{result['response']}"
    except Exception:
        pass
    # Fallback: truncate
    return content[:8000] + "\n...[truncated at 8000 chars]"


def needs_enrichment(filepath: Path, current_trust: int) -> bool:
    """Fast check (no LLM) whether a file needs enrichment.

    Reads only the frontmatter portion (first 2KB) of each file for
    speed when pre-scanning thousands of candidates.
    """
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            head = f.read(2048)
    except Exception:
        return False

    if not head.strip():
        return False

    if not head.startswith("---"):
        return True  # No frontmatter → needs enrichment

    end_idx = head.find("---", 3)
    if end_idx < 0:
        return True  # Malformed or frontmatter extends beyond 2KB → try to enrich

    fm_text = head[3:end_idx].strip()

    # 30-day recency check
    date_match = re.search(r'^date-triage-enriched:\s*(.+)$', fm_text, re.MULTILINE)
    if date_match:
        try:
            enriched_at = datetime.fromisoformat(date_match.group(1).strip())
            if enriched_at.tzinfo is None:
                enriched_at = enriched_at.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - enriched_at
            if age < timedelta(days=30):
                return False
        except (ValueError, AttributeError):
            pass

    # Trust and version check
    _, prev_trust, prev_version = parse_enrichment_provenance(fm_text)
    # Allow re-enrichment if script version is newer (better pipeline)
    if prev_version < int(SCRIPT_VERSION):
        return True
    # Skip if already enriched by equal or higher trust model
    if prev_trust >= 0 and prev_trust >= current_trust:
        return False

    return True


def get_triage_files_oldest_first() -> list[Path]:
    """Get all triage .md files, sorted by modification time (oldest first)."""
    skip_dirs = {".trash", ".obsidian", "node_modules", ".git"}
    files = []

    for root, dirs, filenames in os.walk(TRIAGE_DIR):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in filenames:
            if not f.endswith(".md"):
                continue
            filepath = Path(root) / f
            files.append(filepath)

    # Sort by modification time, oldest first
    files.sort(key=lambda p: p.stat().st_mtime)
    return files


def enrich_file(filepath: Path, dry_run: bool = False, model: str = "") -> dict:
    """Enrich one triage file's frontmatter via local LLM.

    Returns a result dict with status and details.
    """
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"status": "error", "message": f"read failed: {e}"}

    if not content.strip():
        return {"status": "skipped", "message": "empty file"}

    original_fm, body = parse_frontmatter_and_body(content)

    # Model-aware skip logic: check enrichment provenance
    current_model = model or DEFAULT_MODEL
    current_trust = get_model_trust_level(current_model)
    if original_fm:
        prev_model, prev_trust, prev_version = parse_enrichment_provenance(original_fm)
        # Skip if recently enriched (within 30 days) — unless script version is newer
        date_match = re.search(r'^date-triage-enriched:\s*(.+)$', original_fm, re.MULTILINE)
        if date_match and prev_version >= int(SCRIPT_VERSION):
            try:
                enriched_at = datetime.fromisoformat(date_match.group(1).strip())
                if enriched_at.tzinfo is None:
                    enriched_at = enriched_at.replace(tzinfo=timezone.utc)
                age = datetime.now(timezone.utc) - enriched_at
                if age < timedelta(days=30):
                    return {
                        "status": "skipped",
                        "message": f"recently enriched {age.days}d ago by {prev_model}",
                    }
            except (ValueError, AttributeError):
                pass
        # Allow re-enrichment if script version is newer
        if prev_version >= int(SCRIPT_VERSION):
            # Skip if enriched by a model with equal or higher trust
            if prev_trust >= 0 and prev_trust >= current_trust:
                return {
                    "status": "skipped",
                    "message": f"already enriched by {prev_model} (trust {prev_trust} >= {current_trust})",
                }

    # Build the prompt (system from SKILL.md + vocabulary, user = file content)
    system_prompt = _build_system_prompt()

    # Determine file content to send: summarize large files, send small ones whole
    file_tokens = count_tokens(content)
    if file_tokens > SUMMARY_THRESHOLD_TOKENS:
        file_content = summarize_for_enrichment(
            content, str(filepath.relative_to(TRIAGE_DIR))
        )
    else:
        file_content = content

    user_prompt = f"File path: {filepath.relative_to(TRIAGE_DIR)}\n\nFile content:\n{file_content}"

    try:
        response, actual_model = call_llm(system_prompt, user_prompt, model=model)
    except Exception as e:
        return {"status": "error", "message": f"LLM error: {e}"}

    new_fm_text = extract_frontmatter_from_response(response)
    if not new_fm_text:
        return {"status": "error", "message": "could not parse frontmatter from response",
                "response": response[:500]}

    # Post-process tags: normalize, deduplicate, cap count
    new_fm_text, tag_changes = normalize_tags_in_frontmatter(new_fm_text)

    # Auto-correct invalid type values
    new_fm_text, type_changes = normalize_type_in_frontmatter(new_fm_text)
    tag_changes.extend(type_changes)

    # Validate the generated frontmatter
    warnings, errors = validate_frontmatter(new_fm_text)

    if errors:
        return {
            "status": "error",
            "message": f"validation failed: {'; '.join(errors)}",
            "new_frontmatter": new_fm_text,
            "tag_normalization": tag_changes,
        }

    # Stamp provenance using actual model used (may differ from requested if
    # Foundry resolved to a different name or fell back to Ollama)
    new_fm_text = stamp_provenance(new_fm_text, actual_model)

    # Reconstruct the file: new frontmatter + original body
    # The body must be EXACTLY the same as the original
    # Note: body already includes leading whitespace from after the closing ---
    if original_fm is not None:
        # Had frontmatter before — body starts after closing ---
        new_content = f"---\n{new_fm_text}\n---{body}"
    else:
        # No frontmatter before — body is the entire original content
        new_content = f"---\n{new_fm_text}\n---\n\n{content}"

    # CRITICAL: verify body is unchanged
    _, new_body = parse_frontmatter_and_body(new_content)
    if original_fm is not None:
        expected_body = body
    else:
        expected_body = "\n\n" + content

    if new_body != expected_body:
        return {"status": "error", "message": "body content changed — refusing to write",
                "expected_len": len(expected_body), "got_len": len(new_body)}

    if dry_run:
        return {
            "status": "would_enrich",
            "new_frontmatter": new_fm_text,
            "warnings": warnings,
            "tag_normalization": tag_changes,
            "summarized": file_tokens > SUMMARY_THRESHOLD_TOKENS,
        }

    filepath.write_text(new_content, encoding="utf-8")
    return {
        "status": "enriched",
        "new_frontmatter": new_fm_text,
        "warnings": warnings,
        "tag_normalization": tag_changes,
        "summarized": file_tokens > SUMMARY_THRESHOLD_TOKENS,
    }


def format_duration(seconds: float) -> str:
    """Format seconds into a human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


def format_size(bytes_count: int) -> str:
    """Format byte count into human-readable size."""
    if bytes_count < 1024:
        return f"{bytes_count}B"
    if bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f}KB"
    return f"{bytes_count / (1024 * 1024):.1f}MB"


def main():
    parser = argparse.ArgumentParser(
        description="Enrich triage frontmatter via local LLM")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing")
    parser.add_argument("--batch", type=int, default=1,
                        help="Number of files to process (default: 1)")
    parser.add_argument("--file", type=str, default="",
                        help="Process a specific file (relative to triage/)")
    parser.add_argument("--model", type=str, default="",
                        help="Ollama model to use (default: %s)" % DEFAULT_MODEL)
    args = parser.parse_args()

    active_model = args.model or local_llm.suggest_model("classification")
    trust_level = get_model_trust_level(active_model)

    if not local_llm.is_available():
        print("ERROR: No local LLM backend available. Install Ollama or Foundry Local.")
        sys.exit(1)

    if args.file:
        target = TRIAGE_DIR / args.file
        if not target.exists():
            print(f"ERROR: File not found: {target}")
            sys.exit(1)
        files = [target]
        eligible_count = 1
        total_count = 1
    else:
        files = get_triage_files_oldest_first()
        total_count = len(files)
        # Pre-scan to count files that will actually trigger LLM calls.
        # Reads only the first 2KB (frontmatter) of each file — no LLM calls.
        print(f"Pre-scanning {total_count} files...", end="\r", flush=True)
        eligible_count = sum(1 for f in files if needs_enrichment(f, trust_level))

    # Header
    mode = "DRY RUN" if args.dry_run else "ENRICHING"
    candidates_label = (
        f"{eligible_count} of {total_count}"
        if not args.file else "1"
    )
    print(f"{mode} | model: {active_model} (trust {trust_level}) | batch: {args.batch} | candidates: {candidates_label}")
    print()

    enriched = 0
    skipped = 0
    errors = 0
    file_times: list[float] = []
    run_start = time.monotonic()

    for filepath in files:
        if enriched >= args.batch:
            break

        rel = str(filepath.relative_to(TRIAGE_DIR))
        file_size = filepath.stat().st_size

        file_start = time.monotonic()
        result = enrich_file(filepath, dry_run=args.dry_run, model=active_model)
        file_elapsed = time.monotonic() - file_start

        if result["status"] == "skipped":
            skipped += 1
            continue

        if result["status"] == "error":
            errors += 1
            print(f"  ERROR {rel} ({format_size(file_size)}, {format_duration(file_elapsed)})")
            print(f"    {result['message']}")
            if "response" in result:
                print(f"    Response preview: {result['response'][:200]}")
            continue

        enriched += 1
        file_times.append(file_elapsed)
        prefix = "[DRY] " if args.dry_run else ""
        summarized_flag = " [summarized]" if result.get("summarized") else ""
        print(f"  {prefix}{rel} ({format_size(file_size)}, {format_duration(file_elapsed)}{summarized_flag})")

        # Show key fields compactly
        fm_lines = result["new_frontmatter"].split("\n")
        for line in fm_lines:
            print(f"    {line}")
        if result.get("tag_normalization"):
            for tc in result["tag_normalization"]:
                print(f"    TAG FIX: {tc}")
        if result.get("warnings"):
            for w in result["warnings"]:
                print(f"    WARNING: {w}")
        print()

    # Summary
    total_elapsed = time.monotonic() - run_start
    print("---")
    print(f"Done: {enriched} enriched, {skipped} skipped, {errors} errors")
    print(f"Time: {format_duration(total_elapsed)} total", end="")
    if file_times:
        avg = sum(file_times) / len(file_times)
        print(f", {format_duration(avg)} avg/file", end="")
        if len(file_times) > 1:
            fastest = min(file_times)
            slowest = max(file_times)
            print(f" (fastest {format_duration(fastest)}, slowest {format_duration(slowest)})", end="")
    print()


if __name__ == "__main__":
    main()
