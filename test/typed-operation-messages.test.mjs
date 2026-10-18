import test from "node:test";
import assert from "node:assert/strict";
import { admit } from "@red-cup-engineering/signcell/type-system";
import {
  TYPED_OPERATION_MESSAGE_VERSION, TYPED_OPERATION_REQUEST_KIND,
  TYPED_OPERATION_RESULT_KIND, TYPED_OPERATION_REFUSAL_KIND,
  typedOperationRequestType, typedOperationResultType, typedOperationRefusalType,
} from "../src/typed-operation-message.mjs";

test("Code owns the existing versioned request, result and refusal types", () => {
  assert.equal(TYPED_OPERATION_MESSAGE_VERSION, 1);
  assert.equal(typedOperationRequestType.id, "typed-operation-message.request.v1");
  assert.equal(typedOperationResultType.id, "typed-operation-message.result.v1");
  assert.equal(typedOperationRefusalType.id, "typed-operation-message.refusal.v1");
  const request = Object.freeze({
    version: 1, kind: TYPED_OPERATION_REQUEST_KIND,
    requestId: "one", operationId: "test:read",
    inputCodec: "json", input: "{}", outputCodec: "json", actorResourceCatalog: {},
  });
  assert.equal(admit(typedOperationRequestType, request).ok, true);
  assert.equal(admit(typedOperationResultType, {
    version: 1, kind: TYPED_OPERATION_RESULT_KIND,
    requestId: "one", outputCodec: "json", output: "42",
  }).ok, true);
  assert.equal(admit(typedOperationRefusalType, {
    version: 1, kind: TYPED_OPERATION_REFUSAL_KIND,
    requestId: "one", code: "denied", message: "no grant",
  }).ok, true);
  for (const bad of [
    { ...request, version: 2 }, { ...request, requestId: "" },
    { ...request, kind: TYPED_OPERATION_RESULT_KIND },
    { ...request, unexpectedGrant: true },
  ]) assert.equal(admit(typedOperationRequestType, bad).ok, false);
});
