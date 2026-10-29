// successor.mjs — the successor n ↦ n+1 as an increment-generator plug-in.
//
// This is the shadow-mancy of arithmetic itself: the settlement orbit of `successor` is ℕ.
// Every step reaches a genuinely new cell, so the reached-set is {0,1,…,τ} at stage τ and the
// orbit NEVER finitely quiesces — its closure ordinal is ω, placing the number line in the
// Scott-continuous regime (κ=ω). The stages ARE the ordinals; Peano's successor axiom is the
// step, and "0 is not a successor" is that the seed is the only cell with no predecessor in the
// orbit. Arithmetic is the orbit; the number line is its shadow.

import { fromEndoMap } from "#increment-sequence";

export default function successor(seed = 0) {
  return fromEndoMap(
    (v) => ({ next: v + 1n, move: "+1 (extension)", nucleusShadow: "transferring-shadow" }),
    { seed: BigInt(seed), name: `successor(${seed})` },
  );
}
