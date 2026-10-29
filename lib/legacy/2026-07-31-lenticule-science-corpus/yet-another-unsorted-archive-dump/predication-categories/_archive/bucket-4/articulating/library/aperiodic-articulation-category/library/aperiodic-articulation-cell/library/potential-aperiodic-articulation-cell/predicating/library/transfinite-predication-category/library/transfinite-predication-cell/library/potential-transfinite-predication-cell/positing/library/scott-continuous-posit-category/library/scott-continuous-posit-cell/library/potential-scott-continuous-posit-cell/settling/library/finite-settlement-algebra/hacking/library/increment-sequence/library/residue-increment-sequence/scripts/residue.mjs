// residue.mjs — a map on Z/m as an increment-generator plug-in.
//
// Modular arithmetic as a strict-finite residue-settlement: the orbit lives in the finite set
// Z/m, so it MUST close (revisit a class) within m steps — closure ordinal κ ≤ m, regime
// strict-finite. The reached cells are exactly the congruence classes the orbit touches; a
// settled fiber over Z/m. The default map is the cyclic successor v ↦ v+1 (mod m), which
// reaches all m classes then repeats (κ = m); pass a custom `map` for any endo-map on Z/m
// (e.g. the affine residue relation, of which Collatz-mod-6 is one instance).

import { fromEndoMap } from "#increment-sequence";

export default function residue(m, { map, seed = 0 } = {}) {
  const M = Number(m);
  const f = map ?? ((v) => v + 1);
  const wrap = (v) => ((Number(v) % M) + M) % M;
  return fromEndoMap(
    (v) => ({ next: wrap(f(v)), move: `↦ (mod ${M})`, nucleusShadow: "—" }),
    { seed: wrap(seed), name: `residue(Z/${M})` },
  );
}
