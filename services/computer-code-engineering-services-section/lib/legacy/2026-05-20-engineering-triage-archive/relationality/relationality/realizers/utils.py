"""
Shared helpers for realizer modules.

Each realizer lives in its own module; utilities here avoid repeated boilerplate.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from relationality.models import RecognitionObject


def clone_payload(obj: RecognitionObject) -> Dict[str, Any]:
    """Deep-copy payload to preserve immutability semantics."""
    return deepcopy(obj.payload)
