import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import {
  applyExactSourceEditOperation, inputSchema, outputSchema, effects,
} from "@red-cup-engineering/computer-code-engineering-services-section/exact-source-edit-operation";
import { applyExactSourceEdits } from "../src/exact-source-edits.mjs";

const digest = text => createHash("sha256").update(text, "utf8").digest("hex");
const request = (text, edits) => ({ text, edits, expectedSourceSha256: digest(text) });
const replace = (text, replacement = "X") => request(text, [
  { start: 0, end: text.length, original: text, text: replacement },
]);

test("exports closed object boundaries and partial pure effects, not an admitted Operation", () => {
  assert.deepEqual(inputSchema.required, ["text", "edits", "expectedSourceSha256"]);
  assert.equal(inputSchema.additionalProperties, false);
  assert.equal(inputSchema.properties.edits.maxItems, 128);
  assert.deepEqual(inputSchema.properties.edits.items.required, ["start", "end", "text", "original"]);
  assert.equal(inputSchema.properties.edits.items.additionalProperties, false);
  assert.equal(inputSchema.properties.edits.items.properties.start.maximum, Number.MAX_SAFE_INTEGER);
  assert.deepEqual(outputSchema, { type: "string", maxLength: 65536 });
  assert.deepEqual(effects, { class: "pure", replay: "safe", coordination: "coordination-free", deterministic: true, totality: "partial" });
  assert.equal(Object.isFrozen(inputSchema.properties.edits.items), true);
});

test("delegates exact UTF-16 spans and preserves BOM, CRLF and untouched UTF-8 bytes", () => {
  const text = "\uFEFFconst basket = '🧺';\r\nconst old = 'é';\r\n";
  const at = text.indexOf("old");
  const input = request(text, [{ start: at, end: at + 3, original: "old", text: "next" }]);
  const before = structuredClone(input);
  const result = applyExactSourceEditOperation(input);
  const expected = text.slice(0, at) + "next" + text.slice(at + 3);
  assert.deepEqual(Buffer.from(result, "utf8"), Buffer.from(expected, "utf8"));
  assert.equal(result, applyExactSourceEdits(text, input.edits, { expectedSourceSha256: input.expectedSourceSha256 }));
  assert.deepEqual(input, before);
  assert.equal(result.charCodeAt(0), 0xfeff);
});

test("astral content may precede or occupy a span; offset units are not code points or bytes", () => {
  const text = "🧺a🚀b";
  assert.equal(applyExactSourceEditOperation(request(text, [
    { start: 2, end: 3, original: "a", text: "A" },
    { start: 3, end: 5, original: "🚀", text: "🌱" },
  ])), "🧺A🌱b");
  for (const [start, end] of [[1, 1], [0, 1], [1, 2], [3, 4], [4, 5]])
    assert.throws(() => applyExactSourceEditOperation(request(text, [
      { start, end, original: "", text: "" },
    ])), /splits a Unicode scalar/);
});

test("strict original JSON admission rejects malformed scalars in every input text slot", () => {
  for (const malformed of ["\uD800", "\uDC00", "a\uD800b", "\uD800\uD800"]) {
    for (const slot of ["source", "replacement", "original", "digest"]) {
      const input = replace("ab");
      if (slot === "source") input.text = malformed;
      if (slot === "replacement") input.edits[0].text = malformed;
      if (slot === "original") input.edits[0].original = malformed;
      if (slot === "digest") input.expectedSourceSha256 = malformed;
      assert.throws(() => applyExactSourceEditOperation(input), /unicode-scalar/);
    }
  }
  // The general primitive can split a pair. This bounded wrapper refuses before
  // such an output can be produced; its original primitive stays unchanged.
  const input = request("🚀", [{ start: 0, end: 1, original: "\uD83D", text: "" }]);
  assert.equal(applyExactSourceEdits(input.text, input.edits), "\uDE80");
  assert.throws(() => applyExactSourceEditOperation(input), /unicode-scalar/);
});

test("non-NFC inputs refuse rather than normalize the exact preimage or edits", () => {
  const decomposed = "e\u0301";
  for (const slot of ["source", "replacement", "original"]) {
    const input = replace("ab");
    if (slot === "source") input.text = decomposed;
    if (slot === "replacement") input.edits[0].text = decomposed;
    if (slot === "original") input.edits[0].original = decomposed;
    assert.throws(() => applyExactSourceEditOperation(input), /NFC-stable/);
  }
  assert.equal(applyExactSourceEditOperation(replace("é", "ö")), "ö");
});

test("NFC stability is checked after composition, including deletion joins", () => {
  assert.equal("\u0301".normalize("NFC"), "\u0301");
  assert.throws(() => applyExactSourceEditOperation(request("e", [
    { start: 1, end: 1, original: "", text: "\u0301" },
  ])), /output text must already be NFC-stable/);
  const text = "eX\u0301";
  assert.equal(text.normalize("NFC"), text);
  assert.throws(() => applyExactSourceEditOperation(request(text, [
    { start: 1, end: 2, original: "X", text: "" },
  ])), /output text must already be NFC-stable/);
});

test("source, replacement, original and output limits count UTF-8 bytes", () => {
  const exact = "é".repeat(32768);
  assert.equal(Buffer.byteLength(exact), 65536);
  assert.equal(applyExactSourceEditOperation(replace(exact, exact)), exact);
  for (const slot of ["source", "replacement", "original"]) {
    const input = replace("a");
    if (slot === "source") input.text = exact + "é";
    if (slot === "replacement") input.edits[0].text = exact + "é";
    if (slot === "original") input.edits[0].original = exact + "é";
    assert.throws(() => applyExactSourceEditOperation(input), /65536 UTF-8 bytes/);
  }
  assert.throws(() => applyExactSourceEditOperation(request(exact, [
    { start: exact.length, end: exact.length, original: "", text: "x" },
  ])), /output text exceeds 65536 UTF-8 bytes/);
});

test("the original canonical input envelope refuses more than 1 MiB", () => {
  const input = request("", Array.from({ length: 17 }, () => ({
    start: 0, end: 0, original: "", text: "x".repeat(65536),
  })));
  assert.throws(() => applyExactSourceEditOperation(input), /canonical-limit/);
});

test("closed keys and mandatory guards apply even to a direct function invocation", () => {
  for (const key of ["text", "edits", "expectedSourceSha256"]) {
    const input = replace("ab"); delete input[key];
    assert.throws(() => applyExactSourceEditOperation(input), /must carry exactly/);
  }
  for (const key of ["start", "end", "text", "original"]) {
    const input = replace("ab"); delete input.edits[0][key];
    assert.throws(() => applyExactSourceEditOperation(input), /must carry exactly/);
  }
  const extraTop = replace("ab"); extraTop.authorizeWrite = true;
  const extraEdit = replace("ab"); extraEdit.edits[0].path = "/ignored";
  for (const input of [null, [], extraTop, extraEdit])
    assert.throws(() => applyExactSourceEditOperation(input), /must carry exactly/);
  for (const sha of ["", "ABCDEF".repeat(10) + "ABCD", "0".repeat(63), "0".repeat(64) + "\n", 1])
    assert.throws(() => applyExactSourceEditOperation({ ...replace("ab"), expectedSourceSha256: sha }), /64-hex/);
  for (const offset of [-1, 0.5, Number.MAX_SAFE_INTEGER + 1]) {
    const input = replace("ab"); input.edits[0].start = offset;
    assert.throws(() => applyExactSourceEditOperation(input), /safe UTF-16 integers/);
  }
});

test("untrusted accessors and non-JSON values refuse without invoking getters", () => {
  let called = false;
  const input = replace("ab");
  Object.defineProperty(input, "text", { enumerable: true, get() { called = true; return "ab"; } });
  assert.throws(() => applyExactSourceEditOperation(input), /accessor/);
  assert.equal(called, false);
  for (const bad of [undefined, () => "ab", 1n, new String("ab")])
    assert.throws(() => applyExactSourceEditOperation({ ...replace("ab"), text: bad }), /invalid-json-value/);
});

test("original stale-preimage, span, overlap and ambiguous-insertion guards survive", () => {
  const input = replace("abcd"); input.text += "!";
  assert.throws(() => applyExactSourceEditOperation(input), /source changed/);
  const staleSpan = replace("abcd"); staleSpan.edits[0].original = "ABCD";
  assert.throws(() => applyExactSourceEditOperation(staleSpan), /original span/);
  for (const edits of [
    [{ start: 0, end: 3, original: "abc", text: "x" }, { start: 2, end: 4, original: "cd", text: "y" }],
    [{ start: 1, end: 1, original: "", text: "x" }, { start: 1, end: 1, original: "", text: "y" }],
  ]) assert.throws(() => applyExactSourceEditOperation(request("abcd", edits)), /overlap|ambiguously/);
  for (const [start, end] of [[0, 5], [3, 2], [Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER]])
    assert.throws(() => applyExactSourceEditOperation(request("abcd", [{ start, end, original: "", text: "" }])), /outside/);
});

test("admitted cardinality includes 128 distinct edits; zero and 129 refuse", () => {
  const text = "x".repeat(128);
  const edits = Array.from({ length: 128 }, (_, start) => ({ start, end: start + 1, original: "x", text: "y" }));
  assert.equal(applyExactSourceEditOperation(request(text, edits.reverse())), "y".repeat(128));
  for (const count of [0, 129])
    assert.throws(() => applyExactSourceEditOperation(request(text, Array.from({ length: count }, () => edits[0]))), /1\.\.128/);
});

test("an independently specified historical theorem-reference repair preserves every other byte", () => {
  const wrong = "Obsmetrologia.Closure.RuleSystem.immediate_consequence_lfp";
  const correct = "Obsmetrologia.ClosureRule.immediate_consequence_lfp";
  const source = `fixed: true,\n        theorem: "${wrong}",\n`;
  const start = source.indexOf(wrong);
  const input = request(source, [{ start, end: start + wrong.length, original: wrong, text: correct }]);
  const accepted = `fixed: true,\n        theorem: "${correct}",\n`;
  assert.deepEqual(Buffer.from(applyExactSourceEditOperation(input)), Buffer.from(accepted));
  // This is source construction, not a certificate that the named Lean theorem ran.
});
