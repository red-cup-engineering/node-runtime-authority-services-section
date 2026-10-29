// collatz.mjs — Collatz as an increment-generator plug-in.
//
// The single point (a,b,d) = (3,1,2) of the affine family: odd n → 3n+1 (transferring-shadow,
// expansion), even n → n/2 (saturating-shadow, contraction). Re-exported from #affine so the
// reduction "Collatz is one affine" is literal, not narrative.

import affine from "#affine";

export default function collatz(seed = 1) {
  const gen = affine({ a: 3, b: 1, d: 2 }, seed);
  return { ...gen, name: `collatz(${seed})` };
}
