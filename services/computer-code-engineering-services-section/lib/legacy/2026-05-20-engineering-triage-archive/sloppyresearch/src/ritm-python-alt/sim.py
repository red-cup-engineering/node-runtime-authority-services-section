# sim.py — RITM simulator (atomic tick = C = □⟐◇, single-hop)
# ------------------------------------------------------------
# Granular, pure-functional implementation.
# Each tick applies exactly: C_graph(Y) = box_step(diamond_step(Y))
# No alternation, no tunables, no noise in the evolver.

from typing import List, Tuple

# ------------------------------
# Boolean matrix algebra (pure)
# ------------------------------

def zeros(n:int,m:int)->List[List[int]]:
    return [[0]*m for _ in range(n)]

def transpose(A:List[List[int]])->List[List[int]]:
    return [list(row) for row in zip(*A)]

def mat_bool_or(A:List[List[int]],B:List[List[int]])->List[List[int]]:
    n,m=len(A),len(A[0])
    return [[1 if (A[i][j] or B[i][j]) else 0 for j in range(m)] for i in range(n)]

def mat_bool_mul(A:List[List[int]],B:List[List[int]])->List[List[int]]:
    n,k=len(A),len(A[0]); m=len(B[0])
    C=zeros(n,m)
    for i in range(n):
        for j in range(m):
            for t in range(k):
                if A[i][t] and B[t][j]:
                    C[i][j]=1; break
    return C

def mat_xor(A:List[List[int]],B:List[List[int]])->List[List[int]]:
    n,m=len(A),len(A[0])
    return [[A[i][j]^B[i][j] for j in range(m)] for i in range(n)]

def count_ones(A:List[List[int]])->int:
    return sum(sum(r) for r in A)

def show_matrix(M:List[List[int]])->str:
    return "\n".join(" ".join(str(x) for x in row) for row in M)

# -----------------------------------
# Single-hop modal nuclei and comonad
# -----------------------------------

def add_reflexive(A:List[List[int]])->List[List[int]]:
    n=len(A); C=[row[:] for row in A]
    for i in range(n): C[i][i]=1
    return C

def box_step(A:List[List[int]])->List[List[int]]:
    """□: one-hop forward closure + reflexivity."""
    return add_reflexive(mat_bool_or(A, mat_bool_mul(A, A)))

def diamond_step(A:List[List[int]])->List[List[int]]:
    """◇: one-hop backward closure + reflexivity (via transpose)."""
    return transpose(box_step(transpose(A)))

def C_graph(Y:List[List[int]])->List[List[int]]:
    """Atomic comonadic tick: C = □∘◇ with each nucleus single-hop."""
    return box_step(diamond_step(Y))

# ----------------
# RITM measures
# ----------------

def apply_C_on_codomain(R:List[List[int]], Y:List[List[int]])->List[List[int]]:
    CY = C_graph(Y)
    return mat_bool_mul(R, CY)

def residual_rho(R:List[List[int]], Y:List[List[int]])->List[List[int]]:
    # ρ = (R ∘ C(Y)) ⊕ R
    return mat_xor(apply_C_on_codomain(R, Y), R)

def action_S(R:List[List[int]], Y:List[List[int]])->float:
    return 0.5 * float(count_ones(residual_rho(R, Y)))

def sigma_score(R:List[List[int]], Y:List[List[int]])->float:
    rho = residual_rho(R, Y)
    n=len(rho); m=len(rho[0]) if n>0 else 0
    tot = n*m
    return 1.0 if tot==0 else 1.0 - count_ones(rho)/float(tot)

# -------------------------
# Evolution (pure, minimal)
# -------------------------

def evolve_step(R:List[List[int]], Y:List[List[int]])->Tuple[List[List[int]],List[List[int]],float,float]:
    """
    One internal application of C (no externalities).
    Update R on codomain; update Y by its comonadic closure plus RᵀR imprint.
    """
    CY = C_graph(Y)
    Rn = mat_bool_mul(R, CY)
    Yn = mat_bool_or(CY, mat_bool_mul(transpose(R), R))
    S  = action_S(Rn, Yn)
    sig = sigma_score(Rn, Yn)
    return Rn, Yn, S, sig

def evolve(
    R0: List[List[int]],
    Y0: List[List[int]],
    *,
    sigma_target: float = 1.0,
    delta_S_max: float = 0.0,
    step_limit: int = 100
) -> List[Tuple[List[List[int]], List[List[int]], float, float]]:
    R, Y = [row[:] for row in R0], [row[:] for row in Y0]
    hist = []
    prev_S = None

    for step in range(step_limit):
        R, Y, S, sigma = evolve_step(R, Y)
        hist.append((R, Y, S, sigma))

        if prev_S is not None:
            if sigma >= sigma_target and abs(S - prev_S) <= delta_S_max:
                break
        prev_S = S

    return hist


# -------------
# Seed graphs
# -------------
def line_graph(n:int)->List[List[int]]:
    return [[1 if j==i+1 else 0 for j in range(n)] for i in range(n)]

def cycle_graph(n:int)->List[List[int]]:
    return [[1 if j==(i+1)%n else 0 for j in range(n)] for i in range(n)]


# -----
# Demo
# -----
if __name__ == "__main__":
    # Size of the relational domain
    n = 10

    # Seed topology (directed line)
    Y0 = line_graph(n)

    # Seed relation (identity + next-edge)
    R0 = [[1 if (j == i or j == i + 1) else 0 for j in range(n)] for i in range(n)]

    # Display initial condition
    print("Initial topology Y₀:")
    print(show_matrix(Y0))
    print("\n--- Beginning comonadic evolution ---")

    # Run until stabilization or safety limit
    hist = evolve(
        R0,
        Y0,
        sigma_target=1.0,      # stop when coherence σ ≥ 1.0
        delta_S_max=0.0,       # and energy change ΔS ≤ 0.0
        step_limit=50          # fallback hard limit
    )

    # Per-step log
    for t, (_, _, S, sigma) in enumerate(hist):
        print(f"t={t:02d}  S={S:.6f}  σ={sigma:.6f}")

    # Report termination summary
    final_step = len(hist) - 1
    final_S = hist[-1][2]
    final_sigma = hist[-1][3]

    if final_sigma >= 1.0 and final_S == hist[-1][2]:
        reason = "stabilization condition reached"
    elif final_step + 1 >= 50:
        reason = "safety step-limit reached"
    else:
        reason = "custom threshold satisfied"

    print(f"\nEvolution halted after {final_step} steps ({reason}).")
    print(f"  Final S = {final_S:.6f}")
    print(f"  Final σ = {final_sigma:.6f}")

    print(f"\nFinal topology Y_{final_step}:")
    print(show_matrix(hist[-1][1]))
