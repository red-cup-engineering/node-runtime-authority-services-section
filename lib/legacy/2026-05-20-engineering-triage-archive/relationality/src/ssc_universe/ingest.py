from __future__ import annotations

import dataclasses
import json
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
            concept = self._parse_file(path)
            concepts[concept.const] = concept
            if concept.same_as:
                same_as[concept.const] = concept.same_as
            try:
                rel = path.relative_to(root)
            except ValueError:
                rel = path
            paths[concept.const] = str(rel)
        return IngestResult(concepts=concepts, same_as=same_as, paths=paths)

    def _parse_file(self, path: Path) -> Concept:
        text = path.read_text(encoding="utf-8")
        frontmatter, body = self._split_frontmatter(text, path)
        if not frontmatter:
            raise ValueError(f"Frontmatter required in {path}")
        try:
            fm = yaml_loader.safe_load(frontmatter) or {}
        except Exception as exc:  # pragma: no cover - defensive; loader may raise
            raise ValueError(f"Failed to parse frontmatter in {path}: {exc}") from exc

        const = str(fm.get("id", "")).strip()
        if not const:
            raise ValueError(f"Missing required 'id' field in frontmatter for {path}")

        title = fm.get("title", const)
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
        )

    def _split_frontmatter(self, text: str, path: Path) -> Tuple[str, str]:
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                return parts[1], parts[2]
        raise ValueError(
            f"Missing frontmatter in {path}: expected leading '---' delimited block"
        )
