import assert from "node:assert/strict";
import test from "node:test";

import {
  EMPTY_WITNESS_ROOT,
} from "@red-cup-engineering/computer-content-engineering-services-section/semantic-content-identity";
import {
  identifyNormalizedSemanticContent,
  verifyNormalizedSemanticContent,
} from "@red-cup-engineering/computer-code-engineering-services-section/semiotic-expression-notation/runtime";
import {
  inferSemioticResourceNameType,
  readSemioticResourceName,
  renderSemioticResourceName,
} from "../../src/semiotic-resource-name/derivation.mjs";

test("one SRN path derives one typed claim and one independently verifiable opaque token", () => {
  const surface = "order.payment:receipt-delay";
  const term = readSemioticResourceName(surface);
  const semanticType = inferSemioticResourceNameType(term);

  const addressed = identifyNormalizedSemanticContent({
    objectKind: "semiotic-resource-name.path-claim",
    semanticType,
    term,
    witnessRoot: EMPTY_WITNESS_ROOT,
  });

  assert.equal(renderSemioticResourceName(addressed.envelope.settledBody), surface);
  assert.equal(verifyNormalizedSemanticContent(addressed.token, addressed.envelope), true);
});
