// settling-endofunctor.mjs — the generic morphism F_U, made runnable.
//
// F_U(v)_τ = cl(v_τ) ∨_k u_τ.  The state v is the ≤_k-monotone set of REACHED entity
// keys; the increment u_τ is the next entity emitted by a plugged-in generator. The orbit
// is the settlement. The least stage with no new cell is the closure ordinal κ; κ<ω ⟺ the
// orbit closed (strict-finite), κ=ω ⟺ it kept producing new cells to the bound.
//
// This is the one machine. Collatz, affine maps, successor, modular arithmetic are all just
// increment-generators (see #increment-sequence and the family plug-ins). The integer VALUE
// may bounce; the knowledge order (reached-set) only grows — that monotonicity is the
// well-founded measure arithmetic cannot see.
//
// An increment-generator is: { name, seed, key(v)→string, step(v)→{next, move, nucleusShadow} }

import { classify } from "#closure-ordinal";

function residueOf(v, mod) {
  if (mod == null) return null;
  if (typeof v === "bigint") { const m = BigInt(mod); return Number(((v % m) + m) % m); }
  const m = Number(mod); return ((Number(v) % m) + m) % m;
}

export default function settle(increment, { bound = 100000, mod = null } = {}) {
  const { name, seed, key, step } = increment;
  const reached = new Set([key(seed)]);
  const orbit = [{ stage: 0, value: seed, key: key(seed), move: "seed", nucleusShadow: "—", residue: residueOf(seed, mod), newCell: true }];
  let v = seed, stage = 0, lastNewStage = 0, converged = false;

  while (stage < bound) {
    const { next, move, nucleusShadow } = step(v);
    stage += 1;
    const k = key(next);
    const newCell = !reached.has(k);
    if (newCell) { reached.add(k); lastNewStage = stage; }
    orbit.push({ stage, value: next, key: k, move, nucleusShadow, residue: residueOf(next, mod), newCell });
    v = next;
    if (!newCell) { converged = true; break; } // the orbit closed a loop — quiescence reached
  }

  const kappa = lastNewStage;
  const stillGrowing = !converged && orbit[orbit.length - 1].newCell;
  const regime = classify(kappa, { converged, stillGrowing, bound });

  // value non-monotonicity witness (the knowledge order is monotone by construction)
  const numeric = orbit.map((o) => (typeof o.value === "bigint" ? o.value : BigInt(Math.trunc(Number(o.value)))));
  const valueBounced = numeric.some((x) => x > numeric[0]) && numeric.some((x) => x < numeric[0]);

  return { name, seed, kappa, regime, converged, reachedSize: reached.size, valueBounced, orbit };
}

// Census of nucleus-shadow tags over the orbit (steps only, excluding the seed).
export function shadowCensus(result) {
  const c = { "transferring-shadow": 0, "saturating-shadow": 0 };
  for (const o of result.orbit.slice(1)) if (o.nucleusShadow in c) c[o.nucleusShadow]++;
  return c;
}
