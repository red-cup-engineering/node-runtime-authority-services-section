"""
cell_rules.py

Each function corresponds directly to a modality or coupling operation
from the formal RITM structure:

    □   — "box" : reflexive/transitive closure on Y
    ◇   — "diamond" : closure on the transpose of Y
    C   — "composite" : ◇ followed by □
    δ   — "delta" : local fibre lift creating higher-level targets
    RC  — relational coupling propagation (x∼a & a→b ⇒ x∼b)
    RT  — relational imprint: rows of R yield cliques in Y

These laws are imported by `cell.py`, which instantiates a concrete
RelationalCell object that enacts them dynamically.
"""

from __future__ import annotations
from typing import Dict, Set, Tuple, Optional

# ----------------------------------------------------------------------------- 
# --- Type definitions --------------------------------------------------------
# -----------------------------------------------------------------------------

Node = Tuple[int, int]       # (identifier, fibre-level)
YAdj = Dict[Node, Set[Node]] # directed adjacency (Y: morphisms)
RRel = Dict[Node, Set[Node]] # symmetric relational coupling (R: relations)
YEvent = Tuple[Node, Node]   # proposed arrow addition
REvent = Tuple[Node, Node]   # proposed relation addition


# ----------------------------------------------------------------------------- 
# --- Core utilities ----------------------------------------------------------
# -----------------------------------------------------------------------------

def nodeset(Y: YAdj) -> Set[Node]:
    """Return all nodes appearing in Y (sources or targets)."""
    s = set(Y.keys())
    for js in Y.values():
        s |= js
    return s


def transpose_Y(Y: YAdj) -> YAdj:
    """Return the transpose of Y (reverse all arrows)."""
    T: YAdj = {n: set() for n in nodeset(Y)}
    for i, js in Y.items():
        for j in js:
            T.setdefault(j, set()).add(i)
    return T


# ----------------------------------------------------------------------------- 
# --- Modal laws --------------------------------------------------------------
# -----------------------------------------------------------------------------

def box(Y: YAdj) -> Optional[YEvent]:
    """
    □ — Reflexive/transitive closure on Y.
    Returns the next missing reflexive or transitive edge, if any.
    """
    ns = sorted(nodeset(Y))
    # Reflexivity: add (a,a) if missing
    for a in ns:
        if a not in Y or a not in Y[a]:
            return (a, a)
    # Transitivity: add (i,k) if i→j and j→k but not i→k
    for i in ns:
        for j in sorted(Y.get(i, ())):
            for k in sorted(Y.get(j, ())):
                if k not in Y.get(i, ()):
                    return (i, k)
    return None


def diamond(Y: YAdj) -> Optional[YEvent]:
    """
    ◇ — Closure computed on the transpose of Y, mirrored back into Y.

    Rules on the transpose T:
        D2: a -> a      (reflexivity)
        D1: j->k & k->i ⇒ j->i
    Mirrored back to Y as (i -> j).
    """
    T = transpose_Y(Y)
    ns = sorted(nodeset(T))

    # Reflexivity on T ⇒ (a,a) in Y
    for a in ns:
        if a not in Y or a not in Y.get(a, ()):
            return (a, a)

    # Transitivity on T ⇒ (i->j) in Y
    for j in ns:
        for k in sorted(T.get(j, ())):
            for i in sorted(T.get(k, ())):
                if j not in Y.get(i, ()):
                    return (i, j)
    return None


def composite(Y: YAdj) -> Optional[YEvent]:
    """C = □∘◇ — compute ◇ first, then □."""
    d = diamond(Y)
    if d:
        return d
    return box(Y)


def delta(Y: YAdj) -> Optional[YEvent]:
    """
    δ — Local-fibre lift.
    For each i→j, propose i→(j_id, j_lvl+1) if missing.
    Ensures indefinite expansion (non-stabilization).
    """
    for i, js in list(Y.items()):
        for j in list(js):
            lifted = (j[0], j[1] + 1)
            if lifted not in Y.get(i, ()):
                return (i, lifted)
    return None


# ----------------------------------------------------------------------------- 
# --- Coupling and imprint laws ----------------------------------------------
# -----------------------------------------------------------------------------

def RC(R: RRel, e: YEvent) -> Optional[REvent]:
    """
    RC — Relational coupling propagation.
    If x∼a and a→b, propose x∼b.
    """
    a, b = e
    for x, ys in R.items():
        if a in ys and b not in ys:
            return (x, b)
    return None


def RT(Y: YAdj, row: Set[Node]) -> Optional[YEvent]:
    """
    RT — Relational imprint.
    Given a row (set of related nodes) from R,
    propose one missing oriented edge i→j between its members.
    """
    for i in row:
        for j in row:
            if j not in Y.get(i, ()):
                return (i, j)
    return None


# ----------------------------------------------------------------------------- 
# --- Seeding convenience -----------------------------------------------------
# -----------------------------------------------------------------------------

def seed_one_arrow(i_id: int, j_id: int) -> Tuple[YAdj, RRel]:
    """
    Construct initial Y and R with a single arrow i→j and symmetric relation i∼j.
    Used for bootstrapping the minimal relational cell.
    """
    i = (i_id, 0)
    j = (j_id, 0)
    Y: YAdj = {i: {j}}
    R: RRel = {i: {j}, j: {i}}
    return Y, R


# ----------------------------------------------------------------------------- 
# --- Law registry (optional convenience) ------------------------------------
# -----------------------------------------------------------------------------

MODAL_LAWS = {
    "box": box,
    "diamond": diamond,
    "C": composite,
    "delta": delta,
}

COUPLING_LAWS = {
    "RC": RC,
    "RT": RT,
}

__all__ = [
    "Node", "YAdj", "RRel", "YEvent", "REvent",
    "nodeset", "transpose_Y",
    "box", "diamond", "composite", "delta",
    "RC", "RT", "seed_one_arrow",
    "MODAL_LAWS", "COUPLING_LAWS",
]
