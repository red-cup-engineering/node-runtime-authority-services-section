"""Normalize term placeholder."""

from __future__ import annotations

from typing import List

from relationality.canonical import assign_canonical_id
from relationality.errors import LoaderError


def normalize_term(graph, payloads: List[dict], ctx=None):
    if len(payloads) != 1 or payloads[0].get("kind") != "term":
        raise LoaderError("normalize_term expects a single term")
    term = payloads[0]
    term_norm = dict(term)
    term_norm["normalized"] = True
    return [assign_canonical_id(term_norm)]
