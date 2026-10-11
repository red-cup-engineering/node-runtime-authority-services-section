"""
events.py — Constructive Relational Infinity Topos Modality (RITM) event engine

Implements one-step consequence generation for the constructive relational
∞-topos model described in the accompanying formal document.

Core objects:
    Y : dict[node, set[node]]
        Oriented adjacency relation (the “spatial” arrows of the topos cell)
    R : dict[node, set[node]]
        Relational coupling; propagates via RC, imprints via RT

Each event step introduces exactly one new arrow in Y or R according to
the logical modalities:
    □  — reflexive/transitive closure on Y
    ◇  — same on transpose(Y)
    C  — composite (◇ then □)
    δ  — local fibre lift of Y
    RC — R–propagation over Y-edges
    RT — R–imprint: rows of R yield cliques in Y
"""

from __future__ import annotations
from typing import Dict, Set, Tuple, Optional

Node = Tuple[int, int]
YAdj = Dict[Node, Set[Node]]
RRel = Dict[Node, Set[Node]]
YEvent = Tuple[Node, Node]
REvent = Tuple[Node, Node]


# -----------------------------------------------------------------------------
# --- Basic utilities ---------------------------------------------------------
# -----------------------------------------------------------------------------

def add_Y(Y: YAdj, i: Node, j: Node) -> None:
    """Add an arrow i→j to Y (initializes source if missing)."""
    Y.setdefault(i, set()).add(j)


def add_R(R: RRel, i: Node, j: Node) -> None:
    """Add a relational link i∼j to R (symmetric)."""
    R.setdefault(i, set()).add(j)
    R.setdefault(j, set()).add(i)


def nodeset(Y: YAdj) -> Set[Node]:
    """All nodes mentioned in Y (as sources or targets)."""
    s = set(Y.keys())
    for js in Y.values():
        s |= js
    return s


def transpose_Y(Y: YAdj) -> YAdj:
    """
    Return the transpose of Y (reverse all arrows).
    Ensures all nodes appear as keys in the returned adjacency dict.
    """
    T: YAdj = {}
    # ensure all nodes appear as keys for determinism
    for n in nodeset(Y):
        T.setdefault(n, set())
    for i, js in Y.items():
        for j in js:
            T.setdefault(j, set()).add(i)
    # make sure all referenced nodes are present as keys
    for k in list(T):
        T.setdefault(k, set())
    return T


# -----------------------------------------------------------------------------
# --- Seeding -----------------------------------------------------------------
# -----------------------------------------------------------------------------

def seed_one_arrow(i_id: int, j_id: int) -> Tuple[YAdj, RRel]:
    """Seed Y and R with a single arrow i→j and relation i∼j."""
    i = (i_id, 0)
    j = (j_id, 0)
    Y: YAdj = {i: {j}}
    R: RRel = {i: {j}, j: {i}}
    return Y, R


# -----------------------------------------------------------------------------
# --- RC and RT coupling ------------------------------------------------------
# -----------------------------------------------------------------------------

def propagate_R_over_edge(R: RRel, e: YEvent) -> Optional[REvent]:
    """
    RC — If x∼a and a→b, add x∼b.
    """
    a, b = e
    for x, ys in R.items():
        if a in ys and b not in ys:
            return (x, b)
    return None


def imprint_from_R_row(Y: YAdj, row: Set[Node]) -> Optional[YEvent]:
    """
    RT — Imprint a clique in Y from a given R-row.
    Adds one missing oriented pair y_p→y_q at a time.
    """
    for i in row:
        for j in row:
            if j not in Y.get(i, ()):
                return (i, j)
    return None


# -----------------------------------------------------------------------------
# --- Modal closures ----------------------------------------------------------
# -----------------------------------------------------------------------------

def find_box_consequence(Y: YAdj) -> Optional[YEvent]:
    """
    □ — Reflexive/transitive closure on Y.
    Adds one missing reflexive or transitive edge per call.
    """
    ns = sorted(nodeset(Y))
    # reflexivity
    for a in ns:
        if a not in Y or a not in Y[a]:
            return (a, a)
    # transitivity
    for i in ns:
        for j in sorted(Y.get(i, ())):
            for k in sorted(Y.get(j, ())):
                if k not in Y.get(i, ()):
                    return (i, k)
    return None


def find_diamond_consequence(Y: YAdj) -> Optional[YEvent]:
    """
    ◇ — Consequence generation on the transpose T of Y,
    mirrored back into Y.

    Rules on T:
        D2: a -> a      (reflexivity)
        D1: j->k & k->i ⇒ j->i
    Mirrored to Y:
        (i -> j)
    """
    T = transpose_Y(Y)
    ns = sorted(nodeset(T))

    # D2 on T ⇒ (a->a) in Y
    for a in ns:
        if a not in Y or a not in Y.get(a, ()):
            return (a, a)

    # D1 on T ⇒ (i->j) in Y
    for j in ns:
        for k in sorted(T.get(j, ())):
            for i in sorted(T.get(k, ())):
                if j not in Y.get(i, ()):
                    return (i, j)
    return None


def find_C_consequence(Y: YAdj) -> Optional[YEvent]:
    """C = □∘◇ — compute ◇ first, then □."""
    d = find_diamond_consequence(Y)
    if d:
        return d
    return find_box_consequence(Y)


# -----------------------------------------------------------------------------
# --- δ-lift (local fibre extension) -----------------------------------------
# -----------------------------------------------------------------------------

def find_delta_lift(Y: YAdj) -> Optional[YEvent]:
    """
    δ — Local-fibre lift: for each i→j, add i→(j_id, j_lvl+1).
    Ensures non-stabilization by always creating a higher-level target.
    """
    for i, js in list(Y.items()):
        for j in list(js):
            lifted = (j[0], j[1] + 1)
            if lifted not in Y.get(i, ()):
                return (i, lifted)
    return None


# -----------------------------------------------------------------------------
# --- Step driver -------------------------------------------------------------
# -----------------------------------------------------------------------------

def step_event(R: RRel, Y: YAdj, prefer: str = "Cδ") -> Optional[Tuple[str, YEvent]]:
    """
    Execute exactly one event in priority order:
      1. C (◇ then □)
      2. RT (imprint clique)
      3. δ (local lift)
    After any Y-event, apply one RC propagation if available.
    Returns (kind, event) or None if stable.
    """
    evt: Optional[YEvent] = None
    kind: Optional[str] = None

    if prefer.startswith("C"):
        evt = find_C_consequence(Y)
        kind = "C"
    if evt is None:
        # RT
        for row in R.values():
            evt = imprint_from_R_row(Y, row)
            if evt:
                kind = "RT"
                break
    if evt is None and "δ" in prefer:
        evt = find_delta_lift(Y)
        kind = "δ"

    if evt:
        add_Y(Y, *evt)
        # RC after any new Y-edge
        rc_evt = propagate_R_over_edge(R, evt)
        if rc_evt:
            add_R(R, *rc_evt)
        return (kind, evt)
    return None


# -----------------------------------------------------------------------------
# --- End of module -----------------------------------------------------------
# -----------------------------------------------------------------------------
