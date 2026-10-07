"""
cell.py — Constructive Relational ∞-Topos Cell

Implements the *RelationalCell* object: the minimal constructive model
of the Relational ∞-Topos Modality (RITM) described in the formal document.

This class provides a mutable presheaf cell (Y,R) that enacts the
axiomatic laws defined in `cell_laws.py`.  Each event step applies
one modality or coupling rule (□,◇,C,δ,RC,RT), progressively generating
a self-stabilizing relational field.

Conceptual layering:
    cell_laws.py   — defines the pure axioms (stateless inference)
    cell.py        — enacts those axioms (constructive presheaf model)
    category.py    — formalizes them as functors, adjunctions, monads

Author: em senn
Date: 2025-10-17
"""

from __future__ import annotations
from typing import Optional, Tuple, List

from cell_rules import (
    Node, YAdj, RRel, YEvent, REvent,
    seed_one_arrow,
    box, diamond, composite, delta,
    RC, RT,
)


class RelationalCell:
    """
    The constructive presheaf cell implementing the Relational ∞-Topos Modality.

    Attributes:
        Y : dict[node, set[node]]
            Directed adjacency relation (spatial arrows)
        R : dict[node, set[node]]
            Symmetric relational coupling
    """

    def __init__(self, i_id: int = 0, j_id: int = 1):
        """Initialize cell with a single seed arrow i→j."""
        self.Y, self.R = seed_one_arrow(i_id, j_id)
        self.history: List[Tuple[str, Tuple[Node, Node]]] = []

    # -------------------------------------------------------------------------
    # --- Core dynamics -------------------------------------------------------
    # -------------------------------------------------------------------------

    def step(self, prefer: str = "Cδ") -> Optional[Tuple[str, Tuple[Node, Node]]]:
        """
        Execute one event according to the prioritized constructive rules.

        Order:
            1. C (composite = ◇ then □)
            2. RT (relational imprint)
            3. δ (local fibre lift)
        After any Y-event, apply one RC (relational coupling).

        Returns:
            (kind, event) if a new event occurs, or None if stable.
        """
        evt: Optional[YEvent] = None
        kind: Optional[str] = None

        # Step 1: composite (C)
        if prefer.startswith("C"):
            evt = composite(self.Y)
            kind = "C"

        # Step 2: relational imprint (RT)
        if evt is None:
            for row in self.R.values():
                evt = RT(self.Y, row)
                if evt:
                    kind = "RT"
                    break

        # Step 3: delta-lift (δ)
        if evt is None and "δ" in prefer:
            evt = delta(self.Y)
            kind = "δ"

        # Apply event if found
        if evt:
            i, j = evt
            self.Y.setdefault(i, set()).add(j)

            # RC coupling after any Y-edge
            rc_evt = RC(self.R, evt)
            if rc_evt:
                a, b = rc_evt
                self.R.setdefault(a, set()).add(b)
                self.R.setdefault(b, set()).add(a)

            self.history.append((kind, evt))
            return kind, evt

        return None

    # -------------------------------------------------------------------------
    # --- Iterative dynamics --------------------------------------------------
    # -------------------------------------------------------------------------

    def run(self, steps: int = 1_000, prefer: str = "Cδ") -> None:
        """
        Run successive step() calls until stability or step limit reached.
        """
        for _ in range(steps):
            event = self.step(prefer=prefer)
            if event is None:
                break

    # -------------------------------------------------------------------------
    # --- Inspection utilities ------------------------------------------------
    # -------------------------------------------------------------------------

    def node_count(self) -> int:
        """Return total number of distinct nodes present in Y."""
        return len({n for src, dsts in self.Y.items() for n in [src, *dsts]})

    def edge_count(self) -> int:
        """Return total number of directed edges in Y."""
        return sum(len(dsts) for dsts in self.Y.values())

    def relation_count(self) -> int:
        """Return total number of symmetric relations in R."""
        return sum(len(v) for v in self.R.values()) // 2

    def summary(self) -> str:
        """Return a brief textual summary of current cell state."""
        return (
            f"RelationalCell: {self.node_count()} nodes, "
            f"{self.edge_count()} edges, "
            f"{self.relation_count()} relations"
        )

    def __repr__(self) -> str:
        return self.summary()


# -----------------------------------------------------------------------------
# --- Demonstration -----------------------------------------------------------
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    cell = RelationalCell()
    print("Initial:", cell.summary())

    for i in range(20):
        event = cell.step()
        if event is None:
            print(f"Stable after {i} steps.")
            break
        kind, (a, b) = event
        print(f"Step {i:02d}: {kind} {a} → {b}")

    print("Final:", cell.summary())
