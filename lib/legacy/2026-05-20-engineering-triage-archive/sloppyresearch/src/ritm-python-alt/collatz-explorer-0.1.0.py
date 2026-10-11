# RITM—Affine Family (Collatz-like) Modal Spectrum
# Requires: sim.py in the same directory

from sim import *
import matplotlib.pyplot as plt
from collections import defaultdict
from typing import Dict, List, Tuple, Iterable
import math

# =============================================
# Stepwise comonadic operators
# =============================================

def box_step(A: List[List[int]], steps:int=1) -> List[List[int]]:
    n = len(A)
    C = [row[:] for row in A]
    for _ in range(steps):
        C_next = mat_bool_or(C, mat_bool_mul(C, A))
        for i in range(n):
            C_next[i][i] = 1
        C = C_next
    return C

def diamond_step(A: List[List[int]], steps:int=1) -> List[List[int]]:
    return transpose(box_step(transpose(A), steps=steps))

def C_graph_step(A: List[List[int]], steps:int=1) -> List[List[int]]:
    return box_step(diamond_step(A, steps=steps), steps=steps)

# =============================================
# Relation constructors
# =============================================

def pairs_from_function(n:int, f)->List[Tuple[int,int]]:
    pairs = []
    for i in range(n):
        j = f(i)
        if 0 <= j < n:
            pairs.append((i, j))
    return pairs

# Collatz-like family: even→ n//d  (integer division), odd→ a*n + b
# Standard Collatz is (d=2, a=3, b=1).

def collatz_like_pairs(n:int, d:int=2, a:int=3, b:int=1) -> List[Tuple[int,int]]:
    def f(i:int)->int:
        if i==0: return 0
        if i % 2 == 0:
            return i // d
        else:
            return a*i + b
    return pairs_from_function(n, f)

# Pure affine map f(n)=a*n + b (no parity split)

def affine_pairs(n:int, a:int, b:int) -> List[Tuple[int,int]]:
    return pairs_from_function(n, lambda i: a*i + b)

# =============================================
# Stepwise evolution
# =============================================

def evolve_RY_stepwise(R, Y, steps=10, closure_step=1, verbose=False):
    hist = []
    for t in range(steps):
        CY = C_graph_step(Y, steps=closure_step)
        Rn = mat_bool_mul(R, CY)
        Yn = mat_bool_or(Y, CY)
        S = action_S(Rn, Yn)
        sig = sigma_score(Rn, Yn)
        if verbose:
            print(f"t={t:02d}  S={S:.3f}  σ={sig:.3f}")
        hist.append((Rn, Yn, S, sig))
        if t>0 and abs(hist[-1][2]-hist[-2][2])<1e-9:
            break
        R, Y = Rn, Yn
    return hist

# =============================================
# Residue-class analysis & stats
# =============================================

def residue_partition(n:int, mod:int) -> Dict[int, List[int]]:
    part = defaultdict(list)
    for i in range(n):
        part[i % mod].append(i)
    return part


def residue_metrics(R: List[List[int]], Y: List[List[int]], mod:int=6):
    n = len(Y)
    classes = residue_partition(n, mod)
    res_metrics: Dict[int, Tuple[float,float]] = {}
    for r, idxs in classes.items():
        if not idxs: continue
        subR = [[R[i][j] for j in idxs] for i in idxs]
        subY = [[Y[i][j] for j in idxs] for i in idxs]
        S = action_S(subR, subY)
        sig = sigma_score(subR, subY)
        res_metrics[r] = (S, sig)
    return res_metrics


def residue_decay_stats(per_residue: List[Dict[int, Tuple[float, float]]]):
    T = len(per_residue)
    residues = sorted(per_residue[0].keys())
    stats = {}
    for r in residues:
        S_series = [per_residue[t][r][0] for t in range(T)]
        t0 = None
        for t, Sv in enumerate(S_series):
            if Sv == 0:
                t0 = t
                break
        S0 = S_series[0]
        S1 = S_series[1] if T>1 else S0
        drop = (S0 - S1) / S0 if S0>0 else 1.0
        auc = sum(S_series)
        stats[r] = {"time_to_zero": float(t0 if t0 is not None else -1),
                    "first_drop_ratio": float(drop),
                    "auc_S": float(auc)}
    # Modulus-level aggregates
    def avg(xs): return sum(xs)/len(xs) if xs else 0.0
    agg = {
        "avg_time_to_zero": avg([v["time_to_zero"] for v in stats.values()]),
        "avg_first_drop_ratio": avg([v["first_drop_ratio"] for v in stats.values()]),
        "avg_auc_S": avg([v["auc_S"] for v in stats.values()])
    }
    return stats, agg

# =============================================
# Experiment wrappers
# =============================================

def run_residue_experiment(R, n:int, steps:int, closure_step:int, mod_list:List[int]):
    Y0 = line_graph(n)
    hist = evolve_RY_stepwise(R, Y0, steps=steps, closure_step=closure_step, verbose=False)
    per_mod_residue = {}
    per_mod_agg = {}
    for m in mod_list:
        per_residue = [residue_metrics(Rt, Yt, mod=m) for (Rt, Yt, _, _) in hist]
        stats, agg = residue_decay_stats(per_residue)
        per_mod_residue[m] = per_residue
        per_mod_agg[m] = agg
    return hist, per_mod_residue, per_mod_agg

# Sweep over a,b for collatz-like family (even→n//2, odd→a*n+b)

def sweep_collatz_like(n:int=80, steps:int=10, closure_step:int=1, a_vals:Iterable[int]=range(2,6), b_vals:Iterable[int]=range(1,6), mod_list:List[int]=[4,6,8,12]):
    results = {}
    for a in a_vals:
        for b in b_vals:
            R = relation_from_pairs(n, n, collatz_like_pairs(n, d=2, a=a, b=b))
            hist, per_mod_residue, per_mod_agg = run_residue_experiment(R, n, steps, closure_step, mod_list)
            results[(a,b)] = {"hist": hist, "per_mod_residue": per_mod_residue, "per_mod_agg": per_mod_agg}
    return results

# Optional: sweep pure affine (not default Collatz-like)

def sweep_affine(n:int=80, steps:int=10, closure_step:int=1, a_vals:Iterable[int]=range(2,6), b_vals:Iterable[int]=range(1,6), mod_list:List[int]=[4,6,8,12]):
    results = {}
    for a in a_vals:
        for b in b_vals:
            R = relation_from_pairs(n, n, affine_pairs(n, a, b))
            hist, per_mod_residue, per_mod_agg = run_residue_experiment(R, n, steps, closure_step, mod_list)
            results[(a,b)] = {"hist": hist, "per_mod_residue": per_mod_residue, "per_mod_agg": per_mod_agg}
    return results

# =============================================
# Visualization
# =============================================

def heatmap_mod_spectrum(results:Dict[Tuple[int,int], dict], mod:int, metric:str="avg_auc_S", title_prefix:str="Collatz-like"):
    # Build grid for a,b
    a_vals = sorted({a for (a,_) in results.keys()})
    b_vals = sorted({b for (_,b) in results.keys()})
    Z = [[0.0 for _ in b_vals] for _ in a_vals]
    for ia, a in enumerate(a_vals):
        for ib, b in enumerate(b_vals):
            Z[ia][ib] = results[(a,b)]["per_mod_agg"][mod][metric]
    fig, ax = plt.subplots(figsize=(6,5))
    im = ax.imshow(Z, aspect='auto')
    ax.set_xticks(range(len(b_vals))); ax.set_xticklabels([str(b) for b in b_vals])
    ax.set_yticks(range(len(a_vals))); ax.set_yticklabels([str(a) for a in a_vals])
    ax.set_xlabel('b'); ax.set_ylabel('a')
    ax.set_title(f"{title_prefix}: {metric} (mod {mod})")
    plt.colorbar(im, ax=ax)
    plt.tight_layout(); plt.show()


def print_mod_agg_table(results:Dict[Tuple[int,int], dict], mod:int):
    print(f"\n=== Modulus {mod} aggregates ===")
    print(" a  b   avg_ttz  avg_drop  avg_auc_S")
    for (a,b), rec in sorted(results.items()):
        agg = rec["per_mod_agg"][mod]
        print(f" {a:>1}  {b:>1}   {agg['avg_time_to_zero']:.2f}    {agg['avg_first_drop_ratio']:.3f}     {agg['avg_auc_S']:.2f}")

# =============================================
# Main: run a sweep and visualize
# =============================================
if __name__ == "__main__":
    n = 80
    steps = 10
    closure_step = 1
    mod_list = [4,6,8,12]

    # Sweep Collatz-like family (even→n//2, odd→a*n+b)
    results = sweep_collatz_like(n=n, steps=steps, closure_step=closure_step, a_vals=range(2,6), b_vals=range(1,6), mod_list=mod_list)

    # Show heatmaps for a couple of metrics at key moduli
    heatmap_mod_spectrum(results, mod=6, metric="avg_auc_S", title_prefix="Collatz-like")
    heatmap_mod_spectrum(results, mod=4, metric="avg_auc_S", title_prefix="Collatz-like")

    # Print compact tables at mod 6 and mod 4
    print_mod_agg_table(results, mod=6)
    print_mod_agg_table(results, mod=4)

    # (Optional) compare pure affine family by uncommenting below
    aff_results = sweep_affine(n=n, steps=steps, closure_step=closure_step, a_vals=range(2,6), b_vals=range(1,6), mod_list=mod_list)
    heatmap_mod_spectrum(aff_results, mod=6, metric="avg_auc_S", title_prefix="Affine a*n+b")
    print_mod_agg_table(aff_results, mod=6)
