from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict

from . import yaml_loader


DEFAULT_CONFIG = {
    "sources": "content/**/*.md",
    "publish": {"mode": "permissive", "outputs": {}, "filters": {}},
    "identity": {"prefer_frontmatter_id": True, "allow_hash_ids": True},
    "annterm": {"source": "frontmatter", "key": "ann"},
    "groupoid": {"key": "same_as"},
    "html": {
        "sanitize": True,
        "mathjax": False,
        "lang": "en",
        "assets": {"inline": True, "minify": False},
    },
    "cache": {"enabled": True, "location": None, "keyed_by": []},
}


@dataclasses.dataclass
class UniverseConfig:
    data: Dict[str, Any]
    location: Path | None

    @classmethod
    def load(cls, path: str | os.PathLike | None) -> "UniverseConfig":
        base = json.loads(json.dumps(DEFAULT_CONFIG))
        location: Path | None = None
        if path:
            location = Path(path)
            with open(location, "r", encoding="utf-8") as f:
                user_data = yaml_loader.safe_load(f.read()) or {}
            base = _merge(base, user_data)
        return cls(data=base, location=location)

    def mode(self, override: str | None = None) -> str:
        return override or self.data.get("publish", {}).get("mode", "permissive")

    def publish_filters(self) -> Dict[str, Any]:
        return self.data.get("publish", {}).get("filters", {}) or {}

    def hash(self) -> str:
        h = hashlib.sha256(json.dumps(self.data, sort_keys=True).encode()).hexdigest()
        return h


def _merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            result[k] = _merge(base[k], v)
        else:
            result[k] = v
    return result
