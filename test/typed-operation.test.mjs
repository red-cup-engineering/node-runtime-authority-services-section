import assert from "node:assert/strict";
import test from "node:test";
import { defineType } from "@red-cup-engineering/signcell/type-system";
import { tm } from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation";
import {
  COMPUTER_ENGINEERING_SPECIFICATION_ID,
  admitOperation, composeOperations, declareCapabilityOperation, executeOperation,
} from "../src/typed-operation.mjs";

const textType = defineType({
  id: "typed-operation-regression-text",
  name: "Typed operation regression text",
  description: "An admitted text value at a portable code boundary.",
  parents: [],
  schema: { type: "string" },
}).value;

function senIdentity(id, type, descriptor = { kind: "string" }) {
  const admitted = admitOperation({
    specification: COMPUTER_ENGINEERING_SPECIFICATION_ID, id,
    domain: type, codomain: type, effects: [],
    body: {
      kind: "sen", term: tm.lam(tm.var(0)),
      inputDescriptor: descriptor, outputDescriptor: descriptor,
    },
  });
  assert.equal(admitted.ok, true, admitted.ok ? undefined : JSON.stringify(admitted.refusal));
  return admitted.value;
}

test("portable operations compose at the original typed code owner", () => {
  const identity = senIdentity("test-code-identity", textType);
  const composed = composeOperations(identity, identity, "test-code-double-identity");
  assert.equal(composed.ok, true, composed.ok ? undefined : JSON.stringify(composed.refusal));
  assert.deepEqual(executeOperation(composed.value, "carried text"), { ok: true, value: "carried text" });
});

test("composition refuses malformed operands through admission instead of dereferencing them", () => {
  const identity = senIdentity("test-code-identity-refusal", textType);
  for (const malformed of [null, undefined, {}, { codomain: { id: "pretend" } }]) {
    const first = composeOperations(malformed, identity, "refuse-producer");
    const second = composeOperations(identity, malformed, "refuse-consumer");
    assert.equal(first.ok, false);
    assert.equal(first.refusal.code, "CompositionRefused");
    assert.equal(second.ok, false);
    assert.equal(second.refusal.code, "CompositionRefused");
  }
});

test("SEN descriptor composition preserves lexical field identity rather than NFC aliasing", () => {
  const recordType = defineType({
    id: "typed-operation-regression-record",
    name: "Typed operation regression record",
    description: "An opaque object; SEN descriptor names refine the wire shape.",
    parents: [], schema: { type: "object" },
  }).value;
  const decomposed = senIdentity("decomposed-record", recordType, {
    kind: "record", fields: { "e\u0301": { kind: "string" } },
  });
  const composed = senIdentity("composed-record", recordType, {
    kind: "record", fields: { "\u00e9": { kind: "string" } },
  });
  const result = composeOperations(decomposed, composed, "invalid-lexical-join");
  assert.equal(result.ok, false);
  assert.equal(result.refusal.message, "SEN descriptors differ");
});

test("host effects require exact explicit tokens and cannot be granted by substring", () => {
  const operation = declareCapabilityOperation({
    id: "test-net-capability", domain: textType, codomain: textType,
    effects: ["net"], capability: "net.echo",
  });
  assert.equal(operation.ok, true);
  let invoked = 0;
  const resolveHost = () => (value) => { invoked += 1; return value; };
  for (const allowedEffects of ["internet", ["internet"], new Set(["net"])]) {
    const result = executeOperation(operation.value, "not authorized", { allowedEffects, resolveHost });
    assert.equal(result.ok, false);
    assert.equal(result.refusal.code, "EffectRefused");
  }
  assert.equal(invoked, 0, "an unauthorized capability must not run");
  const authorized = executeOperation(operation.value, "explicit authorization", {
    allowedEffects: ["net"], resolveHost,
  });
  assert.deepEqual(authorized, { ok: true, value: "explicit authorization" });
  assert.equal(invoked, 1);
});
