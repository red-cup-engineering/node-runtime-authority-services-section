import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { decodeCanonical, encodeCanonical } from "@red-cup-engineering/cbor-services-section";
import { conformAscribedTerm } from "../../src/semiotic-expression-notation/runtime/conformance.mjs";
import {
  assay,
  assayEffectTransition,
  effectTerm,
  normalizeEffectCell,
  parseRml,
} from "../../src/semiotic-expression-notation/runtime.mjs";
import {
  inferTerm,
  validateType,
} from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation/typing";
import { decodeSemantic, semanticBytes, semanticId } from "@red-cup-engineering/computer-content-address-engineering-services-section/semiotic-content-address";
import { SEN_FORMS, TySchema, tm } from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation";
import { FOUR, isKnowledgeCover } from "@red-cup-engineering/computer-data-engineering-services-section/four";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");



test("an effect cell carries only witnessed fields and refuses stored law", () => {
  const cell = {
    caller: "eip155:1:0x0000000000000000000000000000000000000001",
    provider: "eip155:1:0x0000000000000000000000000000000000000002",
    outcome: { positiveEvidence: true, negativeEvidence: false },
    measures: [],
    evidenceRoot: semanticId(["star"]),
    parent: null,
  };
  const normalized = normalizeEffectCell(cell);
  assert.deepEqual(Object.keys(normalized).sort(), ["caller", "evidenceRoot", "measures", "outcome", "parent", "provider"]);
  assert.throws(() => normalizeEffectCell({ ...cell, law: cell.evidenceRoot }), /must expose exactly/u);
  assert.throws(() => normalizeEffectCell({ ...cell, precondition: cell.evidenceRoot }), /must expose exactly/u);
});

test("effect-bundle conformance derives operation identity from the bundled term", () => {
  const operation = ["mark", "perform the bounded operation"];
  const cell = {
    caller: "eip155:1:0x0000000000000000000000000000000000000001",
    provider: "eip155:1:0x0000000000000000000000000000000000000002",
    outcome: { positiveEvidence: false, negativeEvidence: false },
    measures: [],
    evidenceRoot: semanticId(["mark", "no evidence yet"]),
    parent: null,
  };
  const bundle = ["pair", effectTerm(cell), operation];
  const result = conformAscribedTerm(["ascribe", inferTerm(bundle), bundle]);
  assert.equal(result.kind, "effect-bundle");
  assert.equal(result.operation, semanticId(operation));
  assert.deepEqual(result.effectCell, cell);
  assert.throws(() => effectTerm({ ...cell, operation: semanticId(operation) }), /must expose exactly/u);
});

test("obsolete product type spelling is refused", () => {
  assert.throws(() => validateType(["product", ["effect"], ["base"]]), /unknown or malformed SEN type/u);
});

test("RFC 8949 and RFC 6920 identities match the released vectors", () => {
  const values = new Map([
    ["star", ["star"]],
    ["four-neither", ["four", false, false]],
    ["mark-nfc-e-acute", ["mark", "é"]],
    ["identity-rml", ["app", ["lam", ["var", 0]], ["star"]]],
  ]);
  const vectors = readFileSync(join(ROOT, "content/vectors/sen-core-v2.tsv"), "utf8")
    .split("\n")
    .filter((line) => line && !line.startsWith("#"));
  for (const line of vectors) {
    const [name, hex, ni] = line.split("\t");
    assert.equal(encodeCanonical(values.get(name)).toString("hex"), hex);
    assert.equal(semanticId(values.get(name)), ni);
  }
  assert.throws(() => decodeCanonical(Buffer.from([0x18, 0x00])), /not in RFC 8949 core deterministic form/u);
});


test("bounded normalization and FOUR knowledge covers remain exact", () => {
  const term = parseRml("#lang sen/v2\n(app (lam (var 0)) (star))");
  assert.deepEqual(assay({ term, expectedType: ["unit"], fuel: 4 }).normalForm, ["star"]);
  assert.deepEqual(
    conformAscribedTerm(["ascribe", ["unit"], ["app", ["lam", ["var", 0]], ["star"]]]).response,
    ["ascribe", ["unit"], ["star"]],
  );
  assert.equal(isKnowledgeCover(FOUR.neither, FOUR.true), true);
  assert.equal(isKnowledgeCover(FOUR.true, FOUR.both), true);
});

test("a WIT is one FOUR cover between two cells of one effect, carried as core charge marks", () => {
  const cell = (positiveEvidence, evidenceRoot) => ({
    caller: "eip155:1:0x0000000000000000000000000000000000000001",
    provider: "eip155:1:0x0000000000000000000000000000000000000002",
    outcome: { positiveEvidence, negativeEvidence: false },
    measures: [],
    evidenceRoot,
    parent: null,
  });
  const evidence = semanticId(["mark", "evidence"]);
  const wit = assayEffectTransition({ proposalCell: cell(false, semanticId(["mark", "none"])), completionCell: cell(true, evidence), evidence });
  assert.deepEqual(wit.witnessTerm[2][1], tm.reading("unknown"));
  assert.deepEqual(wit.witnessTerm[2][2][1], tm.reading("held"));
  assert.equal(wit.witness, semanticId(wit.witnessTerm));
  assert.throws(() => assayEffectTransition({ proposalCell: cell(false, evidence), completionCell: { ...cell(true, evidence), outcome: { positiveEvidence: true, negativeEvidence: true } }, evidence }), /WIT/u);
});
