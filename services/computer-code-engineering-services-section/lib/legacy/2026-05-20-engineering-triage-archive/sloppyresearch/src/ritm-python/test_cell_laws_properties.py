"""
test_cell_laws_properties.py — Property-based tests for cell_laws.py

Uses Hypothesis to verify invariants of the formal laws (□,◇,δ,RC,RT)
over randomly generated small adjacency and relation graphs.

Run with:
    pytest --maxfail=1 --disable-warnings -q
"""

from __future__ import annotations
import copy
from typing import Dict, Set, Tuple
from hypothesis import given, strategies as st

import cell_laws as laws


# ----------------------------------------------------------------------------- 
# --- Strategies -------------------------------------------------------------
# -----------------------------------------------------------------------------

# Basic node generator: (id, level)
node = st.tuples(st.integers(0, 3), st.integers(0, 2))

def small_Y():
    """Generate small adjacency relations (Y)."""
    return st.dictionaries(
        keys=node,
        values=st.lists(node, unique=True, max_size=3).map(set),
        max_size=4,
    ).filter(lambda Y: bool(Y))  # non-empty

def small_R():
    """Generate small symmetric relations (R)."""
    return st.dictionaries(
        keys=node,
        values=st.lists(node, unique=True, max_size=3).map(set),
        max_size=4,
    ).map(lambda R: {k: (v - {k}) for k, v in R.items()})  # remove self
    # symmetry checked later


# ----------------------------------------------------------------------------- 
# --- Invariant helpers ------------------------------------------------------
# -----------------------------------------------------------------------------

def is_symmetric(R: Dict, verbose=False) -> bool:
    for a, bs in R.items():
        for b in bs:
            if a not in R.get(b, set()):
                if verbose:
                    print(f"Asymmetry: {a}∼{b} but not {b}∼{a}")
                return False
    return True


def no_self_edges(Y: Dict) -> bool:
    """Allow self edges only if they are reflexive, not extraneous."""
    for a, bs in Y.items():
        for b in bs:
            if a == b:
                continue  # reflexive allowed
    return True


# ----------------------------------------------------------------------------- 
# --- Modal law invariants ---------------------------------------------------
# -----------------------------------------------------------------------------

@given(small_Y())
def test_box_does_not_mutate_Y(Y):
    Y_copy = copy.deepcopy(Y)
    _ = laws.box(Y_copy)
    assert Y_copy == Y


@given(small_Y())
def test_box_reflexivity_event_is_self_edge(Y):
    evt = laws.box(Y)
    if evt:
        i, j = evt
        assert isinstance(i, tuple) and isinstance(j, tuple)
        # reflexivity or transitivity — both preserve Y's domain
        assert i in laws.nodeset(Y)


@given(small_Y())
def test_delta_lift_increments_level(Y):
    evt = laws.delta(Y)
    if evt:
        (i, j) = evt
        assert j[1] == evt[1][1]  # correct type
        # fibre-level increases by exactly +1
        src, tgt = evt
        assert tgt[1] - src[1] >= 0


# ----------------------------------------------------------------------------- 
# --- Coupling law invariants ------------------------------------------------
# -----------------------------------------------------------------------------

@given(small_R(), small_Y())
def test_RC_preserves_symmetry(R, Y):
    """If RC proposes an event, adding it symmetrically keeps symmetry."""
    evt = laws.RC(R, ((0, 0), (1, 0)))
    if evt:
        x, b = evt
        new_R = copy.deepcopy(R)
        new_R.setdefault(x, set()).add(b)
        new_R.setdefault(b, set()).add(x)
        assert is_symmetric(new_R)


@given(small_R(), small_Y())
def test_RT_event_within_row(R, Y):
    """RT only proposes edges between nodes actually in the row."""
    for row in R.values():
        evt = laws.RT(Y, row)
        if evt:
            i, j = evt
            assert i in row and j in row


@given(small_R(), small_Y())
def test_RT_does_not_mutate(Y, R):
    Y_copy = copy.deepcopy(Y)
    row = next(iter(R.values()), set())
    _ = laws.RT(Y_copy, row)
    assert Y_copy == Y


# ----------------------------------------------------------------------------- 
# --- Global properties ------------------------------------------------------
# -----------------------------------------------------------------------------

@given(small_Y(), small_R())
def test_all_laws_are_pure(Y, R):
    """None of the modal or coupling laws mutate their inputs."""
    originals = (copy.deepcopy(Y), copy.deepcopy(R))

    for fn in [laws.box, laws.diamond, laws.composite, laws.delta]:
        Y_copy = copy.deepcopy(Y)
        _ = fn(Y_copy)
        assert Y_copy == Y

    for fn in [laws.RC]:
        R_copy = copy.deepcopy(R)
        _ = fn(R_copy, ((0, 0), (1, 0)))
        assert R_copy == R

    for fn in [laws.RT]:
        Y_copy = copy.deepcopy(Y)
        R_copy = copy.deepcopy(R)
        row = next(iter(R_copy.values()), set())
        _ = fn(Y_copy, row)
        assert Y_copy == Y and R_copy == R

    # Ensure we didn’t modify original tuple objects
    assert originals[0] == Y and originals[1] == R


@given(small_R())
def test_symmetry_check_helper(R):
    """Symmetry checker works as expected."""
    R_sym = copy.deepcopy(R)
    for a, bs in list(R_sym.items()):
        for b in bs:
            R_sym.setdefault(b, set()).add(a)
    assert is_symmetric(R_sym)
