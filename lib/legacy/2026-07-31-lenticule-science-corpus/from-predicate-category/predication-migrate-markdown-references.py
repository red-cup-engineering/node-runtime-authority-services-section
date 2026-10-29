"""One-shot script: bulk-update markdown references from old tool paths to
the new `predication_categories` per-note module paths.

Mappings are based on the supersession recorded in `README.md`. The script
operates on every `.md` file under the chapter root (excluding `tools/`,
which has its own scripts and shouldn't be touched).

Run from the chapter root: `python -m predication_categories.migrate_markdown_references`.

After running, manually inspect `git diff` for any references that should be
preserved (e.g., references in narrative discussions of the migration history).
"""

from __future__ import annotations

import re
from pathlib import Path


# Mapping from old tool path patterns to new per-note module paths.
# Order matters: more specific patterns first.
REPLACEMENTS = [
    # verify-zero-dim-curry → per-fiber-curry example
    (
        r"tools/verify-zero-dim-curry(/[\w._-]+)?",
        "tools/predication_categories/examples/per_fiber_d_frame_curry_on_belnap_fiber.py",
    ),
    # cosettling-enumerator → iterated cosettling theorem module
    (
        r"tools/cosettling-enumerator(/[\w._-]+)?",
        "tools/predication_categories/theorems/iterated_cosettling_counts_derivable_cells.py",
    ),
    # regime-classifier → four-regime-dichotomy theorem module
    (
        r"tools/regime-classifier(/[\w._-]+)?",
        "tools/predication_categories/theorems/four_regime_dichotomy.py",
    ),
    # n-ary-settling → causal-triples-3-ary benchmark
    (
        r"tools/n-ary-settling(/[\w._-]+)?",
        "tools/predication_categories/examples/benchmark_causal_triples_3_ary.py",
    ),
    # stochastic-settling → stochastic-stationary theorem module
    (
        r"tools/stochastic-settling(/[\w._-]+)?",
        "tools/predication_categories/theorems/stochastic_stationary_as_settling.py",
    ),
    # lawvere-quantale-settling and continuous-V-step-n → continuous-state regime
    (
        r"tools/lawvere-quantale-settling(/[\w._-]+)?",
        "tools/predication_categories/theorems/continuous_state_regime_classification.py",
    ),
    (
        r"tools/continuous-V-step-n(/[\w._-]+)?",
        "tools/predication_categories/theorems/continuous_state_regime_classification.py",
    ),
    # lorentzian-causal-set → benchmark-lorentzian-causal-set
    (
        r"tools/lorentzian-causal-set(/[\w._-]+)?",
        "tools/predication_categories/examples/benchmark_lorentzian_causal_set.py",
    ),
    # void-cone-comparison → void-cone-associated-graded-direct theorem
    (
        r"tools/void-cone-comparison(/[\w._-]+)?",
        "tools/predication_categories/theorems/void_cone_associated_graded_direct.py",
    ),
    # strong-mld-orbits → strong-mld-via-composed-duality theorem
    (
        r"tools/strong-mld-orbits(/[\w._-]+)?",
        "tools/predication_categories/theorems/strong_mld_via_composed_duality.py",
    ),
    # kripke-to-settling and crdt-to-settling → benchmark-5/6-paraconsistency
    (
        r"tools/kripke-to-settling(/[\w._-]+)?",
        "tools/predication_categories/examples/benchmark_5_epistemic_kripke.py",
    ),
    (
        r"tools/crdt-to-settling(/[\w._-]+)?",
        "tools/predication_categories/examples/benchmark_5_epistemic_kripke.py",
    ),
    # Substitution benchmark family — these all collapse into per-substitution benchmark modules
    (
        r"tools/d-frame-cohomology(/[\w._-]+)?",
        "tools/predication_categories/examples/benchmark_1_fibonacci.py",
    ),
    (
        r"tools/anderson-putnam-cohomology(/[\w._-]+)?",
        "tools/predication_categories/examples/benchmark_1_fibonacci.py",
    ),
    (
        r"tools/verdier-dual(/[\w._-]+)?",
        "tools/predication_categories/examples/benchmark_1_fibonacci.py",
    ),
    (
        r"tools/run-benchmark(/[\w._-]+)?",
        "tools/predication_categories/examples/benchmark_1_fibonacci.py",
    ),
]


def chapter_root() -> Path:
    return Path(__file__).parent.parent.parent


def main() -> int:
    root = chapter_root()
    md_files = list(root.glob("**/*.md"))
    # Exclude things under tools/ (those are the new package's own files)
    md_files = [
        f for f in md_files
        if "tools" not in f.relative_to(root).parts
    ]

    total_subs = 0
    files_changed = 0
    for fp in md_files:
        body = fp.read_text(encoding="utf-8")
        new_body = body
        for pattern, replacement in REPLACEMENTS:
            new_body = re.sub(pattern, replacement, new_body)
        if new_body != body:
            n_subs = sum(
                len(re.findall(pat, body)) for pat, _ in REPLACEMENTS
            )
            total_subs += n_subs
            files_changed += 1
            fp.write_text(new_body, encoding="utf-8")

    print(f"Updated {files_changed} files, ~{total_subs} reference replacements.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
