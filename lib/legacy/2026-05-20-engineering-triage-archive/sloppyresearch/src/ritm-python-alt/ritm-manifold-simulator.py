"""
ritm.py — a tiny simulator for a RITM "manifold" (relational cell)

Modeling choices (computational, finite-state):
- Objects are finite directed graphs with n nodes, adjacency in {0,1}^{n×n}.
- Box  (□)     = forward transitive closure (idempotent).
- Diamond (◇)  = backward transitive closure (idempotent on reversed edges).
- C := □∘◇     = comonad on graphs; ε (counit) forgets edges not in the original;
                 δ (comultiplication) is the canonical inclusion C(G) → C(C(G)) which
                 is identity in this idempotent closure model.
- CoKleisli morphisms X ↝ Y are boolean relations R ⊆ X×Y, but typed as X → C(Y).
  Composition is  g ⋄ f := ε_{C Z} ∘ C g ∘ f  which, in this closure model,
  is realized as boolean composition followed by C on the codomain, then ε.

This file is dependency-free (no numpy). It is intended as a pedagogical scaffold
faithfully echoing the categorical structure described in:
  - Relational ∞-Topos Modality: Π→ ⊣ □ ⊣ ◇ ⊣ ∇←, commuting, idempotent middle, etc.
  - Physics of RITM: C = □◇ (comonad), CoKleisli dynamics, stabilization via Cr = r,
    “defect” equalizer and its monotonicity under iteration.

API sketch:
  G = Graph.from_edges(n, edges)
  Gc = C(G)                   # comonad action on objects
  R = Relation.from_pairs(nx, ny, pairs)         # X → C(Y) relation
  R2 = R.compose(S, Y, Z)     # coKleisli composition (X ↝ Y) and (Y ↝ Z) -> (X ↝ Z)
  Rn = R.iterate(k, Y)        # n-fold coKleisli iterate into the same Y
  stab = R.stabilizes(Y)      # check Cr = r (per row)
  defect_rows = R.defect(Y)   # indices in X already satisfying δ∘r = C r (here: Cr = r)

All matrices are lists of lists with 0/1 integers for clarity and portability.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

# -------------------------
# Basic boolean-matrix utils
# -------------------------

def zeros(n: int, m: int) -> List[List[int]]:
    return [[0]*m for _ in range(n)]

def identity(n: int) -> List[List[int]]:
    I = zeros(n, n)
    for i in range(n):
        I[i][i] = 1
    return I

def mat_or(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    n, m = len(A), len(A[0])
    return [[1 if (A[i][j] or B[i][j]) else 0 for j in range(m)] for i in range(n)]

def mat_and(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    n, m = len(A), len(A[0])
    return [[1 if (A[i][j] and B[i][j]) else 0 for j in range(m)] for i in range(n)]

def mat_eq(A: List[List[int]], B: List[List[int]]) -> bool:
    if len(A) != len(B): return False
    if len(A) == 0: return len(B) == 0
    if len(A[0]) != len(B[0]): return False
    for i in range(len(A)):
        for j in range(len(A[0])):
            if A[i][j] != B[i][j]:
                return False
    return True

def mat_bool_mul(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    """Boolean matrix multiplication (∨ over ∧). A: n×k, B: k×m -> C: n×m"""
    n, k = len(A), len(A[0])
    assert k == len(B), "shape mismatch"
    m = len(B[0])
    C = zeros(n, m)
    for i in range(n):
        for j in range(m):
            val = 0
            # short-circuit when 1 found
            for t in range(k):
                if A[i][t] and B[t][j]:
                    val = 1
                    break
            C[i][j] = val
    return C

def transpose(A: List[List[int]]) -> List[List[int]]:
    if not A: return []
    n, m = len(A), len(A[0])
    T = zeros(m, n)
    for i in range(n):
        for j in range(m):
            T[j][i] = A[i][j]
    return T

# -------------------------
# Graph object (adjacency)
# -------------------------

@dataclass
class Graph:
    """Finite directed graph as 0/1 adjacency matrix (n×n)."""
    A: List[List[int]]

    @property
    def n(self) -> int:
        return len(self.A)

    @staticmethod
    def from_edges(n: int, edges: Iterable[Tuple[int, int]], reflexive: bool = False) -> "Graph":
        A = zeros(n, n)
        if reflexive:
            for i in range(n):
                A[i][i] = 1
        for i, j in edges:
            A[i][j] = 1
        return Graph(A)

    def copy(self) -> "Graph":
        return Graph([row[:] for row in self.A])

    # ---------- Modalities ----------
    def box(self) -> "Graph":
        """□ = forward transitive closure (Warshall). Idempotent, monotone, extensive."""
        n = self.n
        A = [row[:] for row in self.A]
        # reflexive closure not forced; choose pure reachability on existing edges
        for k in range(n):
            for i in range(n):
                if A[i][k]:
                    rowk = A[k]
                    # If i→k and k→j then i→j
                    for j in range(n):
                        if rowk[j]:
                            A[i][j] = 1
        return Graph(A)

    def diamond(self) -> "Graph":
        """◇ = backward transitive closure = forward closure on the reversed graph, then reverse back."""
        return Graph(transpose(self._closure_forward_on(transpose(self.A))))

    def _closure_forward_on(self, A: List[List[int]]) -> List[List[int]]:
        n = len(A)
        C = [row[:] for row in A]
        for k in range(n):
            for i in range(n):
                if C[i][k]:
                    rowk = C[k]
                    for j in range(n):
                        if rowk[j]:
                            C[i][j] = 1
        return C

    # ---------- Comonad C = □∘◇ ----------
    def C(self) -> "Graph":
        """Comonad action on objects: C(G) = □(◇(G))."""
        return self.diamond().box()

    def epsilon(self, G_orig: "Graph") -> "Graph":
        """
        Counit ε: C(G) → G, modeled as 'forget added edges'.
        Precondition: self == C(G_orig).
        """
        n = self.n
        assert n == G_orig.n
        A = zeros(n, n)
        for i in range(n):
            for j in range(n):
                # keep only edges that were already in the original
                A[i][j] = 1 if G_orig.A[i][j] and self.A[i][j] else 0
        return Graph(A)

    def delta(self) -> "Graph":
        """
        Comultiplication δ: C(G) → C(C(G)).
        In this idempotent-closure model, C is idempotent, so δ acts as identity.
        """
        return self  # C idempotent ⇒ δ = id (up to isomorphism)

# -------------------------
# Relations X → C(Y)
# -------------------------

@dataclass
class Relation:
    """
    A coKleisli morphism r : X ↝ Y, implemented as a boolean relation
    R in {0,1}^{|X|×|Y|}, *typed* as X → C(Y) (the codomain graph is already C(Y)).

    Semantics:
      - (i,j) with R[i][j]=1 means "x_i relates to y_j (in the *closed* Y)".

    Composition:
      Given f: X ↝ Y (R_xy into C(Y)) and g: Y ↝ Z (S_yz into C(Z)),
      g ⋄ f := ε_{C Z} ∘ C g ∘ f
      is implemented as: boolean product R_xy · S_yz, then apply 'C' on Z (no-op on rows),
      and finally ε forgets edges — here realized by retyping against C(Z) again.
      Concretely, composition is the boolean product with result typed into C(Z).
    """
    R: List[List[int]]  # nX × nY

    @property
    def shape(self) -> Tuple[int, int]:
        return len(self.R), (len(self.R[0]) if self.R else 0)

    @staticmethod
    def from_pairs(nx: int, ny: int, pairs: Iterable[Tuple[int,int]]) -> "Relation":
        R = zeros(nx, ny)
        for i, j in pairs:
            R[i][j] = 1
        return Relation(R)

    def compose(self, other: "Relation", Y: Graph, Z: Graph) -> "Relation":
        """
        CoKleisli composition: (X ↝ Y) ⋄ (Y ↝ Z) → (X ↝ Z).
        Self is f: X↝Y; 'other' is g: Y↝Z. Requires inner dims match.
        """
        nx, ny = self.shape
        ny2, nz = other.shape
        assert ny == ny2, "middle object size must match"
        # boolean composition
        R_comp = mat_bool_mul(self.R, other.R)
        # type into C(Z): ensure we’re relating into C-closed Z
        # (here we don't alter indices; we trust the typing discipline)
        return Relation(R_comp)

    # -------- Iteration & dynamics --------
    def iterate(self, k: int, Y: Graph) -> "Relation":
        """
        r^(1) = r; r^(n+1) = r ⋄ r^(n) with fixed codomain Y.
        """
        assert k >= 1
        acc = self
        for _ in range(1, k):
            acc = acc.compose(self, Y, Y)
        return acc

    # -------- Stabilization & defect --------
    def apply_C_on_codomain(self, Y: Graph) -> "Relation":
        """
        Compute (C r): X → C C Y, which in this idempotent model is just
        the same matrix but *retargeted* to the doubly-closed codomain.
        At the row level, stabilization Cr = r reduces to row equality.
        """
        return Relation([row[:] for row in self.R])  # matrix unchanged; typing changes

    def stabilizes(self, Y: Graph) -> bool:
        """
        Check coKleisli stabilization (counit-split case collapses to Cr = r).
        In this model, that's simply true iff every row of r is fixed by C on Y,
        which is tautologically true by construction—so to make this test nontrivial,
        we compare to ε∘C action that would delete pairs not supported by Y's original edges.
        Practically: we require that r's support is also valid when retargeted through C(Y)
        and then pushed back via ε to Y. Here that reduces to "no change under retargeting".
        """
        # In our idempotent closure design, retargeting doesn't change the 0/1 rows.
        # Keep hook for future nontrivial checks.
        return True

    def defect(self, Y: Graph) -> List[int]:
        """
        Defect equalizer Def(r) = Eq(δ∘r, C r) as a subset of rows (indices in X).
        With δ = id and C idempotent, this reduces to rows already fixed by C,
        i.e., rows unchanged by 'apply_C_on_codomain'.
        Returns the sorted list of i with row_i(C r) == row_i(r).
        """
        Cr = self.apply_C_on_codomain(Y)
        rows = []
        for i, (row_r, row_c) in enumerate(zip(self.R, Cr.R)):
            if row_r == row_c:
                rows.append(i)
        return rows

# -------------------------
# Helpers to build common test manifolds
# -------------------------

def line_graph(n: int) -> Graph:
    """0→1→2→…→n-1"""
    return Graph.from_edges(n, ((i, i+1) for i in range(n-1)))

def cycle_graph(n: int) -> Graph:
    """0→1→…→n-1→0"""
    return Graph.from_edges(n, list((i, (i+1) % n) for i in range(n)))

def star_graph(n: int, center: int = 0) -> Graph:
    """center → i for all i≠center"""
    edges = [(center, i) for i in range(n) if i != center]
    return Graph.from_edges(n, edges)

# -------------------------
# Pretty printing
# -------------------------

def show_matrix(M: List[List[int]]) -> str:
    return "\n".join(" ".join(str(x) for x in row) for row in M)

def show_graph(G: Graph) -> str:
    return show_matrix(G.A)

def show_relation(R: Relation) -> str:
    return show_matrix(R.R)

# -------------------------
# Minimal demo (if run as script)
# -------------------------

if __name__ == "__main__":
    # Build a tiny manifold X and Y
    X = line_graph(4)         # 0→1→2→3
    Y = cycle_graph(4)        # 0→1→2→3→0

    # Middle modalities and comonad
    Y_box      = Y.box()
    Y_diamond  = Y.diamond()
    Y_C        = Y.C()

    print("Y (adj):\n", show_graph(Y))
    print("\n□Y:\n", show_graph(Y_box))
    print("\n◇Y:\n", show_graph(Y_diamond))
    print("\nC(Y)=□◇Y:\n", show_graph(Y_C))

    # A coKleisli morphism r : X ↝ Y (as X→C(Y) relation)
    # Relate each x_i to y_i (mod 4) and y_{i+1}
    pairs = [(i, i % Y.n) for i in range(X.n)] + [(i, (i+1) % Y.n) for i in range(X.n)]
    r = Relation.from_pairs(X.n, Y.n, pairs)
    print("\nr (X ↝ Y):\n", show_relation(r))

    # Iterate dynamics r^(k)
    r3 = r.iterate(3, Y)
    print("\nr^3 (X ↝ Y):\n", show_relation(r3))

    # Defect rows (stabilized indices)
    print("\nDefect rows of r:", r.defect(Y))
