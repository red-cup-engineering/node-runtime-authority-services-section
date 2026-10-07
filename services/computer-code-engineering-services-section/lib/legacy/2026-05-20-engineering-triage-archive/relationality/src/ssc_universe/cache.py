from __future__ import annotations

import hashlib
import os
import pickle
from datetime import datetime
from importlib import metadata
from pathlib import Path
from typing import Optional

from .config import UniverseConfig
from .repo import compute_repo_fingerprint
from .sscu_model import Concept, UniverseInstance


TOOL_PACKAGE_NAME = "ssc-universe"


def resolve_version() -> str:
    try:
        return metadata.version(TOOL_PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        # Fallback for editable installs
        return "0.0.0"


def default_cache_dir(location: Optional[str]) -> Path:
    if location:
        loc_path = Path(location)
        return loc_path if loc_path.is_absolute() else loc_path.expanduser().resolve()
    base = os.getenv("XDG_CACHE_HOME")
    base_path = Path(base) if base else Path.home() / ".cache"
    return base_path / "ssc_universe"


class CacheManager:
    """Simple content-hash-based cache for UniverseInstance evaluation results."""

    def __init__(self, config: UniverseConfig, root: Path, sources_pattern: str, version: str | None = None):
        self.config = config
        self.root = root
        self.sources_pattern = sources_pattern
        self.version = version or resolve_version()
        self.signature = self._compute_signature()
        self.cache_dir = default_cache_dir(self.config.data.get("cache", {}).get("location"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.cache_dir / f"{self.signature}.pkl"

    def _compute_signature(self) -> str:
        h = hashlib.sha256()
        h.update(self.config.hash().encode())
        h.update(self.version.encode())
        keyed_by = self.config.data.get("cache", {}).get("keyed_by", []) or []
        for extra in keyed_by:
            h.update(str(extra).encode())
        for path in sorted(self.root.glob(self.sources_pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(self.root)
            h.update(str(rel).encode())
            h.update(path.read_bytes())
        return h.hexdigest()

    def _load_path(self, path: Path) -> Optional[UniverseInstance]:
        if not path.exists():
            return None
        try:
            instance = pickle.loads(path.read_bytes())
            if not getattr(instance, "repo_fingerprint", None):
                instance.repo_fingerprint = compute_repo_fingerprint(self.root)
            if not getattr(instance, "canonical_concepts", None):
                class_map: dict[str, list[Concept]] = {}
                for concept in instance.concepts.values():
                    rep = instance.groupoid_rep.get(concept.const, concept.const)
                    class_map.setdefault(rep, []).append(concept)
                canonical_concepts: dict[str, Concept] = {}
                equivalence_classes: dict[str, list[str]] = {}
                for rep, members in class_map.items():
                    ordered = sorted(members, key=lambda c: (c.const != rep, c.const))
                    primary = ordered[0]
                    tags = sorted({t for c in ordered for t in c.tags})
                    ann_terms = []
                    same_as = set()
                    publish = primary.publish
                    publish_to = set(getattr(primary, "publish_to", []) or [])
                    status = getattr(primary, "status", None)
                    for concept in ordered:
                        ann_terms.extend(getattr(concept, "ann", []))
                        same_as.update(getattr(concept, "same_as", []))
                        if publish is None:
                            publish = getattr(concept, "publish", None)
                        publish_to.update(getattr(concept, "publish_to", []) or [])
                        if status is None:
                            status = getattr(concept, "status", None)
                    same_as.update(c.const for c in ordered)
                    same_as.discard(rep)
                    canonical_concepts[rep] = Concept(
                        const=rep,
                        title=primary.title,
                        tags=tags,
                        ann=ann_terms,
                        body=primary.body,
                        same_as=sorted(same_as),
                        publish=publish,
                        publish_to=sorted(publish_to),
                        status=status,
                    )
                    equivalence_classes[rep] = sorted(c.const for c in ordered)
                instance.canonical_concepts = canonical_concepts
                instance.equivalence_classes = equivalence_classes
            # Backfill equivalence classes to include declared aliases even when
            # older cache entries omitted them.
            classes: dict[str, set[str]] = {}
            for rep, concept in getattr(instance, "canonical_concepts", {}).items():
                current_rep = getattr(instance, "groupoid_rep", {}).get(rep, rep)
                classes.setdefault(current_rep, set()).add(rep)
                for alias in getattr(concept, "same_as", []):
                    alias_rep = getattr(instance, "groupoid_rep", {}).get(alias, current_rep)
                    classes.setdefault(alias_rep, set()).add(alias)
            for rep, members in getattr(instance, "equivalence_classes", {}).items():
                existing = classes.setdefault(rep, set())
                existing.update(members)
            instance.equivalence_classes = {rep: sorted(vals) for rep, vals in classes.items()}
            if not hasattr(instance, "html_lang"):
                instance.html_lang = "en"
            if not hasattr(instance, "source_paths"):
                instance.source_paths = {}
            return instance
        except Exception:
            return None

    def load(self) -> Optional[UniverseInstance]:
        return self._load_path(self.cache_path)

    def load_latest(self) -> Optional[UniverseInstance]:
        candidates = sorted(self.cache_dir.glob("*.pkl"), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in candidates:
            instance = self._load_path(path)
            if instance:
                return instance
        return None

    def store(self, instance: UniverseInstance) -> None:
        data = pickle.dumps(instance)
        tmp_path = self.cache_path.with_suffix(".tmp")
        tmp_path.write_bytes(data)
        tmp_path.replace(self.cache_path)

    def list_entries(self) -> list[Path]:
        """List available cache artifacts in the configured directory.

        Entries are returned sorted by modification time descending to surface the
        most recent evaluations first.
        """

        return sorted(self.cache_dir.glob("*.pkl"), key=lambda p: p.stat().st_mtime, reverse=True)

    def entry_info(self, path: Path) -> dict:
        """Inspect a cache entry for reporting purposes.

        The returned dictionary includes signature, mtime, size, and lightweight
        evaluation details when the cache artifact can be loaded (constant count
        and repo fingerprint). Any load errors are swallowed to keep listing
        resilient.
        """

        stat = path.stat()
        info: dict[str, object] = {
            "path": path,
            "signature": path.stem,
            "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "size": stat.st_size,
        }
        instance = self._load_path(path)
        if instance:
            info["constants"] = len(getattr(instance, "concepts", {}))
            info["repo_fingerprint"] = getattr(instance, "repo_fingerprint", None)
        return info

    def path_for_signature(self, signature: str | None = None) -> Path:
        target = signature or self.signature
        return self.cache_dir / f"{target}.pkl"

    def clear(self, all_entries: bool = False, signature: str | None = None) -> list[Path]:
        """Remove cache artifacts.

        When ``all_entries`` is False, only the current signature's cache file is
        removed. When True, every cache artifact in the configured cache
        directory is deleted. Returns the list of removed paths for reporting.
        """

        removed: list[Path] = []
        if all_entries:
            for path in self.cache_dir.glob("*.pkl"):
                try:
                    path.unlink()
                    removed.append(path)
                except FileNotFoundError:
                    continue
            return removed

        cache_path = self.path_for_signature(signature)
        try:
            cache_path.unlink()
            removed.append(cache_path)
        except FileNotFoundError:
            pass
        return removed
