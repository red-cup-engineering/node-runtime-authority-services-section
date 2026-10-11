"""
collatz_lab.py — extended Collatz-space exploration using RITM physics
with plotting of comonadic stabilization patterns.

Requires:
    ritm.py        — RITM physics core
    collatz.py     — graph constructors and run_experiment()
    matplotlib     — for plotting

Run:
    python3 collatz_lab.py
"""

import json
import matplotlib.pyplot as plt
from collatz import (
    integer_graph,
    affine_graph,
    collatz_graph,
    residue_graph,
    run_experiment
)


# --------------------------------------------------------------------
# Experiment suites
# --------------------------------------------------------------------

def sweep_affine_family(n=60, a_range=(2, 6), b_vals=(1, 2, 3), d_vals=(2, 3)):
    results = []
    for a in range(a_range[0], a_range[1] + 1):
        for b in b_vals:
            for d in d_vals:
                name = f"Affine(a={a}, b={b}, d={d})"
                R = affine_graph(n, a, b, d)
                Y = integer_graph(n)
                hist = run_experiment(name, R, Y)
                S_final = hist[-1][2]
                sigma_final = hist[-1][3]
                results.append({
                    "a": a, "b": b, "d": d,
                    "steps": len(hist),
                    "S_final": S_final,
                    "sigma_final": sigma_final
                })
    return results


def test_collatz_residues(n=60, moduli=(4, 6, 8, 12, 18, 24)):
    results = []
    R = collatz_graph(n)
    for m in moduli:
        Y = residue_graph(n, m)
        name = f"Collatz residue mod {m}"
        hist = run_experiment(name, R, Y)
        results.append({
            "modulus": m,
            "steps": len(hist),
            "S_final": hist[-1][2],
            "sigma_final": hist[-1][3]
        })
    return results


# --------------------------------------------------------------------
# Plotting utilities
# --------------------------------------------------------------------

def plot_affine_results(affine_data):
    plt.figure(figsize=(8, 5))
    for d in sorted(set(r["d"] for r in affine_data)):
        subset = [r for r in affine_data if r["d"] == d]
        x = [r["a"] for r in subset]
        y = [r["sigma_final"] for r in subset]
        plt.plot(x, y, marker="o", label=f"d={d}")
    plt.title("Affine family: coherence σ_final vs a (by d)")
    plt.xlabel("a (odd-branch multiplier)")
    plt.ylabel("final σ")
    plt.ylim(0, 1.05)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("affine_coherence.png")
    print("→ Saved affine_coherence.png")


def plot_residue_results(residue_data):
    plt.figure(figsize=(8, 5))
    x = [r["modulus"] for r in residue_data]
    y = [r["steps"] for r in residue_data]
    plt.bar(x, y, color="skyblue")
    plt.title("Collatz residue topologies: stabilization steps vs modulus")
    plt.xlabel("Modulus (m)")
    plt.ylabel("Steps to stabilization")
    plt.tight_layout()
    plt.savefig("collatz_residue_steps.png")
    print("→ Saved collatz_residue_steps.png")


# --------------------------------------------------------------------
# Main orchestration
# --------------------------------------------------------------------

def main():
    all_results = {}

    print("\n=== Sweeping affine family ===")
    affine_data = sweep_affine_family()
    all_results["affine_family"] = affine_data

    print("\n=== Collatz residue topologies ===")
    residue_data = test_collatz_residues()
    all_results["residue_tests"] = residue_data

    # Save results
    with open("collatz_lab_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("\nResults written to collatz_lab_results.json")

    # Plotting
    plot_affine_results(affine_data)
    plot_residue_results(residue_data)
    plt.show()


if __name__ == "__main__":
    main()
