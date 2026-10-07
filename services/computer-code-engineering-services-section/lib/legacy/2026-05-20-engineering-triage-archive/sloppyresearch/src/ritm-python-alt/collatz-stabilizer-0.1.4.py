# RITM-Collatz Experiment Simulator with Residue-Class Analysis & Decay Rates
# Requires: sim.py in the same directory

from sim import *
import matplotlib.pyplot as plt
from collections import defaultdict
from typing import Dict, List, Tuple

# --- Stepwise comonadic operators ---
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

# --- Collatz relation construction ---
def collatz_pairs(n:int):
    pairs = []
    for i in range(1, n):
        if i % 2 == 0:
            j = i // 2
        else:
            j = 3 * i + 1
        if j < n:
            pairs.append((i, j))
    return pairs

# --- Stepwise evolution ---
def evolve_RY_stepwise(R, Y, steps=10, closure_step=1, verbose=True):
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

# --- Residue-class analysis ---
def residue_partition(n:int, mod:int) -> Dict[int, List[int]]:
    part = defaultdict(list)
    for i in range(n):
        part[i % mod].append(i)
    return part

def residue_metrics(R: List[List[int]], Y: List[List[int]], mod:int=6):
    n = len(Y)
    classes = residue_partition(n, mod)
    res_metrics = {}
    for r, idxs in classes.items():
        if not idxs:
            continue
        subR = [[R[i][j] for j in idxs] for i in idxs]
        subY = [[Y[i][j] for j in idxs] for i in idxs]
        S = action_S(subR, subY)
        sig = sigma_score(subR, subY)
        res_metrics[r] = (S, sig)
    return res_metrics

# Compute simple decay stats: time-to-zero S, first-step drop ratio, and area under S
DefStats = Dict[int, Dict[str, float]]

def residue_decay_stats(per_residue: List[Dict[int, Tuple[float, float]]]) -> DefStats:
    # per_residue[t][r] = (S, σ)
    T = len(per_residue)
    residues = sorted(per_residue[0].keys())
    stats: DefStats = {}
    for r in residues:
        S_series = [per_residue[t][r][0] for t in range(T)]
        # time to hit zero S
        t0 = None
        for t, Sv in enumerate(S_series):
            if Sv == 0:
                t0 = t
                break
        # first-step drop ratio (avoid division by 0)
        S0 = S_series[0]
        S1 = S_series[1] if T > 1 else S0
        drop = (S0 - S1) / S0 if S0 > 0 else 1.0
        # discrete area under curve (AUC)
        auc = sum(S_series)
        stats[r] = {"time_to_zero": float(t0 if t0 is not None else -1),
                    "first_drop_ratio": float(drop),
                    "auc_S": float(auc)}
    return stats

# --- Experiment drivers ---
def run_collatz_experiment_residues(n=32, steps=10, closure_step=1, mod:int=6, verbose=True):
    Y0 = line_graph(n)
    R0 = relation_from_pairs(n, n, collatz_pairs(n))
    hist = evolve_RY_stepwise(R0, Y0, steps=steps, closure_step=closure_step, verbose=verbose)
    per_residue = []
    for R, Y, S, sig in hist:
        res = residue_metrics(R, Y, mod=mod)
        per_residue.append(res)
    return hist, per_residue

# Multiple moduli wrapper

def run_multi_moduli(n=48, steps=10, closure_step=1, mod_list:List[int]=[4,6,8,12], verbose=False):
    results = {}
    for m in mod_list:
        if verbose:
            print(f"\n=== modulus {m} ===")
        hist, per_residue = run_collatz_experiment_residues(n=n, steps=steps, closure_step=closure_step, mod=m, verbose=verbose)
        stats = residue_decay_stats(per_residue)
        results[m] = {"hist": hist, "per_residue": per_residue, "stats": stats}
    return results

# --- Visualization ---

def plot_residue_dynamics(per_residue, title_prefix=""):
    mods = sorted(list(per_residue[0].keys()))
    steps = range(len(per_residue))
    fig, ax = plt.subplots(2, 1, figsize=(7,6))
    for m in mods:
        S_vals = [res[m][0] for res in per_residue]
        σ_vals = [res[m][1] for res in per_residue]
        ax[0].plot(steps, S_vals, marker='o', label=f"mod {m}")
        ax[1].plot(steps, σ_vals, marker='o', label=f"mod {m}")
    ax[0].set_title(f'{title_prefix}Action S per residue class')
    ax[0].set_xlabel('Step')
    ax[0].set_ylabel('S')
    ax[0].legend()
    ax[1].set_title(f'{title_prefix}σ coherence per residue class')
    ax[1].set_xlabel('Step')
    ax[1].set_ylabel('σ')
    ax[1].legend()
    plt.tight_layout()
    plt.show()


def plot_multi_moduli(results):
    # results[m]["per_residue"]
    M = len(results)
    figS, axesS = plt.subplots(M, 1, figsize=(7, 3*M), sharex=True)
    figσ, axesσ = plt.subplots(M, 1, figsize=(7, 3*M), sharex=True)
    if M == 1:
        axesS = [axesS]
        axesσ = [axesσ]
    for i, m in enumerate(sorted(results.keys())):
        per_residue = results[m]["per_residue"]
        residues = sorted(per_residue[0].keys())
        steps = range(len(per_residue))
        for r in residues:
            S_vals = [res[r][0] for res in per_residue]
            σ_vals = [res[r][1] for res in per_residue]
            axesS[i].plot(steps, S_vals, marker='o', label=f"r={r}")
            axesσ[i].plot(steps, σ_vals, marker='o', label=f"r={r}")
        axesS[i].set_title(f"Action S by residues (mod {m})")
        axesS[i].set_ylabel('S')
        axesS[i].legend(ncol=min(6, len(residues)))
        axesσ[i].set_title(f"σ by residues (mod {m})")
        axesσ[i].set_ylabel('σ')
        axesσ[i].legend(ncol=min(6, len(residues)))
    axesS[-1].set_xlabel('Step')
    axesσ[-1].set_xlabel('Step')
    figS.tight_layout(); figσ.tight_layout()
    plt.show()


def print_decay_tables(results):
    # pretty-print decay stats per modulus
    for m in sorted(results.keys()):
        stats = results[m]["stats"]
        residues = sorted(stats.keys())
        print(f"\n=== Decay stats (mod {m}) ===")
        print("res  time_to_zero  first_drop  auc_S")
        for r in residues:
            s = stats[r]
            print(f"{r:>3}  {int(s['time_to_zero']):>12}  {s['first_drop_ratio']:.3f}     {s['auc_S']:.1f}")
        # modulus-level aggregates
        ttz_vals = [stats[r]['time_to_zero'] for r in residues]
        drop_vals = [stats[r]['first_drop_ratio'] for r in residues]
        auc_vals = [stats[r]['auc_S'] for r in residues]
        avg = lambda xs: sum(xs)/len(xs) if xs else 0.0
        print(f"-- avg --  {avg(ttz_vals):>12.2f}  {avg(drop_vals):.3f}     {avg(auc_vals):.1f}")

# --- Main ---
if __name__ == "__main__":
    # single-modulus quick run
    hist, per_residue = run_collatz_experiment_residues(n=36, steps=10, closure_step=1, mod=6)
    plot_residue_dynamics(per_residue)

    # multi-moduli comparison
    results = run_multi_moduli(n=60, steps=10, closure_step=1, mod_list=[4,6,8,12], verbose=False)
    plot_multi_moduli(results)
    print_decay_tables(results)

    # final stabilized set (for the last modulus run only)
    last_m = sorted(results.keys())[-1]
    Rf, Yf, Sf, sigf = results[last_m]["hist"][-1]
    print("\nFinal stabilized indices (last run):", defect_rows(Rf, Yf))
