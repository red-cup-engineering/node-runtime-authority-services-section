from __future__ import annotations

import dataclasses
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from .annterm import parse_ann_term
from . import yaml_loader
from .sscu_model import Concept


@dataclasses.dataclass
class IngestResult:
    concepts: Dict[str, Concept]
    same_as: Dict[str, List[str]]
    paths: Dict[str, str]


class Ingestor:
    def __init__(self, sources_pattern: str):
        self.pattern = sources_pattern

    def load(self, root: Path) -> IngestResult:
        concepts: Dict[str, Concept] = {}
        same_as: Dict[str, List[str]] = {}
        paths: Dict[str, str] = {}
        for path in root.glob(self.pattern):
            if not path.is_file():
                continue
            concept = self._parse_file(path, root)
            if concept.const in concepts:
                prev = paths.get(concept.const, "<unknown>")
                try:
                    rel = path.relative_to(root)
                except ValueError:
                    rel = path
                raise ValueError(
                    f"Duplicate concept id '{concept.const}' from {prev} and {rel}"
                )
            concepts[concept.const] = concept
            if concept.same_as:
                same_as[concept.const] = concept.same_as
            try:
                rel = path.relative_to(root)
            except ValueError:
                rel = path
            paths[concept.const] = str(rel)
        return IngestResult(concepts=concepts, same_as=same_as, paths=paths)

    def _parse_file(self, path: Path, root: Path) -> Concept:
        text = path.read_text(encoding="utf-8")
        frontmatter, body = self._split_frontmatter(text)
        has_frontmatter = bool(frontmatter.strip())
        try:
            fm = yaml_loader.safe_load(frontmatter) if has_frontmatter else {}
            fm = fm or {}
        except Exception as exc:  # pragma: no cover - defensive; loader may raise
            raise ValueError(f"Failed to parse frontmatter in {path}: {exc}") from exc

        const_raw = str(fm.get("id", "")).strip() if has_frontmatter else ""
        if const_raw:
            const = slugify(const_raw)
        else:
            const = self._derive_id(path, root)

        title = fm.get("title")
        if not title:
            title = _first_heading(body) or path.stem
        tags = fm.get("tags", []) or []
        same_as = fm.get("same_as", []) or []
        publish = fm.get("publish", None)
        publish_to_raw = fm.get("publish_to", []) or []
        if isinstance(publish_to_raw, str):
            publish_to = [publish_to_raw]
        elif isinstance(publish_to_raw, list):
            publish_to = [str(item) for item in publish_to_raw if item]
        else:
            publish_to = []
        status = fm.get("status")
        ann_raw = fm.get("ann", []) or []
        ann_terms = [parse_ann_term(x) for x in ann_raw]
        exogenous = self._exogenous_metadata(path, root)
        endogenous = fm if has_frontmatter else {}
        return Concept(
            const=const,
            title=title,
            tags=tags,
            ann=ann_terms,
            body=body,
            same_as=same_as,
            publish=publish,
            publish_to=publish_to,
            status=status,
            exogenous=exogenous,
            endogenous=endogenous,
        )

    def _split_frontmatter(self, text: str) -> Tuple[str, str]:
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                return parts[1], parts[2]
            raise ValueError("Unterminated frontmatter block (missing closing '---')")
        return "", text

    def _derive_id(self, path: Path, root: Path) -> str:
        # Derive concept id from path (semiotic-markdown spec).
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        # If the file lives under a content tree, prefer id relative to that root.
        # This keeps ids stable even when evaluating from repo root.
        for marker in ("content",):
            try:
                idx = rel.parts.index(marker)
                rel = Path(*rel.parts[idx + 1 :])
                break
            except ValueError:
                continue
        rel = rel.with_suffix("")
        return slugify(rel.as_posix())

    def _exogenous_metadata(self, path: Path, root: Path) -> Dict[str, object]:
        stat = path.stat()
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        mime, _ = mimetypes.guess_type(path.name)
        if not mime and path.suffix.lower() == ".md":
            mime = "text/markdown"
        return {
            "path": str(rel),
            "suffix": path.suffix,
            "mime_type": mime,
            "size_bytes": stat.st_size,
            "mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        }


_HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _first_heading(body: str) -> str | None:
    match = _HEADING_RE.search(body)
    if not match:
        return None
    return match.group(1).strip() or None


_SLUG_BAD = re.compile(r"[^a-z0-9_-]+")
_SLUG_DASH = re.compile(r"-+")


def slugify(text: str) -> str:
    # Matches `content/specs/semiotic-markdown.md` slugification rules.
    value = (text or "").strip().lower()
    value = value.replace("/", "-").replace("\\", "-")
    value = _SLUG_BAD.sub("-", value)
    value = _SLUG_DASH.sub("-", value).strip("-")
    return value or "item"
