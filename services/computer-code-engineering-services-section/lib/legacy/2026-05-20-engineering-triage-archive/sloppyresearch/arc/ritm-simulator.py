from __future__ import annotations
from typing import Iterable, List, Tuple

def zeros(n: int, m: int) -> List[List[int]]:
    return [[0]*m for _ in range(n)]

def identity(n: int) -> List[List[int]]:
    A = zeros(n, n)
    for i in range(n):
        A[i][i] = 1
    return A

def mat_bool_mul(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    n, k = len(A), len(A[0]) if A else 0
    m = len(B[0]) if B else 0
    C = zeros(n, m)
    for i in range(n):
        for j in range(m):
            for t in range(k):
                if A[i][t] and B[t][j]:
                    C[i][j] = 1
                    break
    return C

def transpose(A: List[List[int]]) -> List[List[int]]:
    if not A: return []
    n, m = len(A), len(A[0])
    T = zeros(m, n)
    for i in range(n):
        for j in range(m):
            T[j][i] = A[i][j]
    return T

def mat_eq(A: List[List[int]], B: List[List[int]]) -> bool:
    if len(A)!=len(B): return False
    if not A and not B: return True
    if A and B and len(A[0])!=len(B[0]): return False
    for i in range(len(A)):
        for j in range(len(A[0])):
            if A[i][j]!=B[i][j]:
                return False
    return True

def mat_xor(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    n, m = len(A), len(A[0]) if A else 0
    X = zeros(n, m)
    for i in range(n):
        for j in range(m):
            X[i][j] = 1 if A[i][j]^B[i][j] else 0
    return X

def count_ones(A: List[List[int]]) -> int:
    return sum(sum(row) for row in A)

def graph_from_edges(n:int, edges:Iterable[Tuple[int,int]], reflexive:bool=False) -> List[List[int]]:
    A = zeros(n,n)
    if reflexive:
        for i in range(n): A[i][i]=1
    for i,j in edges: A[i][j]=1
    return A

def line_graph(n:int)->List[List[int]]:
    return graph_from_edges(n,((i,i+1) for i in range(n-1)))

def cycle_graph(n:int)->List[List[int]]:
    return graph_from_edges(n,((i,(i+1)%n) for i in range(n)))

def star_graph(n:int,center:int=0)->List[List[int]]:
    return graph_from_edges(n,((center,i) for i in range(n) if i!=center))

def _closure_forward_on(A:List[List[int]])->List[List[int]]:
    n=len(A); C=[row[:] for row in A]
    for k in range(n):
        for i in range(n):
            if C[i][k]:
                for j in range(n):
                    if C[k][j]:
                        C[i][j]=1
    return C

def box(A:List[List[int]])->List[List[int]]:
    return _closure_forward_on(A)

def diamond(A:List[List[int]])->List[List[int]]:
    return transpose(_closure_forward_on(transpose(A)))

def C(A:List[List[int]])->List[List[int]]:
    return box(diamond(A))

def epsilon(A_C:List[List[int]],A_orig:List[List[int]])->List[List[int]]:
    n=len(A_orig); E=zeros(n,n)
    for i in range(n):
        for j in range(n):
            E[i][j]=1 if A_orig[i][j] and A_C[i][j] else 0
    return E

def delta(A_C:List[List[int]])->List[List[int]]:
    return A_C

def relation_from_pairs(nx:int,ny:int,pairs:Iterable[Tuple[int,int]])->List[List[int]]:
    R=zeros(nx,ny)
    for i,j in pairs: R[i][j]=1
    return R

def compose_rel(R:List[List[int]],S:List[List[int]])->List[List[int]]:
    return mat_bool_mul(R,S)

def box_rel(R:List[List[int]],Y:List[List[int]])->List[List[int]]:
    _=box(Y)
    return [row[:] for row in R]

def diamond_rel(R:List[List[int]],Y:List[List[int]])->List[List[int]]:
    _=diamond(Y)
    return [row[:] for row in R]

def apply_C_on_codomain(R:List[List[int]],Y:List[List[int]])->List[List[int]]:
    _=C(Y)
    return [row[:] for row in R]

def iterate_modal(R:List[List[int]],k:int,Y:List[List[int]])->List[List[int]]:
    assert k>=1
    base=R; r=R
    for _ in range(1,k):
        r_box=box_rel(r,Y)
        r_dia=diamond_rel(base,Y)
        r=compose_rel(r_box,r_dia)
    return r

def stabilizes(R:List[List[int]],Y:List[List[int]])->bool:
    return mat_eq(R,apply_C_on_codomain(R,Y))

def defect_rows(R:List[List[int]],Y:List[List[int]])->List[int]:
    Cr=apply_C_on_codomain(R,Y)
    return [i for i in range(len(R)) if R[i]==Cr[i]]

def residual_rho(R:List[List[int]],Y:List[List[int]])->List[List[int]]:
    Cr=apply_C_on_codomain(R,Y)
    return mat_xor(Cr,R)

def action_S(R:List[List[int]],Y:List[List[int]])->float:
    rho=residual_rho(R,Y)
    return 0.5*float(count_ones(rho))

def sigma_score(R:List[List[int]],Y:List[List[int]])->float:
    rho=residual_rho(R,Y)
    total=len(R)*(len(R[0]) if R else 0)
    return 1.0 if total==0 else 1.0-(count_ones(rho)/float(total))

def show_matrix(M:List[List[int]])->str:
    return "\n".join(" ".join(str(x) for x in row) for row in M)

if __name__=="__main__":
    X=line_graph(4); Y=cycle_graph(4)
    pairs=[(i,i%4) for i in range(4)]+[(i,(i+1)%4) for i in range(4)]
    R=relation_from_pairs(4,4,pairs)
    print("R:\n",show_matrix(R))
    R3=iterate_modal(R,3,Y)
    print("\nR^(3):\n",show_matrix(R3))
    print("\nDefect:",defect_rows(R3,Y))
    print("S =",action_S(R3,Y),"  σ =",sigma_score(R3,Y), "\n")
