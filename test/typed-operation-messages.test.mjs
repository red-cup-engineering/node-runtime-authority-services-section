import test from "node:test";
import assert from "node:assert/strict";
import { admit } from "@red-cup-engineering/signcell/type-system";
import { invokeTypedOperation } from "../src/typed-operation-invoke.mjs";
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

test("source-owned Code invocation executes only explicitly registered message operations", async () => {
  const request = {
    version: 1, kind: TYPED_OPERATION_REQUEST_KIND, requestId: "source-cased",
    operationId: "object:read", inputCodec: "json",
    input: '{"answer":42}', outputCodec: "json", actorResourceCatalog: {},
  };
  const result = await invokeTypedOperation({
    operations: Object.freeze({ "object:read": value => ({value:value.answer}) }),
    request,
  });
  assert.deepEqual(result, {
    version: 1, kind: TYPED_OPERATION_RESULT_KIND, requestId: "source-cased",
    outputCodec: "json", output: '{"value":42}',
  });
  const invalid = await invokeTypedOperation({
    operations: Object.freeze({ "object:read": value => value }),
    request: {...request, input:"{"},
  });
  assert.equal(invalid.code, "malformed-input");
});

test("unregistered inherited names and prototype codecs never execute", async () => {
  let calls = 0;
  const operations = { "allowed": value => { calls++; return value; } };
  const request = {
    version: 1, kind: TYPED_OPERATION_REQUEST_KIND, requestId: "prototype-refusal",
    operationId: "constructor", inputCodec: "json", input: "{}",
    outputCodec: "json", actorResourceCatalog: {},
  };
  for(const name of ["constructor", "toString", "__proto__"]) {
    const result = await invokeTypedOperation({operations,request:{...request,operationId:name}});
    assert.equal(result.code, "unknown-operation");
  }
  const unsupported = await invokeTypedOperation({
    operations, request:{...request,operationId:"allowed",inputCodec:"constructor"},
  });
  assert.equal(unsupported.code, "unsupported-codec");
  assert.equal(calls, 0);
});

test("a failed or unencodable handler cannot forge a successful typed operation result", async () => {
  const request = {
    version: 1, kind:TYPED_OPERATION_REQUEST_KIND, requestId:"refuse-output",
    operationId:"test:read",inputCodec:"json",input:"{}",outputCodec:"json",
    actorResourceCatalog:{},
  };
  const failure = await invokeTypedOperation({
    operations:{"test:read":() => {throw Error("PRIVATE TOKEN CONTENT");}},request,
  });
  assert.equal(failure.code,"operation-failed");
  assert.ok(!JSON.stringify(failure).includes("PRIVATE TOKEN CONTENT"));
  const undefinedResult = await invokeTypedOperation({
    operations:{"test:read":()=>undefined},request,
  });
  assert.equal(undefinedResult.code,"malformed-output");
  const circular = {};
  circular.self = circular;
  const cyclicResult = await invokeTypedOperation({
    operations:{"test:read":()=>circular},request,
  });
  assert.equal(cyclicResult.code,"malformed-output");
});
