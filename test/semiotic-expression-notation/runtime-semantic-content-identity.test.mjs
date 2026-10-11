import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  admitJsonSemanticContent,
  EMPTY_WITNESS_ROOT,
  identifyJsonSemanticContent,
  identifyBytesSemanticContent,
  IDENTITY_SETTLEMENT_PROFILE,
  SEN_NORMALIZATION_PROFILE,
  verifyJsonSemanticRecord,
} from "@red-cup-engineering/computer-content-engineering-services-section/semantic-content-identity";
import {
  admitNormalizedSemanticContent,
  identifyNormalizedSemanticContent,
  verifyNormalizedSemanticContent,
} from "../../src/semiotic-expression-notation/runtime/semantic-content-identity.mjs";

const witnessA = "ni:///sha-256;U3uKJJT0vR4Qw4-gzCLa9apzf5Y3QXY-dXiIFV5IPA4";
const witnessB = "ni:///sha-256;As10nkr7yVtaiUQ44SzVlS20Iy8ucJi2qwvP4OJ9X_8";
const BASE = Object.freeze(["base"]);
const mark = (value) => ["mark", value];
const pair = (left, right) => ["pair", left, right];
const fst = (value) => ["fst", value];

test("JSON semantic records verify their visible body identity without throwing", () => {
  const options = { objectKind: "example.semantic-record", witnessRoot: witnessA };
  const body = { category: "example", count: 2 };
  const id = identifyJsonSemanticContent({ ...options, value: body }).id;

  assert.equal(verifyJsonSemanticRecord({ ...options, value: { id, ...body } }), true);
  assert.equal(verifyJsonSemanticRecord({ ...options, value: { id: `${id}tampered`, ...body } }), false);
  assert.equal(verifyJsonSemanticRecord({ ...options, value: body }), false);
  assert.equal(verifyJsonSemanticRecord({ ...options, value: null }), false);
  assert.equal(verifyJsonSemanticRecord({ ...options, value: [] }), false);

  const nullPrototype = Object.assign(Object.create(null), { id, ...body });
  assert.equal(verifyJsonSemanticRecord({ ...options, value: nullPrototype }), true);

  class SemanticRecord {
    constructor(recordId) {
      this.id = recordId;
      this.category = body.category;
      this.count = body.count;
    }
  }
  assert.equal(verifyJsonSemanticRecord({ ...options, value: new SemanticRecord(id) }), true);

  const inheritedIdentity = Object.assign(Object.create({ id }), body);
  assert.equal(verifyJsonSemanticRecord({ ...options, value: inheritedIdentity }), true);
  const inheritedTamperedIdentity = Object.assign(Object.create({ id: `${id}tampered` }), body);
  assert.equal(verifyJsonSemanticRecord({ ...options, value: inheritedTamperedIdentity }), false);

  const digest = identifyJsonSemanticContent({ ...options, value: body }).id;
  assert.equal(verifyJsonSemanticRecord({ ...options, identityField: "digest", value: { digest, ...body } }), true);
  assert.equal(verifyJsonSemanticRecord({ ...options, value: { id, bad: undefined } }), false);
});

test("normalization converges a redex and its normal form under the exact profile", () => {
  const common = {
    objectKind: "example.normalized-mark",
    semanticType: BASE,
    witnessRoot: witnessA,
  };
  const redex = identifyNormalizedSemanticContent({
    ...common,
    term: fst(pair(mark("left"), mark("right"))),
  });
  const normal = identifyNormalizedSemanticContent({ ...common, term: mark("left") });

  assert.equal(redex.token, normal.token);
  assert.deepEqual(redex.envelope.settledBody, mark("left"));
  assert.equal(redex.envelope.normalizationProfile, SEN_NORMALIZATION_PROFILE);
  assert.equal(redex.envelope.settlementProfile, IDENTITY_SETTLEMENT_PROFILE);
  assert.equal(verifyNormalizedSemanticContent(redex.token, redex.envelope), true);
  assert.deepEqual(admitNormalizedSemanticContent(redex.bytes, redex.token).envelope, redex.envelope);
});

test("a large normalized carrier remains immutable and re-admits to identical bytes", () => {
  const term = mark("semantic carrier ".repeat(8_192));
  const identified = identifyNormalizedSemanticContent({
    objectKind: "example.large-normalized-carrier",
    semanticType: BASE,
    term,
    witnessRoot: EMPTY_WITNESS_ROOT,
  });
  const admitted = admitNormalizedSemanticContent(identified.bytes, identified.token);
  assert.equal(Object.isFrozen(identified.envelope), true);
  assert.equal(Object.isFrozen(identified.envelope.settledBody), true);
  assert.notStrictEqual(identified.envelope.settledBody, term);
  assert.deepEqual(admitted.bytes, identified.bytes);
  assert.deepEqual(admitted.envelope, identified.envelope);
});

test("identity settlement names an explicit shared empty witness bundle", () => {
  const identified = identifyNormalizedSemanticContent({
    objectKind: "example.unwitnessed-mark",
    semanticType: BASE,
    term: mark("body"),
    witnessRoot: EMPTY_WITNESS_ROOT,
  });
  assert.match(EMPTY_WITNESS_ROOT, /^ni:\/\/\/sha-256;/u);
  assert.equal(identified.envelope.witnessRoot, EMPTY_WITNESS_ROOT);
});

test("declared variable-length list types are admitted by the canonical SEN runtime", () => {
  const semanticType = ["list", BASE];
  const term = ["pair", ["mark", "list"], ["pair", ["mark", "first"], ["pair", ["mark", "second"], ["star"]]]];
  const identified = identifyNormalizedSemanticContent({
    objectKind: "example.variable-length-list",
    semanticType,
    term,
    witnessRoot: EMPTY_WITNESS_ROOT,
  });

  assert.deepEqual(identified.envelope.semanticType, semanticType);
  assert.deepEqual(identified.envelope.settledBody, term);
  assert.deepEqual(
    admitNormalizedSemanticContent(identified.bytes, identified.token).envelope,
    identified.envelope,
  );
});

test("obsolete product type spelling is not an identity-admission fallback", () => {
  assert.throws(
    () => identifyNormalizedSemanticContent({
      objectKind: "example.obsolete-type",
      semanticType: ["product", BASE, BASE],
      term: pair(mark("left"), mark("right")),
      witnessRoot: EMPTY_WITNESS_ROOT,
    }),
    (error) => error.code === "non-relational-content",
  );
});

test("byte identity uses the exact standard JSON byte carrier, never a Buffer-shaped record", () => {
  const bytes = Buffer.from([0, 1, 2, 250, 255]);
  const content = identifyBytesSemanticContent({
    objectKind: "example.bytes",
    bytes,
    mediaType: "application/example",
    witnessRoot: EMPTY_WITNESS_ROOT,
  });
  const explicitCarrier = identifyJsonSemanticContent({
    objectKind: "example.bytes",
    value: { mediaType: "application/example", contentBase64: "AAEC+v8=" },
    witnessRoot: EMPTY_WITNESS_ROOT,
  });
  assert.equal(content.token, explicitCarrier.token);
  assert.deepEqual(content.bytes, explicitCarrier.bytes);
  assert.throws(
    () => identifyJsonSemanticContent({ objectKind: "example.bytes", value: bytes, witnessRoot: EMPTY_WITNESS_ROOT }),
    (error) => error.code === "non-relational-content",
  );
});

test("refuses unsupported profiles, malformed witnesses, and mutation", () => {
  const input = { objectKind: "example.mark", semanticType: BASE, term: mark("body"), witnessRoot: witnessA };
  assert.throws(
    () => identifyNormalizedSemanticContent({ ...input, normalizationProfile: "urn:foreign:normalizer" }),
    (error) => error.code === "unsupported-normalization-profile",
  );
  assert.throws(
    () => identifyNormalizedSemanticContent({ ...input, settlementProfile: "urn:lenticule:articulating:fregean-four:1" }),
    (error) => error.code === "unsupported-settlement-profile",
  );
  assert.throws(
    () => identifyNormalizedSemanticContent({ ...input, witnessRoot: "ni:///sha-256:not-canonical" }),
    (error) => error.code === "malformed-content-address",
  );

  const identified = identifyNormalizedSemanticContent(input);
  const changedEnvelope = structuredClone(identified.envelope);
  changedEnvelope.witnessRoot = witnessB;
  assert.equal(verifyNormalizedSemanticContent(identified.token, changedEnvelope), false);
  const changedBytes = Buffer.from(identified.bytes);
  changedBytes[changedBytes.length - 1] ^= 1;
  assert.throws(
    () => admitNormalizedSemanticContent(changedBytes, identified.token),
    (error) => typeof error.code === "string",
  );
});

// Phase-1 relocation regression: real (objectKind, value) pairs pulled
// directly from real `data/logs/**/witness-journal-seavt.jsonl` files
// elsewhere in this workspace (decoded from their persisted SEN-term `a`/`v`
// coordinates), each paired with the exact `ni:` identity that was actually
// persisted as that record's `e` coordinate. These are not synthetic vectors:
// they are the empirical proof that relocating this module out of
// `semantic-content-identify-service` and into this runtime package changed
// not one byte of its output. `sourceFile` on each entry names the real
// on-disk journal the sample was pulled from, for re-verification.
const witnessJournalSamples = JSON.parse(
  readFileSync(new URL("../content/vectors/witness-journal-regression-samples.json", import.meta.url)),
);

test("real witness-journal entries reproduce their exact persisted ni: identity after relocation", () => {
  assert.ok(witnessJournalSamples.length >= 5, "expected at least 5 real regression samples");
  for (const sample of witnessJournalSamples) {
    const identity = identifyJsonSemanticContent({
      objectKind: sample.objectKind,
      value: sample.value,
      witnessRoot: EMPTY_WITNESS_ROOT,
    });
    assert.equal(
      identity.id,
      sample.expectedId,
      `objectKind ${sample.objectKind} (from ${sample.sourceFile}) must reproduce its persisted identity`,
    );
  }
});
