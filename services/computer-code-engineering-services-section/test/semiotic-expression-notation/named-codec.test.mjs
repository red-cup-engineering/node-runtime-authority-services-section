import assert from "node:assert/strict";
import test from "node:test";
import { tm } from "@red-cup-engineering/computer-data-services-section/semiotic-expression-notation";
import { evaluate } from "../../src/semiotic-expression-notation/eval.mjs";
import { inferTy } from "@red-cup-engineering/computer-data-services-section/semiotic-expression-notation/typing";
import {
  namedString, namedArray, namedObject, namedBool, namedGenerator,
  compileNamedSen, parseNamedSen,
  canonicalNamedSen, digestNamedSen,
} from "../../src/semiotic-expression-notation/named-codec.mjs";
// Every export below was originally differentially tested against the real,
// compiled metroplat build of the module this package was split out of
// (metroplat's reader/index.mts bundled the admission gate and this
// named-surface codec together; this package is the codec half). That
// evidence is preserved in this package's own commit history; metroplat has
// since been deleted, so these tests now assert the same hard-coded expected
// values directly instead of re-deriving them from a live comparison.

// =============================================================================
// Named-surface syntax.
// =============================================================================

// ── Builders — checking they build the expected pair/mark/star shapes exactly. ──

test("namedString: compiles to the canonical JSON string term", () => {
  assert.deepEqual(compileNamedSen(namedString("hello")), namedString("hello"));
});

test("namedArray: builds a mark-tagged pair spine over the given (possibly open) items, terminated by star", () => {
  const items = [["var", "x"], ["star"]];
  const tagMark = namedArray([])[1]; // ["mark", canonicalBytes(arrayTag)] — reused so this test doesn't hard-code canonicalBytes' own output
  assert.deepEqual(namedArray(items), ["pair", tagMark, ["pair", ["var", "x"], ["pair", ["star"], ["star"]]]]);
});

test("namedObject: sorts entries deterministically by key, regardless of input order", () => {
  const entries = [["b", ["star"]], ["a", ["var", "x"]]];
  const mine = namedObject(entries);
  assert.equal(mine[0], "pair");
  assert.equal(mine[1][0], "mark");
  // Confirm the sort actually happened: "a" sorts before "b" in the spine,
  // regardless of input order. mine = ["pair", tagMark, list]; list's first
  // cons cell is ["pair", firstEntry, restList]; firstEntry is
  // ["pair", ["mark", <canonical "a">], value].
  const list = mine[2];
  const firstEntry = list[1];
  assert.deepEqual(firstEntry[2], ["var", "x"]);
});

test("namedBool: compiles to the truth-axis charge marks", () => {
  assert.deepEqual(namedBool(true), ["mark", "held"]);
  assert.deepEqual(namedBool(false), ["mark", "denied"]);
  assert.deepEqual(inferTy([], compileNamedSen(namedBool(true))), ["base"]);
  assert.deepEqual(inferTy([], compileNamedSen(namedBool(false))), ["base"]);
});

test("namedGenerator: builds a bare mark for each of the four generator names", () => {
  for (const name of ["specialization", "converse", "subjectProjection", "objectProjection"]) {
    assert.deepEqual(namedGenerator(name), ["mark", name]);
  }
});

test("namedGenerator: rejects a name that is not one of the four generators", () => {
  assert.throws(() => namedGenerator("not-a-generator"), TypeError);
});

// ── compileNamedSen — the single most important behavioral test in this
//    module: confirm resolveByFca's "innermost binder wins" claim concretely.
//    An outer binder named "x" and an inner binder ALSO named "x" are BOTH
//    in scope at the point the innermost lambda's body resolves "x" — only
//    the "take the last match scanning from the end" tie-break inside
//    resolveByFca picks the inner one. If that tie-break were wrong (e.g.
//    picked the outer one, or picked arbitrarily), this compiles to
//    `["lam", ["lam", ["var", 1]]]` instead of the correct
//    `["lam", ["lam", ["var", 0]]]`, and the two nested lambdas would
//    silently swap which value the body actually uses. ──

test("compileNamedSen: shadowing — nested binders BOTH named \"x\"; the inner var resolves to the INNERMOST (closer) binder, not the outer one", () => {
  const shadowed = ["lam", "x", ["lam", "x", ["var", "x"]]];
  const compiled = compileNamedSen(shadowed);
  // de Bruijn index 0 at that depth means "the nearest enclosing binder" —
  // i.e. the inner lambda's own parameter, confirming innermost-wins.
  assert.deepEqual(compiled, ["lam", ["lam", ["var", 0]]]);
});

test("compileNamedSen: shadowing evaluates correctly — applying the shadowed function to two different marks returns the INNER argument, confirming resolution picked the inner binder not just structurally but semantically", () => {
  const shadowed = ["lam", "x", ["lam", "x", ["var", "x"]]];
  const compiled = compileNamedSen(shadowed);
  // (lam x. lam x. x) outerArg innerArg  ==>  innerArg, if and only if the
  // body's "x" really is bound by the inner lambda.
  const applied = tm.app(tm.app(compiled, tm.mark("outer-value")), tm.mark("inner-value"));
  const settled = evaluate(applied);
  assert.deepEqual(settled, tm.mark("inner-value"));
});

test("compileNamedSen: a genuinely non-trivial NamedTm (nested lam/var/app/pair with shadowing) evaluates to the expected value", () => {
  // (lam x. lam y. lam x. pair (var x) (var y)) A B C
  //   -> innermost x (bound to C) paired with y (bound to B)
  const surface = [
    "lam", "x", ["lam", "y", ["lam", "x",
      ["pair", ["var", "x"], ["var", "y"]],
    ]],
  ];
  const compiled = compileNamedSen(surface);

  const applied = tm.app(
    tm.app(tm.app(compiled, tm.mark("A")), tm.mark("B")),
    tm.mark("C"),
  );
  const settled = evaluate(applied);
  assert.deepEqual(settled, tm.pair(tm.mark("C"), tm.mark("B")));
});

test("compileNamedSen: without shadowing (two distinct names), resolution is unaffected — a sanity control alongside the shadowing tests", () => {
  const surface = ["lam", "a", ["lam", "b", ["var", "a"]]];
  const compiled = compileNamedSen(surface);
  assert.deepEqual(compiled, ["lam", ["lam", ["var", 1]]]);
});

test("compileNamedSen: throws on an unbound variable", () => {
  const surface = ["var", "nowhere"];
  assert.throws(() => compileNamedSen(surface), TypeError);
});

test("compileNamedSen validates the completed tree without allowing an embed to capture a surrounding binder", () => {
  assert.throws(
    () => compileNamedSen(["lam", "x", ["embed", ["var", 0]]]),
    /embed requires one closed SEN term/u,
  );
  assert.throws(() => compileNamedSen(["embed", ["unknown-form"]]), /unknown or malformed SEN term tag/u);
  assert.throws(() => compileNamedSen(["embed", ["var", -1]]), /invalid SEN natural atom/u);
  assert.deepEqual(compileNamedSen(["lam", "x", ["pair", ["var", "x"], ["mark", "ok"]]]),
    ["lam", ["pair", ["var", 0], ["mark", "ok"]]]);
});

// ── namedOfCompiled / canonicalNamedSen (reverse direction) — round-trip a
//    compiled term back to named surface / canonical JSON. (namedOfCompiled
//    itself is not exported; canonicalNamedSen and digestNamedSen are the
//    exported surface over it.) ──

test("canonicalNamedSen: the round-tripped named form uses positional placeholder names ($0, $1, ...), never the original source names", () => {
  const shadowed = ["lam", "x", ["lam", "x", ["var", "x"]]];
  const compiled = compileNamedSen(shadowed);
  const canonical = canonicalNamedSen(compiled);
  const parsed = JSON.parse(canonical);
  assert.deepEqual(parsed, ["lam", "$0", ["lam", "$1", ["var", "$1"]]]);
});

test("named codec keeps each sum-case branch's independent binder", () => {
  const surface = [
    "case", ["inl", ["mark", "left"], ["unit"]],
    "left", ["var", "left"],
    "right", ["mark", "right"],
  ];
  const compiled = compileNamedSen(surface);
  assert.deepEqual(evaluate(compiled), tm.mark("left"));
  assert.deepEqual(JSON.parse(canonicalNamedSen(compiled)), [
    "case", ["inl", ["mark", "left"], ["unit"]],
    "$0", ["var", "$0"],
    "$0", ["mark", "right"],
  ]);
});

test("digestNamedSen: two structurally different compiled terms produce different digests", () => {
  const a = compileNamedSen(["mark", "a"]);
  const b = compileNamedSen(["mark", "b"]);
  assert.throws(() => digestNamedSen(tm.lam(tm.var(0))), /closed and well typed/);
  assert.notEqual(digestNamedSen(a), digestNamedSen(b));
});

// ── parseNamedSen — end-to-end on JSON-encoded named surface. ──

test("parseNamedSen: end-to-end parses a small JSON-encoded named surface, compiles it, and admits it", () => {
  const source = JSON.stringify(["mark", "payload"]);
  const term = parseNamedSen(source);
  assert.deepEqual(term, tm.mark("payload"));
  assert.deepEqual(evaluate(term), tm.mark("payload"));
});

test("parseNamedSen: throws when the compiled result is not closed and well-typed", () => {
  // "x" free in the top-level surface — compiles to an open var.
  const source = JSON.stringify(["var", "unbound"]);
  assert.throws(() => parseNamedSen(source), TypeError);
});
