// shape-statistics.mjs — the cream of the old `predictions.py`: the shortcut-shape statistic
// whose depth-binned growth rate is the settling's Pisot inflation.
//
// Kept ONLY the parts that measure the inflation rate (the cream); the Ω-binned count that
// merely reproduced the Fibonacci failure is dropped. The depth-binned distinct-shape count is
// the substitution word-growth, whose dominant ratio is the regime spiral — for finite Collatz,
// the plastic number ρ (see ../docs/dev/theorems/collatz-padovan-shape-law.md).

import { PLASTIC, GOLDEN } from "#settlement-spiral";

export function v2(n) {
  if (n === 0) return Infinity;
  let c = 0;
  while (n % 2 === 0) { c++; n = Math.floor(n / 2); }
  return c;
}

// The shortcut shape: v2(3m+1) at each odd m in the trajectory of n.
export function collatzShortcutShape(n) {
  const shape = [];
  let cur = n;
  const seen = new Set();
  while (cur !== 1) {
    if (seen.has(cur)) return null;
    seen.add(cur);
    if (cur % 2 === 0) cur = cur / 2;
    else { const val = 3 * cur + 1, vv = v2(val); shape.push(vv); cur = val / 2 ** vv; }
  }
  return shape;
}

// Distinct shapes binned by trajectory depth ℓ (#odd steps): the substitution word-growth.
export function shapeCountsByDepth(limit) {
  const byLen = new Map();
  for (let n = 3; n <= limit; n += 2) {
    const s = collatzShortcutShape(n);
    if (s === null) continue;
    const L = s.length;
    if (!byLen.has(L)) byLen.set(L, new Set());
    byLen.get(L).add(s.join(","));
  }
  const maxL = Math.max(...byLen.keys());
  const c = [];
  for (let L = 1; L <= maxL; L++) c[L] = byLen.get(L)?.size ?? 0;
  return c;
}

// Median of the dominant (up-)ratios over a stable window — strips the parity-2 oscillation.
export function depthGrowthVerdict(c, lo = 25, hi = 70) {
  const up = [];
  for (let L = Math.max(2, lo); L <= Math.min(hi, c.length - 1); L++)
    if (c[L - 1] > 0) { const r = c[L] / c[L - 1]; if (r > 1) up.push(r); }
  up.sort((a, b) => a - b);
  const median = up.length ? up[Math.floor(up.length / 2)] : NaN;
  return {
    sampleSize: up.length,
    medianUpRatio: median,
    distToPlastic: Math.abs(median - PLASTIC),
    distToGolden: Math.abs(median - GOLDEN),
    closerTo: Math.abs(median - PLASTIC) < Math.abs(median - GOLDEN) ? "plastic" : "golden",
  };
}
