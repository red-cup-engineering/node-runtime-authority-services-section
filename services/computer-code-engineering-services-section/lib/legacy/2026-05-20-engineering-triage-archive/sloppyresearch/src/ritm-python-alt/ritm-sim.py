from typing import Iterable, List, Tuple, Dict, Set

def zeros(n: int, m: int) -> List[List[int]]:
    return [[0]*m for _ in range(n)]

def identity(n: int) -> List[List[int]]:
    I = zeros(n, n)
    for i in range(n): I[i][i] = 1
    return I

def mat_bool_or(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    n, m = len(A), len(A[0]) if A else 0
    C = zeros(n, m)
    for i in range(n):
        for j in range(m):
            C[i][j] = 1 if (A[i][j] or B[i][j]) else 0
    return C

def transpose(A: List[List[int]]) -> List[List[int]]:
    if not A: return []
    n, m = len(A), len(A[0])
    T = zeros(m, n)
    for i in range(n):
        for j in range(m):
            T[j][i] = A[i][j]
    return T

def mat_bool_mul(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    n, k = len(A), len(A[0]) if A else 0
    k2, m = (len(B), len(B[0]) if B else 0) if B else (0,0)
    assert k == k2, f"shape mismatch: {n}x{k} * {k2}x{m}"
    C = zeros(n, m)
    for i in range(n):
        for j in range(m):
            val = 0
            for t in range(k):
                if A[i][t] and B[t][j]:
                    val = 1
                    break
            C[i][j] = val
    return C

def mat_xor(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    n, m = len(A), len(A[0]) if A else 0
    X = zeros(n, m)
    for i in range(n):
        for j in range(m):
            X[i][j] = 1 if (A[i][j] ^ B[i][j]) else 0
    return X

def count_ones(A: List[List[int]]) -> int:
    return sum(sum(row) for row in A)

def show_matrix(M: List[List[int]]) -> str:
    return "\n".join(" ".join(str(x) for x in row) for row in M)

def graph_from_edges(n:int, edges:Iterable[Tuple[int,int]], reflexive:bool=False) -> List[List[int]]:
    A = zeros(n, n)
    if reflexive:
        for i in range(n): A[i][i] = 1
    for i, j in edges: A[i][j] = 1
    return A

def line_graph(n:int) -> List[List[int]]:
    return graph_from_edges(n, ((i, i+1) for i in range(n-1)))

def cycle_graph(n:int) -> List[List[int]]:
    return graph_from_edges(n, ((i, (i+1) % n) for i in range(n)))

def star_graph(n:int, center:int=0) -> List[List[int]]:
    return graph_from_edges(n, ((center, i) for i in range(n) if i != center))

def rtc(A: List[List[int]]) -> List[List[int]]:
    n = len(A)
    C = [row[:] for row in A]
    # reflexivity
    for i in range(n): C[i][i] = 1
    # transitivity
    for k in range(n):
        for i in range(n):
            if C[i][k]:
                row_k = C[k]
                Ci = C[i]
                for j in range(n):
                    if row_k[j]:
                        Ci[j] = 1
    return C

def box(A: List[List[int]]) -> List[List[int]]:
    return rtc(A)

def diamond(A: List[List[int]]) -> List[List[int]]:
    return transpose(rtc(transpose(A)))

def C_graph(A: List[List[int]]) -> List[List[int]]:
    return box(diamond(A))

def relation_from_pairs(nx:int, ny:int, pairs:Iterable[Tuple[int,int]]) -> List[List[int]]:
    R = zeros(nx, ny)
    for i, j in pairs: R[i][j] = 1
    return R

def apply_C_on_codomain(R: List[List[int]], Y: List[List[int]]) -> List[List[int]]:
    CY = C_graph(Y)
    return mat_bool_mul(R, CY)

def residual_rho(R: List[List[int]], Y: List[List[int]]) -> List[List[int]]:
    return mat_xor(apply_C_on_codomain(R, Y), R)

def action_S(R: List[List[int]], Y: List[List[int]]) -> float:
    return 0.5 * float(count_ones(residual_rho(R, Y)))

def sigma_score(R: List[List[int]], Y: List[List[int]]) -> float:
    rho = residual_rho(R, Y)
    n = len(rho); m = len(rho[0]) if n>0 else 0
    total = n*m
    return 1.0 if total == 0 else 1.0 - count_ones(rho)/float(total)

def defect_rows(R: List[List[int]], Y: List[List[int]]) -> List[int]:
    rho = residual_rho(R, Y)
    return [i for i, row in enumerate(rho) if all(v == 0 for v in row)]

def compose_rel(R: List[List[int]], S: List[List[int]]) -> List[List[int]]:
    return mat_bool_mul(R, S)

def box_rel(R: List[List[int]], Y: List[List[int]]) -> List[List[int]]:
    return mat_bool_mul(R, box(Y))

def diamond_rel(R: List[List[int]], Y: List[List[int]]) -> List[List[int]]:
    return mat_bool_mul(R, diamond(Y))

def iterate_modal(R: List[List[int]], k:int, Y: List[List[int]]) -> List[List[int]]:
    assert k >= 1
    base = R
    r = R
    for _ in range(1, k):
        r_box = box_rel(r, Y)
        r_dia = diamond_rel(base, Y)
        r = compose_rel(r_box, r_dia)
    return r

def jacobian_S(R: List[List[int]], Y: List[List[int]]) -> List[List[int]]:
    base_S = action_S(R, Y)
    n = len(R); m = len(R[0]) if n>0 else 0
    J = zeros(n, m)
    for i in range(n):
        for j in range(m):
            R_flip = [row[:] for row in R]
            R_flip[i][j] = 1 - R_flip[i][j]
            J[i][j] = int(round(action_S(R_flip, Y) - base_S))
    return J

def horn_rules_from_Y(Y: List[List[int]]) -> Set[Tuple[int, int]]:
    CY = C_graph(Y)
    n = len(CY)
    rules = set()
    for j in range(n):
        for k in range(n):
            if CY[j][k] and not (j == k):
                rules.add((j, k))
    return rules

def horn_closure_of_R(R: List[List[int]], Y: List[List[int]]) -> List[Set[int]]:
    rules = horn_rules_from_Y(Y)
    n = len(R); m = len(R[0]) if n>0 else 0
    entailments: List[Set[int]] = []
    succ: Dict[int, Set[int]] = {a:set() for a in range(m)}
    for a,b in rules: succ[a].add(b)

    for i in range(n):
        active = {j for j in range(m) if R[i][j] == 1}
        changed = True
        closure = set(active)
        while changed:
            changed = False
            for a in list(closure):
                for b in succ[a]:
                    if b not in closure:
                        closure.add(b)
                        changed = True
        entailments.append(closure)
    return entailments

def indeg_outdeg(Y):
    n = len(Y)
    outd = [sum(Y[i][j] for j in range(n)) for i in range(n)]
    indeg = [sum(Y[i][j] for i in range(n)) for j in range(n)]
    edges = sum(outd)  # total directed edges
    return indeg, outd, edges

def realize_digraph_with_preferences(target_indeg, target_outdeg, P):
    n = len(target_indeg)
    assert n == len(target_outdeg)
    # remaining "stubs"
    rem_in  = target_indeg[:]
    rem_out = target_outdeg[:]
    Y = [[0]*n for _ in range(n)]
    # Build a preference list for each i: j sorted by P[i][j] then tie-break by remaining in-degree
    pref_lists = [sorted(range(n), key=lambda j: (-P[i][j], -rem_in[j], j)) for i in range(n)]
    # For fast available targets per j
    avail_in = {j for j in range(n) if rem_in[j] > 0}

    # Greedy pass honoring preferences
    changed = True
    while changed:
        changed = False
        for i in range(n):
            while rem_out[i] > 0:
                # try preferred j first
                chosen = None
                for j in pref_lists[i]:
                    if i != j and rem_in[j] > 0 and Y[i][j] == 0:
                        chosen = j
                        break
                # fallback to any available j
                if chosen is None:
                    for j in range(n):
                        if i != j and rem_in[j] > 0 and Y[i][j] == 0:
                            chosen = j
                            break
                if chosen is None:
                    # no placement possible; break this i (will be handled by cleanup)
                    break
                Y[i][chosen] = 1
                rem_out[i]  -= 1
                rem_in[chosen] -= 1
                if rem_in[chosen] == 0 and chosen in avail_in:
                    avail_in.remove(chosen)
                changed = True
    # If leftover stubs remain (rare on feasible sequences), attempt simple 2-switch repairs
    # Find edges (i->a)=1, (k->b)=1 where swapping to (i->b),(k->a) frees capacity while moving toward P
    # Iterate a few rounds to improve Hamming proximity without changing degrees.
    def score_delta(i,a,k,b):
        before = P[i][a] + P[k][b]
        after  = P[i][b] + P[k][a]
        return after - before
    for _ in range(4):
        improved = False
        ones = [(i,j) for i in range(n) for j in range(n) if Y[i][j]==1]
        zeros = [(i,j) for i in range(n) for j in range(n) if i!=j and Y[i][j]==0]
        # try swaps
        for (i,a) in ones:
            for (k,b) in ones:
                if i==k or a==b: continue
                if Y[i][b]==0 and Y[k][a]==0 and i!=b and k!=a:
                    d = score_delta(i,a,k,b)
                    if d>0:
                        Y[i][a]=0; Y[k][b]=0; Y[i][b]=1; Y[k][a]=1
                        improved = True
                        break
            if improved: break
        if not improved: break
    return Y

def apply_permutation_to_matrix(Y, perm):
    # perm is a list p with Y'[i][j] = Y[p[i]][p[j]]
    n = len(Y)
    return [[Y[perm[i]][perm[j]] for j in range(n)] for i in range(n)]

def group_orbit_boolean_average(Y, group_perms):
    # average over orbit (majority vote), tie→keep original bit
    n = len(Y); m = len(Y[0])
    acc = [[0]*m for _ in range(n)]
    for p in group_perms:
        Yp = apply_permutation_to_matrix(Y, p)
        for i in range(n):
            for j in range(m):
                acc[i][j] += Yp[i][j]
    T = len(group_perms)
    Y_avg = [[1 if acc[i][j] > T/2 else (Y[i][j] if acc[i][j]==T/2 else 0) for j in range(m)] for i in range(n)]
    return Y_avg

def make_rotation_group(n):
    # cyclic rotations on n points: (i -> (i+k) mod n)
    group = []
    for k in range(n):
        group.append([(i+k)%n for i in range(n)])
    return group

def evolve_RY_noether(R, Y, steps=12, conserve_degrees=True, verbose=True):
    n = len(Y)
    indeg0, outdeg0, edges0 = indeg_outdeg(Y)
    group_perms = make_rotation_group(n)    # always enforce full rotational symmetry
    hist = []

    for t in range(steps):
        CY = C_graph(Y)                     # comonadic closure □∘◇
        Rn = mat_bool_mul(R, CY)            # dynamic update
        Yprop = mat_bool_or(CY, mat_bool_mul(transpose(R), R))  # proposed topology

        # Enforce rotation symmetry first (locked)
        Yprop = group_orbit_boolean_average(Yprop, group_perms)

        # Degree conservation projection
        if conserve_degrees:
            Yn = realize_digraph_with_preferences(indeg0, outdeg0, Yprop)
        else:
            Yn = Yprop

        # Re-apply symmetry after degree realization
        Yn = group_orbit_boolean_average(Yn, group_perms)
        if conserve_degrees:
            Yn = realize_digraph_with_preferences(indeg0, outdeg0, Yn)

        # Measure action and coherence
        S = action_S(Rn, Yn)
        sig = sigma_score(Rn, Yn)
        indeg, outdeg, edges = indeg_outdeg(Yn)
        ok_deg = (sorted(indeg)==sorted(indeg0) and sorted(outdeg)==sorted(outdeg0))
        if verbose:
            print(f"t={t:02d}  S={S:.3f}  σ={sig:.3f}  edges={edges}  degreesOK={ok_deg}")
        hist.append((Rn, Yn, S, sig))

        # Stop if fully stabilized (no change and no energy difference)
        if t>0:
            sameY = all(Yn[i][j]==hist[-2][1][i][j] for i in range(n) for j in range(n))
            if sameY and abs(S - hist[-2][2]) < 1e-9:
                break

        R, Y = Rn, Yn

    return R, Y, hist

if __name__ == "__main__":
    n = 8
    # Seed space and relation
    Y0 = line_graph(n)   # any sparse seed; degrees are the conserved invariant
    pairs = [(i,i) for i in range(n)] + [(i,(i+1)%n) for i in range(n)]
    R0 = relation_from_pairs(n,n,pairs)

    print("=== Noether evolution ===")
    Rf, Yf, hist = evolve_RY_noether(R0, Y0, steps=20, conserve_degrees=True)
    print("Final Y (degrees conserved):")
    print(show_matrix(Yf))
