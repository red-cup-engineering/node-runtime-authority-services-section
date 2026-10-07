from typing import List

def bool_matmul(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    m, p, n = len(A), len(A[0]), len(B[0])
    C = [[0]*n for _ in range(m)]
    for i in range(m):
        Ai = A[i]
        for k in range(p):
            if Ai[k]:
                Bk = B[k]
                for j in range(n):
                    C[i][j] = 1 if (C[i][j] or Bk[j]) else 0
    return C

def reach(R: List[List[int]]) -> List[List[int]]:
    n = len(R)
    F = [[1 if i==j or R[i][j] else 0 for j in range(n)] for i in range(n)]
    for k in range(n):
        F = [[1 if F[i][j] or (F[i][k] and F[k][j]) else 0 for j in range(n)] for i in range(n)]
    return F

def box(R: List[List[int]]) -> List[List[int]]:
    F = reach(R)
    return bool_matmul(R, F)

def diamond(R: List[List[int]]) -> List[List[int]]:
    F = reach(R)
    Ft = [list(row) for row in zip(*F)]   # transpose (reverse reachability)
    return bool_matmul(R, Ft)

def C_modality(R: List[List[int]]) -> List[List[int]]:
    return bool_matmul(box(R), diamond(R))

def residual_rho(R: List[List[int]]) -> List[List[int]]:
    RC = C_modality(R)
    m, n = len(R), len(R[0])
    return [[1 if (RC[i][j] ^ R[i][j]) else 0 for j in range(n)] for i in range(m)]

def action_S(R: List[List[int]]) -> float:
    rho = residual_rho(R)
    m, n = len(rho), len(rho[0])
    ones = sum(sum(row) for row in rho)
    return ones / (m * n) if m and n else 0.0

def sigma_score(R: List[List[int]]) -> float:
    return 1.0 - action_S(R)

def iterate_modal(R: List[List[int]]) -> List[List[int]]:
    return C_modality(R)

def simulate_reflexive(R0: List[List[int]], steps: int = 20) -> None:
    R = R0
    for t in range(steps):
        E = action_S(R)
        sigma = sigma_score(R)
        print(f"Step {t:03d}: E={E:.4f}, σ={sigma:.3f}")
        R = iterate_modal(R)

def show_matrix(M: List[List[int]]) -> str:
    return "\n".join(" ".join(str(x) for x in row) for row in M)

from typing import List

def compose(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    """Boolean composition of relations A and B."""
    m, p, n = len(A), len(A[0]), len(B[0])
    C = [[0]*n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            C[i][j] = 1 if any(A[i][k] and B[k][j] for k in range(p)) else 0
    return C

import numpy as np
import numpy as np

def compose_with_numpy(A, B):
    """
    Boolean composition (∨/∧) using NumPy bit packing.
    Works for any matrix size by equalizing packed lengths.
    """
    A = np.array(A, dtype=np.uint8)
    B = np.array(B, dtype=np.uint8)

    n = B.shape[1]
    pack_width = 8 * ((n + 7) // 8)         # next multiple of 8 bits
    pad = pack_width - n
    if pad:
        A = np.pad(A, ((0, 0), (0, pad)), constant_values=0)
        B = np.pad(B, ((0, 0), (0, pad)), constant_values=0)

    # pack to bytes
    A_bits = np.packbits(A, axis=1)
    B_bits = np.packbits(B, axis=1)
    B_bits_T = B_bits.T

    m = A_bits.shape[0]
    out = np.zeros((m, n), dtype=np.uint8)
    for i in range(m):
        row = A_bits[i]
        # bitwise AND against every transposed column
        mask = np.bitwise_and(row, B_bits_T)
        # nonzero along packed bytes → relation holds
        out[i] = np.any(mask, axis=0).astype(np.uint8)
    return out[:, :n].tolist()

def transpose(R: List[List[int]]) -> List[List[int]]:
    """Return transpose of relation R."""
    return [list(row) for row in zip(*R)]

def induce_C(R: List[List[int]]) -> List[List[int]]:
    """Compute C = □◇ = (R Rᵀ)(Rᵀ R)."""
    Rt = transpose(R)
    return compose(compose(R, Rt), compose(Rt, R))

def induce_C_from_numpy(R: List[List[int]]) -> List[List[int]]:
    """Compute C = □◇ = (R Rᵀ)(Rᵀ R)."""
    Rt = transpose(R)
    return compose_with_numpy(compose_with_numpy(R, Rt), compose_with_numpy(Rt, R))

def canonical_C(n: int = 3) -> List[List[int]]:
    """Generate canonical modality C from the identity relation."""
    I = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    return C_from_first_principles(I)

def perturb_identity(n: int = 5, flips: int = 1) -> list[list[int]]:
    """Return identity with a few off-diagonal 1s added."""
    import random
    I = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    for _ in range(flips):
        i, j = random.randrange(n), random.randrange(n)
        if i != j:
            I[i][j] = 1
    return I

import matplotlib.pyplot as plt

def cohesion(R):
    total = sum(sum(row) for row in R)
    n = len(R)
    return total / (n * n)

def iterate_and_measure(R0, steps=20):
    """Run C-iteration, record cohesion and action."""
    R = R0
    cohesion_vals, action_vals = [], []
    for _ in range(steps):
        cohesion_vals.append(cohesion(R))
        action_vals.append(action_S(R))
        R = induce_C_from_numpy(R)
    return cohesion_vals, action_vals

def plot_evolution(cohesion_vals, action_vals):
    """Plot cohesion and residual/action through time."""
    plt.figure()
    plt.plot(cohesion_vals, label="cohesion (condensed relation)")
    plt.plot(action_vals, label="action / residual energy")
    plt.xlabel("iteration step")
    plt.ylabel("normalized value")
    plt.title("RITM modality evolution")
    plt.legend()
    plt.show()
    
if __name__ == "__main__":
    R0 = perturb_identity(200, flips=400)
    coh, act = iterate_and_measure(R0, steps=20)
    plot_evolution(coh, act)
