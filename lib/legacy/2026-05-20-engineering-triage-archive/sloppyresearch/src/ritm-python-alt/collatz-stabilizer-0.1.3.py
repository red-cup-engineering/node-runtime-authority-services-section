from sim import *
import matplotlib.pyplot as plt
from collections import defaultdict

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

# --- Experiment driver ---
def run_collatz_experiment_residues(n=32, steps=10, closure_step=1, mod:int=6, verbose=True):
    Y0 = line_graph(n)
    R0 = relation_from_pairs(n, n, collatz_pairs(n))
    hist = evolve_RY_stepwise(R0, Y0, steps=steps, closure_step=closure_step, verbose=verbose)
    per_residue = []
    for R, Y, S, sig in hist:
        res = residue_metrics(R, Y, mod=mod)
        per_residue.append(res)
    return hist, per_residue

# --- Visualization ---
def plot_residue_dynamics(per_residue):
    mods = sorted(list(per_residue[0].keys()))
    steps = range(len(per_residue))
    fig, ax = plt.subplots(2, 1, figsize=(7,6))
    for m in mods:
        S_vals = [res[m][0] for res in per_residue]
        σ_vals = [res[m][1] for res in per_residue]
        ax[0].plot(steps, S_vals, marker='o', label=f"mod {m}")
        ax[1].plot(steps, σ_vals, marker='o', label=f"mod {m}")
    ax[0].set_title('Action S per residue class')
    ax[0].set_xlabel('Step')
    ax[0].set_ylabel('S')
    ax[0].legend()
    ax[1].set_title('σ coherence per residue class')
    ax[1].set_xlabel('Step')
    ax[1].set_ylabel('σ')
    ax[1].legend()
    plt.tight_layout()
    plt.show()

# --- Main ---
if __name__ == "__main__":
    hist, per_residue = run_collatz_experiment_residues(n=36, steps=10, closure_step=1, mod=6)
    plot_residue_dynamics(per_residue)
    Rf, Yf, Sf, sigf = hist[-1]
    print("Final stabilized indices:", defect_rows(Rf, Yf))
