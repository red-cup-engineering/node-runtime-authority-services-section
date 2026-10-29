// q-relevance: the quantale Q in which memory relevance lives   [the machinery the weighting hacked]
//
// Memory relevance is a graded PRESENCE strength ("how present is this entity to the agent now?"),
// a dimension ORTHOGONAL to the claim's truth (which stays a charge, in positing/settling). The harness's
// `sense > remembered-sense > learning` tier-order was a hack approximating exactly this grading; the
// proper machinery is a value in a quantale Q (docs/GENEALOGY.md §6). This makes relevance Q-enriched,
// which is what the Laplacian/MLD already wants (spotcomp/MODULI-DESCENT-LAPLACIAN.md: Q-enriched
// cellular sheaves) -- so memory-relevance and consensus/dissent (H1) share one enrichment.
//
// CHOSEN Q (a placement decision; honest hacking/): the unit-interval PRODUCT quantale
//   carrier [0,1], order <=, join = max (sup), meet = min, tensor (x) = product, unit 1, bottom 0.
// Commutative, unital, sups distribute over (x) -- a quantale. Decay is tensoring by a factor f<1;
// persistence is f=1 (sense never decays); promotion is join with a high value; dismissal is meet 0.

const clamp = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
export const Q = { bottom: 0, unit: 1 };

export const qJoin = (a, b) => Math.max(toQ(a), toQ(b));   // sup: strongest presence wins
export const qMeet = (a, b) => Math.min(toQ(a), toQ(b));   // inf
export const qTensor = (a, b) => clamp(toQ(a) * toQ(b));   // monoidal product, unit 1
export const qDecay = (a, factor = 0.7) => clamp(toQ(a) * clamp(factor)); // tensor by a decay factor
export const qLeq = (a, b) => toQ(a) <= toQ(b);

// Provenance bridge -- RETIRES the `sense > remembered-sense > learning` hack as graded Q values
// with per-tier decay factors (sense persists; learning decays). Returns {value, decay}.
const PROVENANCE = {
  sense: { value: 1.0, decay: 1.0 },              // persists -- no decay
  "remembered-sense": { value: 0.8, decay: 0.95 },
  learning: { value: 0.5, decay: 0.7 }            // decays fast, yields to sense
};
export const qFromProvenance = (tier) => PROVENANCE[tier] ?? PROVENANCE.learning;

// value-corner -> Q bridge. COINCIDENCE on the PRESENCE reading (docs/GENEALOGY.md §6): the relevance
// dimension cares only about presence-strength, so bottom (no evidence) -> 0 and any held corner
// (true/false/top) -> present (1). Lossy off the presence reading; that is the declared off-scope.
export const qFromCorner = (v) => (v === "bottom" || v == null ? 0 : v === "top" ? 1 : v === "false" ? 1 : 1);

// Accept either a number already in Q, or a value corner string (backward compatibility).
export function toQ(v) {
  if (typeof v === "number") return clamp(v);
  if (typeof v === "string") return qFromCorner(v);
  return 0;
}

export default { Q, qJoin, qMeet, qTensor, qDecay, qLeq, qFromProvenance, qFromCorner, toQ };
