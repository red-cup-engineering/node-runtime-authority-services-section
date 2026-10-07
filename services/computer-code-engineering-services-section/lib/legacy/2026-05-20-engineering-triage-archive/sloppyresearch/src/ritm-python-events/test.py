"""
test_equivalence.py — Equivalence tests between events.py and the formalism

Goals:
1) Define a clear 'reference semantics' straight from the math:
     - □(Y): reflexive/transitive closure of Y
     - ◇(Y): mirror( □(transpose(Y)) ) ∪ Y
     - C(Y):  □( ◇(Y) )
     - RT, RC: mutual least fixpoint without δ

2) Show the simulator's saturation (applying its one-step rules repeatedly)
   yields EXACTLY the reference results.

3) Check critical algebraic properties the formalism claims:
     - □ idempotent, ◇ idempotent
     - □ and ◇ commute:  □(◇(Y)) == ◇(□(Y))
     - ◇(Y) == mirror( □(transpose(Y)) ) ∪ Y
     - Monotonicity of □, ◇
"""

import copy
import itertools
import rts


# ---------------------------
# Utilities
# ---------------------------

def edgeset(Y):
    """Return set of (i,j) arrows from adjacency dict."""
    return {(i, j) for i, js in Y.items() for j in js}

def mkY(edges):
    """Build adjacency dict from an edge set."""
    Y = {}
    for i, j in edges:
        rts.add_Y(Y, i, j)
    return Y

def nodes_of(Y, R=None):
    """All nodes mentioned in Y (sources/targets) and optionally in R."""
    ns = set(rts.nodeset(Y))
    if R is not None:
        ns |= set(R.keys())
        for s in R.values():
            ns |= set(s)
    return ns


# ---------------------------
# Reference semantics (math)
# ---------------------------

def ref_box(Y0):
    """□ — reflexive/transitive closure (least fixed point)."""
    ns = nodes_of(Y0)
    E = set(edgeset(Y0))
    # Reflexive
    for a in ns:
        E.add((a, a))
    # Transitive until fixpoint
    changed = True
    while changed:
        changed = False
        newE = set(E)
        for (i,j) in list(E):
            for (j2,k) in list(E):
                if j2 == j and (i,k) not in E:
                    newE.add((i,k))
                    changed = True
        E = newE
    return mkY(E)

def ref_diamond(Y0):
    """◇ — mirror( □(transpose(Y)) ) ∪ Y"""
    T = rts.transpose_Y(Y0)
    T_cl = ref_box(T)
    # mirror: (j->i) in T_cl gives (i->j) for diamond
    mirrored = {(i, j) for j, js in T_cl.items() for i in js}
    return mkY(edgeset(Y0) | mirrored)

def ref_C(Y0):
    """C = □∘◇."""
    return ref_box(ref_diamond(Y0))


# ---------------------------
# Simulator saturations
# ---------------------------

def sat_box(Y0):
    Y = copy.deepcopy(Y0)
    while True:
        e = rts.find_box_consequence(Y)
        if not e:
            break
        rts.add_Y(Y, *e)
    return Y

def sat_diamond(Y0):
    Y = copy.deepcopy(Y0)
    while True:
        e = rts.find_diamond_consequence(Y)
        if not e:
            break
        rts.add_Y(Y, *e)
    return Y

def sat_C(Y0):
    Y = copy.deepcopy(Y0)
    while True:
        d = rts.find_diamond_consequence(Y)
        if d:
            rts.add_Y(Y, *d)
            continue
        b = rts.find_box_consequence(Y)
        if b:
            rts.add_Y(Y, *b)
            continue
        break
    return Y


# ---------------------------
# RC/RT mutual closure (no δ)
# ---------------------------

def ref_rc_rt_closure(Y0, R0):
    """Reference least fixed point applying RT then RC to saturation."""
    Y = copy.deepcopy(Y0)
    R = {k: set(v) for k, v in copy.deepcopy(R0).items()}

    # Ensure symmetry in R
    for a in list(R):
        for b in list(R[a]):
            rts.add_R(R, a, b)

    while True:
        changed = False

        # RT: every row becomes a clique in Y
        to_add_Y = set()
        for row in R.values():
            for i in row:
                for j in row:
                    if j not in Y.get(i, ()):
                        to_add_Y.add((i, j))
        for e in to_add_Y:
            rts.add_Y(Y, *e)
        changed |= bool(to_add_Y)

        # RC: propagate R across all Y edges (snapshot)
        Y_edges = list(edgeset(Y))
        to_add_R = set()
        for (a, b) in Y_edges:
            for x, ys in R.items():
                if a in ys and b not in ys:
                    to_add_R.add((x, b))
        for (x, z) in to_add_R:
            rts.add_R(R, x, z)
        changed |= bool(to_add_R)

        if not changed:
            break
    return Y, R


def sat_rc_rt(Y0, R0):
    """
    Saturate using the simulator's primitives only (no C, no δ):
    repeatedly imprint_from_R_row and propagate_R_over_edge until stable.
    """
    Y = copy.deepcopy(Y0)
    R = {k: set(v) for k, v in copy.deepcopy(R0).items()}

    # Ensure symmetry in R
    for a in list(R):
        for b in list(R[a]):
            rts.add_R(R, a, b)

    while True:
        changed = False

        # RT: keep imprinting clique edges from each row
        while True:
            added = False
            for row in list(R.values()):
                e = rts.imprint_from_R_row(Y, row)
                if e:
                    rts.add_Y(Y, *e)
                    added = True
            if not added:
                break
            changed = True

        # RC: try propagation over all current Y edges (snapshot)
        snapshot_Y = list(edgeset(Y))
        new_R_any = False
        for e in snapshot_Y:
            prop = rts.propagate_R_over_edge(R, e)
            if prop:
                rts.add_R(R, *prop)
                new_R_any = True
        changed |= new_R_any

        if not changed:
            break
    return Y, R


# ---------------------------
# Exhaustive graph generator (n<=3)
# ---------------------------

def small_graphs(n=3):
    nodes = [(i, 0) for i in range(n)]
    all_pairs = [(i, j) for i in nodes for j in nodes]
    for mask in range(1 << len(all_pairs)):
        E = set()
        for k, p in enumerate(all_pairs):
            if (mask >> k) & 1:
                E.add(p)
        yield mkY(E)


# ---------------------------
# TESTS: equivalence & laws
# ---------------------------

def test_box_equivalence_small_graphs():
    for Y0 in small_graphs(3):
        Y_ref = ref_box(Y0)
        Y_sat = sat_box(Y0)
        assert edgeset(Y_ref) == edgeset(Y_sat)

def test_diamond_equivalence_small_graphs():
    for Y0 in small_graphs(3):
        Y_ref = ref_diamond(Y0)
        Y_sat = sat_diamond(Y0)
        assert edgeset(Y_ref) == edgeset(Y_sat)

def test_C_equivalence_small_graphs():
    for Y0 in small_graphs(3):
        Y_ref = ref_C(Y0)
        Y_sat = sat_C(Y0)
        assert edgeset(Y_ref) == edgeset(Y_sat)

def test_commutation_box_diamond_small_graphs():
    for Y0 in small_graphs(3):
        left  = ref_box(ref_diamond(Y0))
        right = ref_diamond(ref_box(Y0))
        assert edgeset(left) == edgeset(right)

def test_diamond_is_mirror_box_transpose_small_graphs():
    for Y0 in small_graphs(3):
        # ◇(Y) == mirror(□(transpose(Y))) ∪ Y
        T = rts.transpose_Y(Y0)
        T_cl = ref_box(T)
        mirror = {(i, j) for j, js in T_cl.items() for i in js}
        expected = edgeset(Y0) | mirror
        got = edgeset(ref_diamond(Y0))
        assert got == expected

def test_monotonicity_box_and_diamond():
    # Y ⊆ Y' ⇒ □Y ⊆ □Y' and ◇Y ⊆ ◇Y'
    Ys = list(small_graphs(3))
    for Y0 in Ys:
        for Y1 in Ys:
            if edgeset(Y0).issubset(edgeset(Y1)):
                assert edgeset(ref_box(Y0)).issubset(edgeset(ref_box(Y1)))
                assert edgeset(ref_diamond(Y0)).issubset(edgeset(ref_diamond(Y1)))

def test_idempotence_box_and_diamond():
    for Y0 in small_graphs(3):
        box_once  = ref_box(Y0)
        box_twice = ref_box(box_once)
        assert edgeset(box_once) == edgeset(box_twice)

        dia_once  = ref_diamond(Y0)
        dia_twice = ref_diamond(dia_once)
        assert edgeset(dia_once) == edgeset(dia_twice)

def test_rc_rt_reference_vs_simulator_on_seeds():
    # Compare RC/RT fixpoint for many Y with the same seed R (0~1)
    base_nodes = [(i,0) for i in range(3)]
    R0 = {(0,0): {(1,0)}, (1,0): {(0,0)}}

    for Y0 in small_graphs(3):
        Y_ref, R_ref = ref_rc_rt_closure(Y0, R0)
        Y_sat, R_sat = sat_rc_rt(Y0, R0)
        assert edgeset(Y_ref) == edgeset(Y_sat)
        # Compare symmetric R as undirected edges
        def R_edges(R):
            s = set()
            for a, bs in R.items():
                for b in bs:
                    s.add(tuple(sorted((a,b))))
            return s
        assert R_edges(R_ref) == R_edges(R_sat)

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
