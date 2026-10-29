/**
 * SignChain — the evidence bilattice over SignCell's cells.
 *
 * A cell's evidence is a pair (F, A): the witnesses told for it and against
 * it. Pairs of witness sets under two orders form the product bilattice
 * P(W) ⊙ P(W) (Ginsberg 1988; Arieli & Avron 1996):
 *
 *   knowledge  (F, A) ≤k (F', A')  iff  F ⊆ F' and A ⊆ A'   — how much is told
 *   truth      (F, A) ≤t (F', A')  iff  F ⊆ F' and A ⊇ A'   — which way it leans
 *
 * with negation swapping the sides. Read through "is the side non-empty?", a
 * cell's evidence lands on one of four points, named per reading (metrologic's
 * FOUR: knowledge, told, truth, extremal), whose orders and operations on the
 * points are metrologic's; here the witness sets themselves are ordered and
 * combined.
 *
 * "Non-empty" preserves unions but not intersections, so the reading commutes
 * with negation and with every operation whose sides are unions; where a side
 * is an intersection, the reading of the result can fall below the reading of
 * the operands ({u} ∩ {v} is empty though both were told). Two tellings that
 * share no witness meet to less than their readings meet — computed from the
 * sets, not stored as a separate value.
 *
 * The value is the evidence: no value is stored beside it.
 */
import { cell, cellSet, evidence, evidenced, hasTriple, sameCell, told } from "@red-cup-engineering/computer-data-engineering-services-section/signcell/cell";
import { knowledgeJoinAll, samePoint, sidesOfReading } from "@red-cup-engineering/computer-data-engineering-services-section/four";
import { semanticBytes } from "@red-cup-engineering/computer-content-engineering-services-section/semiotic-content-address";

// — the bilattice on cells: operations on evidence sets —

const key = (witness) => semanticBytes(witness).toString("hex");
const union = (left, right) => [...left, ...right];
const intersection = (left, right) => { const keep = new Set(right.map(key)); return left.filter((w) => keep.has(key(w))); };
const includes = (small, large) => { const has = new Set(large.map(key)); return small.every((w) => has.has(key(w))); };

const sameShape = (left, right) => {
  if (hasTriple(left) !== hasTriple(right)) throw new TypeError("signchain: a cell combines only with a cell, a bare evidence pair only with a pair");
  if (hasTriple(left) && !sameCell(left, right)) throw new TypeError("signchain: evidence of different cells does not combine");
};

/** Rebuild `like` (a cell or a bare pair) with new sides. */
const shaped = (like, sides) => hasTriple(like) ? cell(like.subject, like.predicate, like.object, sides) : evidence(sides);

const combined = (left, right, forSide, againstSide) => {
  sameShape(left, right);
  return shaped(left, { for: forSide(left.for, right.for), against: againstSide(left.against, right.against) });
};

/** Knowledge join: everything either telling told (on cells, SignCell's merge). */
export const knowledgeJoin = (left, right) => combined(left, right, union, union);
/** Knowledge meet: only what both tellings told. */
export const knowledgeMeet = (left, right) => combined(left, right, intersection, intersection);
/** Truth join: for-witnesses of either, against-witnesses of both. */
export const truthJoin = (left, right) => combined(left, right, union, intersection);
/** Truth meet: for-witnesses of both, against-witnesses of either. */
export const truthMeet = (left, right) => combined(left, right, intersection, union);

/** Negation: the same cell (or bare pair) with its sides swapped — told for becomes told against. It is
 *  antitone in truth, monotone in knowledge, and involutive; it is also the linear negation (the residuum
 *  into the multiplicative unit told-both). */
export const negate = (value) => shaped(value, { for: value.against, against: value.for });

/** Whether `left` is told no more than `right`, side by side. */
/** A list of cells with each cell told more than once folded into one by a lattice operation on its
 *  evidence (knowledgeJoin, the default, keeps every telling; knowledgeMeet what every telling shares;
 *  truthJoin and truthMeet the truth order's). */
export const foldCells = (cells, operation = knowledgeJoin) => cellSet(cells, (left, right) => evidenced(left, operation(left, right)));

export function knowledgeLeq(left, right) {
  sameShape(left, right);
  return includes(left.for, right.for) && includes(left.against, right.against);
}

/** Whether `left` leans no more true than `right`. */
export function truthLeq(left, right) {
  sameShape(left, right);
  return includes(left.for, right.for) && includes(right.against, left.against);
}

/** The evidence that tells a reading's sides, each told side witnessed by `witness` — the least evidence
 *  a single witness can give that reads as `name` (knowledgeReading inverts it). */
export function witnessedReading(name, witness) {
  const [forTold, againstTold] = sidesOfReading(name);
  return evidence({ for: forTold ? [witness] : [], against: againstTold ? [witness] : [] });
}

/** Bare evidence pairs: nothing told, one witness for, one witness against. */
export const noEvidence = evidence();
export const witnessedFor = (witness) => evidence({ for: [witness] });
export const witnessedAgainst = (witness) => evidence({ against: [witness] });

/** The JSON Schema of a bare evidence pair. */
export const evidenceSchema = Object.freeze({
  $schema: "https://json-schema.org/draft/2020-12/schema",
  $id: "https://schemas.561.group/signchain/evidence.schema.json",
  title: "Evidence", description: "The witnesses told for and against, each side a set.",
  type: "object", required: ["for", "against"],
  properties: { for: { type: "array", uniqueItems: true }, against: { type: "array", uniqueItems: true } },
  additionalProperties: false,
});

/** Settle named judgments ({ value: reading, ... }) at their knowledge join, keeping every judgment and
 *  separately the ones that are themselves told both ways (a held contradiction is retained, not folded). */
export function settleJudgments(judgments) {
  const records = Object.freeze([...judgments]);
  return Object.freeze({
    kind: "signchain.judgment-settlement",
    value: knowledgeJoinAll(records.map((judgment) => judgment.value)),
    judgments: records,
    stableJudgments: Object.freeze(records.filter((judgment) => samePoint(judgment.value, "stable"))),
  });
}

