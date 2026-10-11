from __future__ import annotations

"""Repository fingerprint utilities.

A lightweight fingerprint tracks the state of the repository at evaluation time
so manifests can record which snapshot produced a projection. The fingerprint
prefers Git metadata when available and falls back to a content hash otherwise.
"""

import hashlib
import subprocess
from pathlib import Path


def compute_repo_fingerprint(root: Path) -> str:
    """Return a stable fingerprint for the repository at ``root``.

    The function prefers Git metadata for efficiency and traceability. If Git is
    unavailable, it hashes the file layout under ``root`` as a conservative
    fallback.
    """

    root = root.resolve()
    try:
        head = (
            subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
        status = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"], stderr=subprocess.DEVNULL
        ).decode()
        dirty = hashlib.sha256(status.encode()).hexdigest()[:8] if status else "clean"
        return f"git:{head}:{dirty}"
    except Exception:
        pass

    h = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root)
            h.update(str(rel).encode())
            try:
                h.update(path.read_bytes())
            except Exception:
                continue
    return f"hash:{h.hexdigest()}"
