// settlement-spiral.mjs — the per-regime spiral inflation factors, made runnable.
//
// Each regime's settling spirals by its Pisot number (residuation-forces-a-spiral). The
// substitution whose Perron eigenvalue is that number, per regime:
//   strict-finite      Padovan/Perrin   x³ = x + 1     ρ ≈ 1.3247  (smallest Pisot)
//   scott-continuous   Fibonacci        x² = x + 1     φ ≈ 1.6180  (golden)
//   transfinite        Tribonacci       x³ = x²+x+1    τ ≈ 1.8393
// Ascending the regime tower loosens the spiral toward the n-bonacci limit 2.

import { inflationFactor } from "#substitution";

export const PLASTIC = 1.324717957244746; // root of x³ = x + 1
export const GOLDEN = (1 + Math.sqrt(5)) / 2; // root of x² = x + 1
export const TRIBONACCI = 1.839286755214161; // root of x³ = x² + x + 1

// The regime → substitution table. Each substitution's inflation factor IS the regime spiral.
export const REGIME_SUBSTITUTION = {
  "strict-finite": { name: "Padovan", sub: { a: "b", b: "c", c: "ab" }, constant: PLASTIC },
  "scott-continuous": { name: "Fibonacci", sub: { a: "ab", b: "a" }, constant: GOLDEN },
  "transfinite": { name: "Tribonacci", sub: { a: "ab", b: "ac", c: "a" }, constant: TRIBONACCI },
};

// Compute the inflation factor for a named regime (the executable spiral).
export function regimeInflation(regime, opts) {
  const entry = REGIME_SUBSTITUTION[regime];
  if (!entry) throw new Error(`no spiral substitution for regime ${regime}`);
  return inflationFactor(entry.sub, opts);
}

// The full tower, ordered finite < scott-continuous < transfinite.
export function pisotTower(opts) {
  return ["strict-finite", "scott-continuous", "transfinite"].map((regime) => {
    const { name, constant } = REGIME_SUBSTITUTION[regime];
    return { regime, name, computed: regimeInflation(regime, opts), expected: constant };
  });
}
