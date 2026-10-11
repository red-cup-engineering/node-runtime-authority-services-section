from __future__ import annotations

"""Manifest construction for SSCU projections.

The manifest is an audit-friendly summary of a build invocation. It captures the
artifacts emitted, the constants included in the projection, unresolved
references, and a small sample of failures in F_X. The manifest is intended to
be written alongside projection outputs and also printed to stdout by the CLI.
"""

from typing import Dict, Iterable, List

from .sscu_model import UniverseInstance


def build_manifest(
    instance: UniverseInstance,
    artifacts: Iterable[str],
    projection: str,
    mode: str,
    cache_status: str = "miss",
    delta: Dict | None = None,
    assets: Iterable[Dict] | None = None,
    constants: Iterable[str] | None = None,
    filters: Dict | None = None,
    unresolved: List[tuple[str, str]] | None = None,
) -> Dict:
    """Construct a manifest dictionary for the current projection.

    Parameters
    ----------
    instance:
        Evaluated SSCU instance capturing Ann_X, fragments, Sem_X, failures, and
        unresolved references.
    artifacts:
        Relative artifact paths that will be emitted by the sink.
    projection:
        Projection identifier (e.g., ``site:static`` or ``single:html``).
    mode:
        Strict or permissive mode used for the build.
    cache_status:
        Optional cache status flag for future extensions. Defaults to ``miss``.
    """

    constant_list = sorted(constants) if constants is not None else sorted({instance.representative(k) for k in instance.concepts})
    failures_list: List[str] = [str(f) for f in instance.failures]
    unresolved_list = unresolved if unresolved is not None else instance.unresolved
    manifest = {
        "projection": projection,
        "mode": mode,
        "config_hash": instance.config_hash,
        "repo": {"fingerprint": instance.repo_fingerprint},
        "artifacts": list(artifacts),
        "constants": constant_list,
        "unresolved": unresolved_list,
        "failures": {"count": len(failures_list), "samples": failures_list[:5]},
        "cache": {"status": cache_status},
        "equivalence_classes": instance.equivalence_classes,
    }
    if delta is not None:
        manifest["delta"] = delta
    if assets is not None:
        manifest["assets"] = list(assets)
    if filters:
        manifest["filters"] = filters
    return manifest

