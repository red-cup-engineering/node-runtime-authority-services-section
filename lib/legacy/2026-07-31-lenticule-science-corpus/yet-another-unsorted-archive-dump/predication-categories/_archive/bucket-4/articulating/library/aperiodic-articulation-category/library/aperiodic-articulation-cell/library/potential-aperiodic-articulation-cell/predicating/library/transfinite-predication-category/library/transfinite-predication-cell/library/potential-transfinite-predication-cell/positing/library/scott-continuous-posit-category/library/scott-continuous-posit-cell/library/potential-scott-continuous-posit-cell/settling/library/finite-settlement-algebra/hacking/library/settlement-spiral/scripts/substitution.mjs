// substitution.mjs — the runnable core of `residuation-forces-a-spiral`.
//
// A substitution (letter → word over the same alphabet) has a non-negative integer
// incidence matrix M (M[i][j] = #occurrences of letter i in σ(letter j)). Residuation's
// integrality forces M ∈ ℕ^{n×n}; Perron–Frobenius gives a dominant eigenvalue λ — the
// inflation factor / Pisot number / spiral growth-per-generation. We compute it by power
// iteration (M is primitive for the families we use).

export function alphabet(sub) {
  return Object.keys(sub);
}

export function substitutionMatrix(sub) {
  const A = alphabet(sub);
  const idx = Object.fromEntries(A.map((l, i) => [l, i]));
  const n = A.length;
  const M = Array.from({ length: n }, () => Array(n).fill(0));
  for (const j of A) for (const ch of sub[j]) M[idx[ch]][idx[j]] += 1; // letter ch appears in σ(j)
  return M;
}

// Dominant (Perron) eigenvalue via power iteration on the incidence matrix.
export function inflationFactor(sub, { iters = 500 } = {}) {
  const M = substitutionMatrix(sub);
  const n = M.length;
  let x = Array(n).fill(1);
  let lambda = 0;
  for (let t = 0; t < iters; t++) {
    const y = M.map((row) => row.reduce((s, m, j) => s + m * x[j], 0));
    const norm = Math.hypot(...y);
    lambda = norm / Math.hypot(...x);
    x = y.map((v) => v / norm);
  }
  return lambda;
}
