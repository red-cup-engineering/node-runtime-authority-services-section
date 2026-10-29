// collatz-settlement.mjs — the $thing's closure rule, now the generic harness + a plug-in.
//
// Collatz is no longer special-cased: it is `#settling-endofunctor` run on the `#collatz`
// increment-generator. The orbit is the settlement; κ (the reported closure ordinal) is the
// total stopping time and the well-founded measure; the value bounces but the knowledge order
// is monotone. This proves the $thing's morphism IS the generic machine with one plug-in.
//
// Usage:  node collatz-settlement.mjs 27

import settle, { shadowCensus } from "#settling-endofunctor";
import collatz from "#collatz";

export function collatzSettlement(seed, opts = {}) {
  return settle(collatz(seed), { mod: 6, ...opts });
}

function main() {
  const seed = process.argv.find((a) => /^\d+$/.test(a)) ?? "27";
  const r = collatzSettlement(seed);
  const census = shadowCensus(r);

  console.log(`collatz-settlement  seed = ${seed}`);
  console.log(`  closure ordinal κ (total stopping time) = ${r.kappa}   [${r.regime.regime}, ${r.regime.band}]`);
  console.log(`  distinct cells reached (|v_κ|)           = ${r.reachedSize}`);
  console.log(`  value bounced (¬monotone) while knowledge order grew monotonically: ${r.valueBounced}`);
  console.log("");
  console.log("  stage  integer    move               nucleus-shadow        n mod 6   new cell");
  console.log("  -----  ---------  -----------------  --------------------  -------  --------");
  for (const o of r.orbit) {
    console.log(
      "  " + String(o.stage).padStart(5) + "  " + String(o.value).padStart(9) + "  " +
      o.move.padEnd(17) + "  " + o.nucleusShadow.padEnd(20) + "  " +
      String(o.residue).padStart(5) + "  " + (o.newCell ? "  yes" : "  no"));
  }
  console.log("");
  console.log(`  step census: transferring-shadow (odd, 3n+1) = ${census["transferring-shadow"]}, ` +
              `saturating-shadow (even, n/2) = ${census["saturating-shadow"]}`);
  console.log(`  (the final no-new-cell step is the entry into the 1→4→2→1 quiescent cycle.)`);
}

if (import.meta.url === `file://${process.argv[1]}`) main();
