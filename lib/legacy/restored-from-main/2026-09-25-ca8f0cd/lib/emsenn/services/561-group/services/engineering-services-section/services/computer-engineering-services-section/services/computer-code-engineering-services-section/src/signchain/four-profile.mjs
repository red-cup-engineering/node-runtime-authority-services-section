import { mark } from "@red-cup-engineering/computer-data-engineering-services-section/signcell/utterance";
import { bottom, joinKnowledge, negate, valueOf, witnessedPotential } from "@lenticule-science/metrologic/articulation/predicating/positing/bilattice-charge";
import { fourScalarTwist } from "@lenticule-science/metrologic/articulation/predicating/positing/four-scalar-twist";

const evidenceValues = (marks) => Object.freeze(marks.map((witness) => witness.value));
export { fourScalarTwist };

/** FOUR evidence profile over SignCell marks; graph settlement remains in SignGraph. */
export function createFourProfile({ positiveDatums = ["for"], negativeDatums = ["against"] } = {}) {
  const positive = new Set(positiveDatums), negative = new Set(negativeDatums);
  return Object.freeze({
    name: "pam-finite-four", scalarTwist: fourScalarTwist, bottom: () => bottom,
    contribute(observation, witness) {
      const polarity = observation.polarity ?? observation.datum ?? "for", contribution = witnessedPotential(mark(witness));
      if (positive.has(polarity)) return contribution;
      if (negative.has(polarity)) return negate(contribution);
      throw new TypeError(`FOUR profile has no polarity mapping for ${JSON.stringify(polarity)}`);
    },
    join: joinKnowledge, reading: (carrier) => valueOf(carrier).name,
    witness(carrier) { return Object.freeze({ profile: "pam-finite-four", value: carrier, reading: valueOf(carrier).name, evidence: Object.freeze({ for: evidenceValues(carrier.evidence[0]), against: evidenceValues(carrier.evidence[1]) }) }); },
  });
}
export const fourProfile = createFourProfile();
