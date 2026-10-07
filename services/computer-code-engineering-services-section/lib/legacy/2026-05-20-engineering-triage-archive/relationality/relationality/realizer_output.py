from __future__ import annotations

"""
Shared realizer output type.

Realizers return a ``RealizerOutput`` instance describing:
- ``nodes``: newly constructed carrier payloads,
- ``edges``: edge payloads linking carriers, and
- ``bindings``: updated role → node-id environment for the runbook.

This dataclass is intentionally independent of any particular graph
implementation; it is consumed by both the legacy engine and the local
execution layer.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RealizerOutput:
    nodes: List[dict]
    edges: List[dict]
    bindings: Dict[str, str]


__all__ = ["RealizerOutput"]

