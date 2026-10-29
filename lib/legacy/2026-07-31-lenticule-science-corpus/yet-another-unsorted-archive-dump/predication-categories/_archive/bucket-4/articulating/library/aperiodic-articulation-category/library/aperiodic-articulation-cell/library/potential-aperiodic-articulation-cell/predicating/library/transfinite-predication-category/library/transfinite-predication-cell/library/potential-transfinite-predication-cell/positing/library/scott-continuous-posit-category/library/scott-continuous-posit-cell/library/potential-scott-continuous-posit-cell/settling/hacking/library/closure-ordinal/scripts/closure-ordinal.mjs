// closure-ordinal.mjs — the regime classifier, made runnable.
//
// κ is the least stage at which a settling stops acquiring new cells. Its ordinal BAND is
// the regime (the four-regime tower is the four bands of closure ordinals):
//   κ < ω    strict-finite        (orbit closed in finitely many steps)
//   κ = ω    scott-continuous     (kept adding new cells; ω-limit, no finite closure)
//   ω<κ<ω₁   transfinite-bounded  (not finitely decidable here)
//   κ ≥ ω₁   aperiodic            (needs the outside; not finitely decidable here)
//
// A finite computation can only WITNESS the first two. We report what we can decide and stay
// honest about the rest.

export function classify(kappa, { converged, stillGrowing, bound }) {
  if (converged) return { regime: "strict-finite", band: "κ<ω", kappa, decided: true };
  if (stillGrowing) return { regime: "scott-continuous", band: "κ=ω", kappa: "ω", witnessedTo: bound, decided: true };
  return { regime: "undecided", band: "ω≤κ", kappa: "≥" + bound, decided: false };
}

export const isFinite = (regime) => regime.regime === "strict-finite";
