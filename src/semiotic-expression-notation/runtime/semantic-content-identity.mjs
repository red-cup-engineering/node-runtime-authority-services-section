/**
 * Normalized semantic content identity: the content address of an arbitrary typed SEN
 * term, taken after the SEN evaluator normalizes it. The envelope law and JSON content
 * identity are the data layer's (`@red-cup-engineering/computer-content-address-engineering-services-section/semantic-content-identity`);
 * this module adds only what needs evaluation — normalizing a term and checking a body is
 * already normal under `SEN_NORMALIZATION_PROFILE`.
 */
import {
  commitSemanticEnvelope,
  decodeSemanticEnvelope,
  inhabitsDeclaredType,
  semanticContentRefusal as refusal,
  IDENTITY_SETTLEMENT_PROFILE,
  SEMANTIC_ENVELOPE_KIND,
  SEMANTIC_ENVELOPE_VERSION,
  SEN_NORMALIZATION_PROFILE,
} from "@red-cup-engineering/computer-content-address-engineering-services-section/semantic-content-identity";
import { evaluate } from "../runtime.mjs";

/** The normal form of a term under `SEN_NORMALIZATION_PROFILE`. */
const normalForm = (term) => evaluate(term, 10_000).normalForm;

/** Normalize one explicitly typed SEN term and bind its identity settlement witness. */
export function identifyNormalizedSemanticContent({
  objectKind,
  semanticType,
  term,
  witnessRoot,
  normalizationProfile = SEN_NORMALIZATION_PROFILE,
  settlementProfile = IDENTITY_SETTLEMENT_PROFILE,
} = {}) {
  if (normalizationProfile !== SEN_NORMALIZATION_PROFILE) {
    throw refusal("unsupported-normalization-profile", `unsupported normalization profile ${String(normalizationProfile)}`);
  }
  if (settlementProfile !== IDENTITY_SETTLEMENT_PROFILE) {
    throw refusal("unsupported-settlement-profile", `identifyNormalizedSemanticContent requires ${IDENTITY_SETTLEMENT_PROFILE}`);
  }
  if (!inhabitsDeclaredType(term, semanticType)) throw refusal("non-relational-content", "term must be a closed SEN term inhabiting semanticType");
  let settledBody;
  try {
    settledBody = normalForm(term);
  } catch {
    throw refusal("normalization-failure", "term could not be normalized under the declared normalization profile");
  }
  if (!inhabitsDeclaredType(settledBody, semanticType)) {
    throw refusal("normalization-type-mismatch", "normalized term no longer inhabits its admitted semanticType");
  }
  return commitSemanticEnvelope({
    kind: SEMANTIC_ENVELOPE_KIND,
    version: SEMANTIC_ENVELOPE_VERSION,
    objectKind,
    semanticType,
    normalizationProfile,
    settlementProfile,
    settledBody,
    witnessRoot,
  }, { typeChecked: true });
}

/** Admit canonical v2 bytes and reproduce their typed normalized commitment. */
export function admitNormalizedSemanticContent(bytes, token = undefined) {
  return decodeSemanticEnvelope(bytes, token, { normalForm });
}

/** Verify a visible v2 envelope against its opaque token. */
export function verifyNormalizedSemanticContent(token, envelope) {
  try {
    return typeof token === "string" && commitSemanticEnvelope(envelope, { normalForm }).token === token;
  } catch {
    return false;
  }
}
