from __future__ import annotations

"""In-memory registry for recognition fibres.

This provides a minimal shared store so that other components (e.g.,
sheaf builders, runbooks) can look up fibres by id without reaching
into ad-hoc lists or dicts.
"""

from typing import Dict, Iterable, List, Optional
from uuid import UUID

from app.schemas.fibers.recognition_fiber import RecognitionFiber

_FIBERS: Dict[UUID, RecognitionFiber] = {}


def register_fiber(fiber: RecognitionFiber) -> None:
    """Register or update a fibre in the registry."""
    _FIBERS[fiber.id] = fiber


def get_fiber(fiber_id: UUID) -> Optional[RecognitionFiber]:
    """Look up a fibre by id."""
    return _FIBERS.get(fiber_id)


def list_fibers() -> List[RecognitionFiber]:
    """Return all fibres currently in the registry."""
    return list(_FIBERS.values())


def clear_registry() -> None:
    """Remove all fibres from the registry (for tests)."""
    _FIBERS.clear()

