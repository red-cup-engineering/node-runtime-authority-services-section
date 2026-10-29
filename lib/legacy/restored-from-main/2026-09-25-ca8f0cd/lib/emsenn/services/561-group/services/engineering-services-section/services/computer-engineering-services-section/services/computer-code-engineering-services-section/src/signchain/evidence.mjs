/**
 * signchain/evidence - FOUR evidence as its wire record { positiveEvidence,
 * negativeEvidence }: construction and validation, the knowledge join and
 * order, knowledge covers, and the witness bit a cover sets.
 */
import {
  charge,
  chargeSide,
  chargeValueAt,
  chargeValues,
  chargeTwist,
  leqKnowledge,
  present,
  sameCharge,
} from "@lenticule-science/metrologic/articulation/predicating/positing/bilattice-charge";

function fail(code, message) { const error = new Error(message); error.code = code; throw error; }

// ── the FOUR evidence wire: a REPRESENTATION BINDING, not a second bilattice ────────────────────
//
// `{ positiveEvidence: bool, negativeEvidence: bool }` is the normative decoded form of FOUR evidence
// that circuits (profile org.emsenn.sen.hierarchical-circuit.v3) and effect cells carry
// positiveEvidence: bool, negativeEvidence: bool }`). It exists because circuits are content-addressed
// — `semanticId` over the canonical bytes yields the `ni:///sha-256;…` a circuit IS — so these two map
// keys are part of already-issued identities on the wire, not a naming preference. That is the whole
// reason this shape survives.
//
// NO ALGEBRA LIVES HERE. Every order, join, covering and witness below is
// `@lenticule-science/metrologic`'s Charge — the single implementation of Obsmetrologia's Charge/FOUR,
// which self-verifies its bilattice laws and ties its Klein-four gauge to the Lean theorem
// `RelMath.KleinFour.K4.isGroup`. Each wire record is decoded to that charge, the charge answers, and
// only the ANSWER is encoded back. Nothing about the four values is re-derived on the wire record.

const fourCoordinates = (value) => [
  chargeSide(value.positiveEvidence ? "present" : "absent"),
  chargeSide(value.negativeEvidence ? "present" : "absent"),
];
const fourWire = (value) => four(value[0].name === "present", value[1].name === "present");
const fourCarrier = (value) => charge(chargeValueAt(fourCoordinates(validateFour(value))));

const FOUR_KEYS = ["negativeEvidence", "positiveEvidence"];

function fourExactKeys(value, keys) {
  return value && Object.getPrototypeOf(value) === Object.prototype
    && Object.keys(value).sort().join(" ") === [...keys].sort().join(" ");
}

export function four(positiveEvidence, negativeEvidence) {
  if (typeof positiveEvidence !== "boolean" || typeof negativeEvidence !== "boolean") {
    fail("malformed-four", "FOUR requires explicit Boolean positiveEvidence and negativeEvidence bits");
  }
  return Object.freeze({ positiveEvidence, negativeEvidence });
}

export function validateFour(value) {
  if (!fourExactKeys(value, FOUR_KEYS)) fail("malformed-four", "FOUR must expose exactly positiveEvidence and negativeEvidence");
  return four(value.positiveEvidence, value.negativeEvidence);
}

export function joinKnowledgeWire(left, right) {
  return fourWire(chargeTwist.joinKnowledge({
    left: fourCoordinates(validateFour(left)), right: fourCoordinates(validateFour(right)),
  }));
}

export function knowledgeLeq(left, right) {
  return leqKnowledge(fourCarrier(left), fourCarrier(right));
}

/** A WIT is a COVERING pair in the charge's knowledge order — nothing lies strictly between. Read as
 *  the order-theoretic covering over the charge's own four values, so the relation is the charge's and
 *  not a bit rule restated on the wire record. */
export function isKnowledgeCover(before, after) {
  const a = fourCarrier(before), b = fourCarrier(after);
  if (!leqKnowledge(a, b) || sameCharge(a, b)) return false;
  return !chargeValues.some((value) => {
    const between = charge(value);
    return leqKnowledge(a, between) && leqKnowledge(between, b)
      && !sameCharge(between, a) && !sameCharge(between, b);
  });
}

/** Which wire key the covering step witnesses — the one question that IS about this representation. */
export function witnessBit(before, after) {
  if (!isKnowledgeCover(before, after)) fail("not-one-wit", "a WIT must be exactly one 0→1 cover transition in the FOUR knowledge order");
  return present(fourCarrier(before))[0].name === present(fourCarrier(after))[0].name
    ? "negativeEvidence"
    : "positiveEvidence";
}

export const FOUR = Object.freeze({
  neither: fourWire(chargeTwist.knowledgeBottom),
  true: fourWire(chargeTwist.truthTop),
  false: fourWire(chargeTwist.truthBottom),
  both: fourWire(chargeTwist.knowledgeTop),
});
