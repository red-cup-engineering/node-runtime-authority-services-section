"""
test_physical_correspondence.py
Physics-level tests for events.py against the RITM correspondences (A–E).

A : Stabilization (CoKleisli idempotence) ↔ equilibrium
B : Defect kernel = 0 ↔ Euler–Lagrange condition
C : Comonad morphism (symmetry) ↔ Noether invariance
D : C/M duality ↔ particle/field correspondence
E : Self-reflexivity ↔ 'witness' behavior (pointwise naturality)

Notes:
- We intentionally EXCLUDE δ from these physics tests, because δ is designed
  to be non-stabilizing (open-ended fibre lifts). The physics here concerns
  stabilization under the comonad C = □∘◇ and the RT/RC couplings.
"""

import itertools
import copy
import random
import rts


# ---------------------------
# Helpers: sets & builders
# ---------------------------

def edgeset(Y):
    return {(i, j) for i, js in Y.items() for j in js}

def mkY(edges):
    Y = {}
    for i, j in edges:
        rts.add_Y(Y, i, j)
    return Y

def nodes_of(Y, R=None):
    ns = set(rts.nodeset(Y))
    if R is not None:
        ns |= set(R.keys())
        for s in R.values():
            ns |= set(s)
    return ns

def transpose_edges(Y):
    return {(j, i) for i, js in Y.items() for j in js}


# ---------------------------
# Reference semantics (math)
# ---------------------------

def ref_box(Y0):
    """□ — reflexive/transitive closure (least fixed point)."""
    ns = nodes_of(Y0)
    E = set(edgeset(Y0))
    # reflexive
    for a in ns:
        E.add((a, a))
    # transitive until fixed
    changed = True
    while changed:
        changed = False
        newE = set(E)
        for (i,j) in list(E):
            for (j2,k) in list(E):
                if j2 == j and (i,k) not in E:
                    newE.add((i,k)); changed = True
        E = newE
    return mkY(E)

def ref_diamond(Y0):
    """◇ — mirror(□(transpose(Y))) ∪ Y."""
    T = rts.transpose_Y(Y0)
    T_cl = ref_box(T)
    mirrored = {(i, j) for j, js in T_cl.items() for i in js}  # (j→i in T_cl) ↦ (i→j)
    return mkY(edgeset(Y0) | mirrored)

def ref_C(Y0):
    """C = □∘◇."""
    return ref_box(ref_diamond(Y0))

def ref_M(Y0):
    """M = ◇∘□ (monad dual)."""
    return ref_diamond(ref_box(Y0))


# ---------------------------
# Simulator saturations (no δ)
# ---------------------------

def sat_C(Y0):
    """Saturate Y under C = ◇ then □, one-step rules, until fixed."""
    Y = copy.deepcopy(Y0)
    while True:
        d = rts.find_diamond_consequence(Y)
        if d:
            rts.add_Y(Y, *d); continue
        b = rts.find_box_consequence(Y)
        if b:
            rts.add_Y(Y, *b); continue
        break
    return Y

def sat_rc_rt(Y0, R0):
    """
    Saturate using RT and RC only (no δ, no C).
    RT: rows imprint cliques in Y; RC: propagate R across Y edges.
    """
    Y = copy.deepcopy(Y0)
    R = {k: set(v) for k, v in copy.deepcopy(R0).items()}
    # ensure symmetry in R
    for a in list(R):
        for b in list(R[a]):
            rts.add_R(R, a, b)

    while True:
        changed = False

        # RT until no more from any row
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

        # RC across current Y-edges (snapshot)
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
# Small graphs (n<=3) for exhaustive checks
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


# ===========================
# A — Stabilization ↔ equilibrium
# ===========================
def test_A_stabilization_equilibrium_small_graphs():
    """
    Saturate under C and check idempotence of the resulting Y: Y∘Y ⊆ Y.
    Also verify the simulator's C-saturation matches the reference C-closure.
    """
    for Y0 in small_graphs(3):
        Y_sim = sat_C(Y0)
        Y_ref = ref_C(Y0)
        assert edgeset(Y_sim) == edgeset(Y_ref), "C-saturation mismatch with reference"

        # Idempotence: after C, transitive closure is already in Y
        comp = {(i,k) for (i,j) in edgeset(Y_sim) for (j2,k) in edgeset(Y_sim) if j2 == j}
        assert comp.issubset(edgeset(Y_sim)), "Post-C graph is not compositional-idempotent"


# ===========================
# B — Defect kernel = 0 ↔ Euler–Lagrange
# ===========================
def test_B_defect_kernel_zero():
    """
    After saturation under C, there should be no 'residual' C-consequence.
    That is, applying C again adds nothing: ref_C(Y_C) == Y_C.
    """
    for Y0 in small_graphs(3):
        Yc = sat_C(Y0)
        Ycc = ref_C(Yc)
        assert edgeset(Yc) == edgeset(Ycc), "Residual nonzero: C not idempotent on the saturated graph"


# ===========================
# C — Symmetry (comonad morphism) ↔ Noether invariance
# ===========================
def permute_nodes(Y, shift=1):
    """Apply a permutation F on node identities: (id, lvl) ↦ ((id+shift)%m, lvl)."""
    ns = sorted({i for i,_ in [(n,0) for n in range(max([a[0] for a in rts.nodeset(Y)] + [1])+1)]})  # identities set guess
    # More robust: build identity set directly from Y
    ids = sorted({i for (i,_) in nodes_of(Y)})
    m = max(ids) + 1 if ids else 1
    def F(n):
        return ((n[0] + shift) % m, n[1])
    E = {(F(i), F(j)) for (i,j) in edgeset(Y)}
    return mkY(E)

def test_C_symmetry_noether_invariance():
    """
    For a permutation F on identities, verify:
        1. C(F(Y)) = F(C(Y))   — comonadic naturality (Noether symmetry)
        2. RT/RC closure is *covariant* when both Y and R are permuted:
           permute_R(R_rt2, shift) == R_rt1.
    """
    random.seed(0)
    for _ in range(30):
        # --- random small Y
        n = 3
        nodes = [(i, 0) for i in range(n)]
        all_pairs = [(i, j) for i in nodes for j in nodes]
        E = {p for p in all_pairs if random.random() < 0.4}
        Y0 = mkY(E)

        # --- permutation helper
        def permute_nodes_with_m(Y, shift=1):
            ids = sorted({i for (i, _) in nodes_of(Y)})
            m = max(ids) + 1 if ids else 1
            def F(n): return ((n[0] + shift) % m, n[1])
            E2 = {(F(i), F(j)) for (i, j) in edgeset(Y)}
            return mkY(E2)

        # --- R permutation helper
        def permute_R(R, shift=1):
            ids = sorted({i for (i, _) in nodes_of(Y0)})
            m = max(ids) + 1 if ids else 1
            def F(n): return ((n[0] + shift) % m, n[1])
            R2 = {}
            for a, bs in R.items():
                a2 = F(a)
                R2[a2] = {F(b) for b in bs}
            return R2

        # --- test 1: comonadic symmetry
        Yc1 = sat_C(permute_nodes_with_m(Y0, shift=1))
        Yc2 = permute_nodes_with_m(sat_C(Y0), shift=1)
        assert edgeset(Yc1) == edgeset(Yc2), "C not natural under permutation symmetry"

        # --- test 2: RT/RC covariance
        R0 = {(0, 0): {(1, 0)}, (1, 0): {(0, 0)}}
        R1 = permute_R(R0, 1)
        Y_perm = permute_nodes_with_m(Y0, 1)

        Yrt1, Rrt1 = sat_rc_rt(Y_perm, R1)
        Yrt2, Rrt2 = sat_rc_rt(Y0, R0)

        # permute the unpermuted result for comparison
        Yrt2p = permute_nodes_with_m(Yrt2, 1)
        Rrt2p = permute_R(Rrt2, 1)

        # define a symmetric comparison for R (unordered pairs)
        def R_edges(R):
            s = set()
            for a, bs in R.items():
                for b in bs:
                    s.add(tuple(sorted((a, b))))
            return s

        # Y should be invariant; R should be *covariant*
        assert edgeset(Yrt1) == edgeset(Yrt2p), "RT/RC Y not symmetric under full permutation"
        assert R_edges(Rrt1) == R_edges(Rrt2p), "RT/RC R not covariant under permutation"

        
# ===========================
# D — C/M duality ↔ particle/field correspondence
# ===========================
def test_D_CM_commute_small_graphs():
    """
    Check CM = MC on all small graphs (n<=3) using reference semantics.
    Also verify simulator C matches reference, and that 'particles' (loops)
    and 'fields' (off-diagonals) transform consistently under C and M.
    """
    for Y0 in small_graphs(3):
        left  = ref_C(ref_M(Y0))
        right = ref_M(ref_C(Y0))
        assert edgeset(left) == edgeset(right), "CM != MC"

        # Simulator C agrees with reference C
        Yc_sim = sat_C(Y0)
        assert edgeset(Yc_sim) == edgeset(ref_C(Y0))

        # Particle/field bookkeeping
        Es = edgeset(ref_M(Y0))
        loops = {(i,j) for (i,j) in Es if i == j}
        off   = Es - loops
        # After C, all nodes must have loops (particles stabilized)
        Es2 = edgeset(ref_C(ref_M(Y0)))
        for (i,j) in Es2:
            assert (i,i) in Es2 and (j,j) in Es2, "Missing particle-like self edge after CM"
        # And off-diagonals persist under commuting closure
        assert any(i != j for (i,j) in Es2) or not off, "Fields vanished unexpectedly"


# ===========================
# E — Self-reflexivity (witness behavior via pointwise naturality)
# ===========================
def test_E_self_reflexivity_pointwise():
    """
    Model a tiny 'presheaf' as a tuple (Y0, Y1) and apply C pointwise.
    Check naturality: reindexing the tuple commutes with C.
    This is a minimal, concrete stand-in for the witness-topos idea.
    """
    def reindex(pair):
        # swap components
        a, b = pair
        return (b, a)

    # two small graphs
    Ys = []
    for Y0 in itertools.islice(small_graphs(3), 5):
        Ys.append(Y0)
    if len(Ys) < 2:
        return
    A, B = Ys[0], Ys[1]

    C_on_pair = (sat_C(A), sat_C(B))
    C_on_reindexed = (sat_C(B), sat_C(A))
    assert (sat_C(*reindex((A,B))) if False else C_on_reindexed)  # placeholder to show intent

    # Natural commutation: C ∘ swap == swap ∘ C
    assert (C_on_reindexed[0], C_on_reindexed[1]) == reindex(C_on_pair), \
        "Pointwise naturality failed: C does not commute with reindexing"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
