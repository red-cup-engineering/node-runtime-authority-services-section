"""
Canonical serialization and hashing utilities.

The specification requires every carrier and runbook to be hashed on its
canonical JSON representation with the ``id`` field omitted.  Canonicalization
uses sorted keys and compact separators to remove incidental formatting noise.
"""

from __future__ import annotations

import copy
import hashlib
import json
from fractions import Fraction
from typing import Any, Iterable, Mapping, MutableMapping, Sequence


def _drop_keys(obj: Any, keys: Iterable[str]) -> Any:
    """
    Recursively drop a set of keys from mappings while preserving list order.
    """
    if isinstance(obj, Mapping):
        return {k: _drop_keys(v, keys) for k, v in obj.items() if k not in keys}
    if isinstance(obj, list):
        return [_drop_keys(v, keys) for v in obj]
    return obj


def canonicalize_json(payload: Any) -> str:
    """
    Convert a JSON-serializable payload into its canonical string form.

    Rules:
    - keys are sorted
    - ASCII-only output
    - compact separators without whitespace
    - list order is preserved as provided
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def hash_canonical_json(payload: Any, drop_keys: Iterable[str] = ("id",)) -> str:
    """
    Compute the SHA256 of the canonical JSON form of ``payload`` with ``drop_keys``
    removed from every mapping level.
    """
    cleaned = _drop_keys(copy.deepcopy(payload), set(drop_keys))
    canonical = canonicalize_json(cleaned)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ensure_id_coherence(payload: MutableMapping[str, Any], *, drop_keys: Iterable[str] = ("id",)) -> str:
    """
    Normalize ``payload["id"]`` to the canonical hash.

    This function is appropriate at construction time or after deliberate,
    in-memory edits to a payload: it *always* overwrites any existing ``id``
    field with the canonical hash computed from the payload (with
    ``drop_keys`` removed) and returns that hash.

    Persisted carriers and edges, where an unexpected mismatch between the
    stored id and the canonical hash is a hard error, must be checked with
    :func:`assert_id_coherence` instead.
    """
    computed = hash_canonical_json(payload, drop_keys=drop_keys)
    payload["id"] = computed
    return computed


def assert_id_coherence(payload: Mapping[str, Any], *, drop_keys: Iterable[str] = ("id",)) -> str:
    """
    Assert that ``payload["id"]`` already matches the canonical hash.

    This function does not mutate ``payload``. It raises ``ValueError`` if the
    ``id`` field is missing or does not equal the canonical hash. It is the
    appropriate check at persistence and AOG-boundary points, enforcing the
    \"no mismatches\" law from the specification.
    """
    computed = hash_canonical_json(payload, drop_keys=drop_keys)
    existing = payload.get("id")
    if existing is None:
        raise ValueError("payload is missing required 'id' field")
    if existing != computed:
        raise ValueError(f"id mismatch: payload has {existing} but canonical hash is {computed}")
    return existing


def sorted_unique(seq: Sequence[str]) -> list[str]:
    """
    Return a deterministically sorted list of unique strings.

    Many carriers treat enumerations (elements, states, observations) as sets.
    Sorting ensures canonical ordering without introducing new information.
    """
    return sorted(dict.fromkeys(seq))


def fraction_to_canonical_string(value: Fraction) -> str:
    """
    Render a Fraction as a canonical JSON string.

    Canonical form:
    - integers are rendered as their decimal representation (e.g. 0, -1, 2);
    - non-integers are rendered as \"numerator/denominator\" with no spaces
      (e.g. 1/2, -3/4).

    This ensures a unique textual representation for each rational, so that
    JSON schemas can use strings for scalar values without losing exactness.
    """
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"
