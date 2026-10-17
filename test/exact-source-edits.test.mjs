import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { applyExactSourceEdits } from "../src/exact-source-edits.mjs";

test("exact-span replacement preserves all untouched code units", () => {
  const text = "start\r\nalpha\r\nbeta\r\nend\r\n";
  const changes = [
    {start: text.indexOf("beta"), end: text.indexOf("beta") + 4, original: "beta", text: "B"},
    {start: text.indexOf("alpha"), end: text.indexOf("alpha") + 5, original: "alpha", text: "A"},
  ];
  const originalOrder = [...changes];
  assert.equal(applyExactSourceEdits(text, changes), "start\r\nA\r\nB\r\nend\r\n");
  assert.deepEqual(changes, originalOrder);
});

test("a source revision mismatch refuses even if the target substring still looks familiar", () => {
  const old = "const alpha = 1;\nconst beta = 2;\n";
  const sha = createHash("sha256").update(old).digest("hex");
  const edit = { start: old.indexOf("beta"), end: old.indexOf("beta") + 4, original: "beta", text: "gamma" };
  assert.equal(applyExactSourceEdits(old, [edit], { expectedSourceSha256: sha }),
    "const alpha = 1;\nconst gamma = 2;\n");
  assert.throws(() => applyExactSourceEdits(old + "\n", [edit], { expectedSourceSha256: sha }),
    /source changed/);
  assert.throws(() => applyExactSourceEdits(old, [edit], { expectedSourceSha256: "not-sha" }),
    /source changed/);
});

test("stale original spans and all overlapping edits fail without a candidate output", () => {
  assert.throws(() => applyExactSourceEdits("abcd", [
    { start: 0, end: 2, original: "XX", text: "ab" }]), /original span/);
  assert.throws(() => applyExactSourceEdits("abcd", [
    { start: 0, end: 3, text: "x" }, { start: 2, end: 4, text: "y" }]), /overlap/);
  assert.throws(() => applyExactSourceEdits("abcd", [
    { start: -1, end: 2, text: "x" }]), /outside/);
  assert.throws(() => applyExactSourceEdits("abcd", [
    { start: 1, end: 5, text: "x" }]), /outside/);
  assert.throws(() => applyExactSourceEdits("abcd", [
    { start: 1.5, end: 2, text: "x" }]), /outside/);
  assert.throws(() => applyExactSourceEdits("abcd", null), /array/);
});

test("insertions/deletions remain possible and an empty plan is the exact identity", () => {
  assert.equal(applyExactSourceEdits("abcd", [
    { start: 0, end: 0, original: "", text: "#" },
    { start: 1, end: 3, original: "bc", text: "" },
    { start: 4, end: 4, original: "", text: "!" },
  ]), "#ad!");
  assert.equal(applyExactSourceEdits("hello\n", []), "hello\n");
});

test("two independently proposed insertions at one position refuse ambiguity", () => {
  assert.throws(() => applyExactSourceEdits("abc", [
    { start: 1, end: 1, text: "left" },
    { start: 1, end: 1, text: "right" },
  ]), /ambiguously/);
  // A single insertion sharing a boundary with a replacement is still unambiguous.
  assert.equal(applyExactSourceEdits("abcd", [
    { start: 1, end: 1, text: "[" },
    { start: 1, end: 3, original: "bc", text: "BC" },
    { start: 3, end: 3, text: "]" },
  ]), "a[BC]d");
});

test("many distinct edits preserve UTF-16 code-unit offsets and untouched text", () => {
  const lines = Array.from({ length: 10000 }, (_, i) => "\uD83E\uDDFA:" + i + "\r\n");
  const original = lines.join("");
  let at = 0;
  const edits = lines.map((line, i) => {
    const edit = {
      start: at + 2, end: at + 3, original: ":", text: i % 2 === 0 ? "=" : "-",
    };
    at += line.length;
    return edit;
  });
  const expected = lines.map((line, i) => line.replace(":", i % 2 === 0 ? "=" : "-")).join("");
  assert.equal(applyExactSourceEdits(original, edits.reverse()), expected);
});
