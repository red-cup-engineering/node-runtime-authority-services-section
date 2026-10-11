"""
collatz_experiments.py — Explorations in Collatz-Space using RITM physics.

This script imports ritm.py, defines constructors for several Collatz-family graphs,
and runs comonadic stabilization experiments to measure defect (S) and coherence (σ).
"""

from ritm import evolve, show_matrix
from typing import List


# --------------------------------------------------------------------
# Graph constructors for Collatz-space
# --------------------------------------------------------------------

def integer_graph(n: int) -> List[List[int]]:
    """Bidirectional line: i→i±1 when in range."""
    A = [[0]*n for _ in range(n)]
    for i in range(n):
        if i + 1 < n:
            A[i][i + 1] = 1
        if i - 1 >= 0:
            A[i][i - 1] = 1
    return A


def arithmetic_graph(n: int, offsets: List[int]) -> List[List[int]]:
    """Additive generator graph: connect i→i+k for each k in offsets."""
    A = [[0]*n for _ in range(n)]
    for i in range(n):
        for k in offsets:
            j = i + k
            if 0 <= j < n:
                A[i][j] = 1
    return A


def affine_graph(n: int, a: int, b: int, d: int) -> List[List[int]]:
    """Two-branch affine map: even→i/d, odd→a*i+b."""
    A = [[0]*n for _ in range(n)]
    for i in range(n):
        j = (i // d) if i % 2 == 0 else a * i + b
        if 0 <= j < n:
            A[i][j] = 1
    return A


def collatz_graph(n: int) -> List[List[int]]:
    """Standard Collatz map (a,b,d)=(3,1,2)."""
    return affine_graph(n, a=3, b=1, d=2)


def residue_graph(n: int, m: int) -> List[List[int]]:
    """Connect numbers with same residue mod m."""
    A = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i % m == j % m:
                A[i][j] = 1
    return A


# --------------------------------------------------------------------
# Experiment runners
# --------------------------------------------------------------------

def run_experiment(name: str, R: List[List[int]], Y: List[List[int]], sigma_target=1.0, step_limit=50):
    print(f"\n=== {name} ===")
    hist = evolve(R, Y, sigma_target=sigma_target, step_limit=step_limit)
    final_S = hist[-1][2]
    final_sigma = hist[-1][3]
    print(f"Final S={final_S:.6f}, σ={final_sigma:.6f}, steps={len(hist)}")
   # print(show_matrix(hist[-1][1]))
    return hist


def main():
    n = 40

    # 1. Base: integer bidirectional topology
    Y_int = integer_graph(n)
    R_int = integer_graph(n)
    run_experiment("Integer graph self-stabilization", R_int, Y_int)

    # 2. Arithmetic additive offsets
    Y_add = arithmetic_graph(n, offsets=[1, -1, 2, -2])
    R_add = arithmetic_graph(n, offsets=[1])
    run_experiment("Arithmetic graph", R_add, Y_add)

    # 3. Affine families
    for a, b, d in [(3, 1, 2), (5, 1, 2), (3, 1, 3)]:
        name = f"Affine (a={a}, b={b}, d={d})"
        R_aff = affine_graph(n, a, b, d)
        Y_aff = integer_graph(n)
        run_experiment(name, R_aff, Y_aff)

    # 4. Collatz proper
    R_col = collatz_graph(n)
    Y_col = integer_graph(n)
    run_experiment("Collatz (3x+1)", R_col, Y_col)

    # 5. Residue coherence test
    for m in [4, 6, 8, 12]:
        Y_res = residue_graph(n, m)
        R_res = collatz_graph(n)
        run_experiment(f"Collatz residue mod {m}", R_res, Y_res)


if __name__ == "__main__":
    main()
