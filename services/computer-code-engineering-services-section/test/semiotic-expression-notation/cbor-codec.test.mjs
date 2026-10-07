import assert from "node:assert/strict";
import test from "node:test";
import { decodeCanonical, encodeCanonical } from "@red-cup-engineering/cbor-services-section";
import { canonicalCborToNiUri } from "@red-cup-engineering/cbor-services-section";
import { decodeSemantic, semanticBytes, semanticId } from "@red-cup-engineering/computer-content-engineering-services-section/semiotic-content-address";

test("canonical SEN carrier bytes round-trip and retain their NI identity", () => {
  const term = ["ascribe", ["base", "operation"], ["mark", "é"]];
  const bytes = semanticBytes(term);
  assert.deepEqual(decodeSemantic(bytes), term);
  assert.deepEqual(bytes, encodeCanonical(term));
  assert.equal(semanticId(term), canonicalCborToNiUri(bytes));
});

test("decoded canonical bytes are normalized before they become an SEN carrier", () => {
  const bytes = encodeCanonical(["mark", "e\u0301"]);
  assert.deepEqual(decodeSemantic(bytes), ["mark", "é"]);
  assert.deepEqual(decodeCanonical(bytes), ["mark", "e\u0301"]);
});

test("semanticBytes encodes a deep finite carrier without exhausting the call stack", () => {
  let value = ["nil", ["base"]];
  for (let index = 0; index < 20_000; index += 1)
    value = ["cons", ["mark", String(index)], value];
  assert.ok(semanticBytes(value).length > 0);
});
