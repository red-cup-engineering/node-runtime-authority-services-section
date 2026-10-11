"""Entropy measurement placeholder."""

from __future__ import annotations

from typing import List

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def entropy_measurement(graph, payloads: List[dict], ctx=None):
    if len(payloads) != 1 or payloads[0].get("kind") != "mixing_evidence":
        raise LoaderError("entropy_measurement expects mixing_evidence")
    entropy = assign_canonical_id({"kind": "entropy_measurement", "values": [0.0]})
    return [entropy]
