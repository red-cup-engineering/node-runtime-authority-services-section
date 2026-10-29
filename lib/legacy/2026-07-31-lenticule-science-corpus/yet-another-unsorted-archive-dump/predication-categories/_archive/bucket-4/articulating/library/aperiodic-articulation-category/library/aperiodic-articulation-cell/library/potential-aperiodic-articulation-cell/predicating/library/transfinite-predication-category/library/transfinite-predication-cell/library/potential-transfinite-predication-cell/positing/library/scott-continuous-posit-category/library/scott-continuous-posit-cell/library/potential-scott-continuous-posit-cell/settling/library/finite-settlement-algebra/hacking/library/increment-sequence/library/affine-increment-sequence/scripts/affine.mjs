// affine.mjs — the Collatz-like affine family as an increment-generator plug-in.
//
// (a,b,d): even n → n/d  [saturating-shadow, contraction];  odd n → a·n+b  [transferring-shadow,
// expansion]. Standard Collatz is the single point (a,b,d) = (3,1,2). This is the literal sense
// in which "affines are just a part of" the harness — one parameterized increment-generator.

import { parityBranched } from "#increment-sequence";

export default function affine({ a = 3, b = 1, d = 2 } = {}, seed = 1) {
  const A = BigInt(a), B = BigInt(b), D = BigInt(d);
  return parityBranched({
    name: `affine(a=${a},b=${b},d=${d}; seed=${seed})`,
    seed: BigInt(seed),
    expand: (v) => A * v + B,
    contract: (v) => v / D,
    expandLabel: `${a}n+${b} (expansion)`,
    contractLabel: `n/${d} (contraction)`,
  });
}
