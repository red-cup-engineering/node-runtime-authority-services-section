# ritm_physics.py — Physics over RITM (local-fibre aware)
# Snapshot-based: builds C(Y) = □∘◇ once, then computes ρ = R·C(Y) - R.
# Outputs action S and coherence σ. Pure functions; no classes.

from typing import Dict, Set, Tuple, List, Optional

Node = Tuple[int, int]   # (identity, level)
RRel = Dict[Node, Set[Node]]
YAdj = Dict[Node, Set[Node]]

# ----------------------------- utilities -------------------------------------

def nodes_union(R: RRel, Y: YAdj) -> List[Node]:
    ns: Set[Node] = set(Y.keys()) | set().union(*Y.values() or [set()])
    ns |= set(R.keys())
    for zs in R.values():
        ns |= zs
    return sorted(ns)

def indexer(nodes: List[Node]) -> Dict[Node, int]:
    return {n: i for i, n in enumerate(nodes)}

def dense_from_Y(nodes: List[Node], Y: YAdj) -> List[List[float]]:
    idx = indexer(nodes)
    n = len(nodes)
    M = [[0.0]*n for _ in range(n)]
    for i, js in Y.items():
        if i not in idx:  # ignore nodes outside this snapshot
            continue
        ii = idx[i]
        for j in js:
            jj = idx.get(j)
            if jj is not None:
                M[ii][jj] = 1.0
    return M

def dense_from_R(dom_nodes: List[Node], cod_nodes: List[Node], R: RRel) -> List[List[float]]:
    id_dom = indexer(dom_nodes)
    id_cod = indexer(cod_nodes)
    M = [[0.0]*len(cod_nodes) for _ in range(len(dom_nodes))]
    for x, zs in R.items():
        i = id_dom.get(x)
        if i is None:
            continue
        for z in zs:
            j = id_cod.get(z)
            if j is not None:
                M[i][j] = 1.0
    return M

def matmul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    n = len(A)
    k = len(A[0]) if A else 0
    m = len(B[0]) if B else 0
    C = [[0.0]*m for _ in range(n)]
    for i in range(n):
        Ai = A[i]
        for t in range(k):
            at = Ai[t]
            if at == 0.0:
                continue
            Bt = B[t]
            for j in range(m):
                bj = Bt[j]
                if bj != 0.0:
                    C[i][j] += at * bj
    return C

def matsub(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    n = len(A)
    m = len(A[0]) if A else 0
    return [[A[i][j] - B[i][j] for j in range(m)] for i in range(n)]

def l1_norm(A: List[List[float]]) -> float:
    return sum(abs(x) for row in A for x in row)

def count_nonzero(A: List[List[float]]) -> int:
    return sum(1 for row in A for x in row if x != 0.0)

# ------------------------- snapshot closure C = □∘◇ --------------------------

def transpose_Y(Y: YAdj) -> YAdj:
    T: YAdj = {}
    for i, js in Y.items():
        for j in js:
            T.setdefault(j, set()).add(i)
    for k in list(T):
        T.setdefault(k, set())
    return T

def ensure_reflexive(Y: YAdj) -> None:
    ns = set(Y.keys()) | set().union(*Y.values() or [set()])
    for i in ns:
        Y.setdefault(i, set())
        Y[i].add(i)

def rtc_closure(Y: YAdj) -> YAdj:
    """Reflexive–transitive closure (finite fixed point). Snapshot only."""
    C: YAdj = {i: set(js) for i, js in Y.items()}
    ensure_reflexive(C)
    changed = True
    while changed:
        changed = False
        for i in list(C.keys()):
            for k in list(C[i]):
                for j in C.get(k, ()):
                    if j not in C[i]:
                        C[i].add(j)
                        changed = True
    return C

def box_closure(Y: YAdj) -> YAdj:
    return rtc_closure(Y)

def diamond_closure(Y: YAdj) -> YAdj:
    T = rtc_closure(transpose_Y(Y))
    return transpose_Y(T)

def C_closure(Y: YAdj) -> YAdj:
    """C = □∘◇ (computed once for the snapshot)."""
    return box_closure(diamond_closure(Y))

# ------------------- linear reflection: ρ, S, σ on a snapshot ----------------

def linear_reflection_rho(
    R: RRel,
    Y: YAdj,
    *,
    use_C_closure: bool = True
) -> Tuple[List[List[float]], List[Node], List[Node]]:
    """
    Build dense matrices and compute ρ := R · C(Y) - R.
    Returns (rho, dom_nodes, cod_nodes) for downstream metrics.
    """
    CY = C_closure(Y) if use_C_closure else Y
    cod_nodes = nodes_union(R, CY)      # codomain index for both CY and R
    dom_nodes = sorted(R.keys())        # rows present in R
    R_dense  = dense_from_R(dom_nodes, cod_nodes, R)
    CY_dense = dense_from_Y(cod_nodes, CY)  # cod×cod
    RCY = matmul(R_dense, CY_dense)          # dom×cod
    rho = matsub(RCY, R_dense)
    return rho, dom_nodes, cod_nodes

def action_S_linear(rho: List[List[float]]) -> float:
    # L1-based action (paper’s linear residual energy, simplified)
    return 0.5 * l1_norm(rho)

def sigma_coherence_linear(rho: List[List[float]], R_dense: List[List[float]]) -> float:
    tot = max(1, count_nonzero(R_dense))
    bad = count_nonzero(rho)
    return 1.0 - bad / float(tot)

def measures_linear(
    R: RRel, Y: YAdj, *, use_C_closure: bool = True
) -> Tuple[float, float]:
    rho, dom_nodes, cod_nodes = linear_reflection_rho(R, Y, use_C_closure=use_C_closure)
    R_dense = dense_from_R(dom_nodes, cod_nodes, R)  # for σ denominator
    S = action_S_linear(rho)
    σ = sigma_coherence_linear(rho, R_dense)
    return S, σ

# -------------------------- symmetry / Noether hooks --------------------------

def shift_levels(n: Node, k: int = 1) -> Node:
    """Uniform δ-shift on levels (acts fibre-wise)."""
    i, ℓ = n
    return (i, ℓ + k)

def apply_symmetry_to_Y(Y: YAdj, f) -> YAdj:
    Z: YAdj = {}
    for i, js in Y.items():
        fi = f(i)
        for j in js:
            fj = f(j)
            Z.setdefault(fi, set()).add(fj)
    return Z

def apply_symmetry_to_R(R: RRel, f) -> RRel:
    S: RRel = {}
    for x, zs in R.items():
        fx = f(x)
        for z in zs:
            fz = f(z)
            S.setdefault(fx, set()).add(fz)
    return S

def noether_invariant_check(
    R: RRel, Y: YAdj, symmap, *, use_C_closure: bool = True, tol: float = 1e-9
) -> Tuple[bool, float, float]:
    S0, σ0 = measures_linear(R, Y, use_C_closure=use_C_closure)
    R2 = apply_symmetry_to_R(R, symmap)
    Y2 = apply_symmetry_to_Y(Y, symmap)
    S1, σ1 = measures_linear(R2, Y2, use_C_closure=use_C_closure)
    return (abs(S1 - S0) <= tol and abs(σ1 - σ0) <= tol, S1 - S0, σ1 - σ0)

# --------------------------------- demo --------------------------------------

if __name__ == "__main__":
    # A small mixed snapshot (3 identities × 2 levels) to produce nontrivial ρ.
    Y: YAdj = {
        # base layer: a 3-cycle with reflexives
        (0,0): {(0,0), (1,0)},
        (1,0): {(1,0), (2,0)},
        (2,0): {(2,0), (0,0)},
        # first lifts: each sees itself and the successor’s *base*
        (0,1): {(0,1), (1,0)},
        (1,1): {(1,1), (2,0)},
        (2,1): {(2,1), (0,0)},
    }

    R: RRel = {
        # base field circulation
        (0,0): {(1,0)},
        (1,0): {(2,0)},
        (2,0): {(0,0)},
        # lifted field: lift the circulation
        (0,1): {(1,1)},
        (1,1): {(2,1)},
        (2,1): {(0,1)},
    }

    S, σ = measures_linear(R, Y, use_C_closure=True)
    print(f"S={S:.6f}  σ={σ:.6f}")

    ok, dS, dσ = noether_invariant_check(R, Y, lambda n: shift_levels(n, +1))
    print(f"Noether (level shift) invariant? {ok}  ΔS={dS:.3g}  Δσ={dσ:.3g}")
