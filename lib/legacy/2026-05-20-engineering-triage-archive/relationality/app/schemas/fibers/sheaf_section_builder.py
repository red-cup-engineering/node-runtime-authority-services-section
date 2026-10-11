from __future__ import annotations

"""Helpers for building small sheaf sections from recognition fibres."""

from typing import Iterable, List

from app.schemas.fibers.recognition_fiber import RecognitionFiber
from app.schemas.fibers.registry import list_fibers
from app.schemas.hypertensor import LatticeSite, LatticeWindow, SheafSection


def build_sheaf_section_from_fibers(fibers: Iterable[RecognitionFiber]) -> SheafSection:
    """Build a 1D sheaf section whose sites are in bijection with fibres.

    Each fibre is placed at a consecutive lattice index (0,), (1,), ...
    and the site's `recognition_id` is the stringified fibre id.
    """
    fibers_list: List[RecognitionFiber] = list(fibers)

    sites: List[LatticeSite] = []
    for i, fibre in enumerate(fibers_list):
        sites.append(
            LatticeSite(
                index=(i,),
                recognition_id=str(fibre.id),
                metadata={},
            )
        )

    window = LatticeWindow(dimension=1, sites=sites, metadata={})
    return SheafSection(window=window, towers=[], metadata={})


def build_sheaf_section_from_registry() -> SheafSection:
    """Build a sheaf section from all fibres in the registry."""
    return build_sheaf_section_from_fibers(list_fibers())

