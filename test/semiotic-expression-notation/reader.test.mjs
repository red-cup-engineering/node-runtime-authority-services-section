import assert from "node:assert/strict";
import test from "node:test";
import { tm } from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation";
import {
  SEN_JSON,
  isRelationalTerm, parseSen, settleSen,
  extractRelationalScripts, htmlIsRelational, settleRelationalHtml,
  sessionIsRelational, settleRelationalSession,
} from "../../src/semiotic-expression-notation/reader.mjs";
// Every exported value below was originally differentially tested against
// the real, compiled metroplat build of the module this package ports —
// the load-bearing evidence that the port is behaviorally identical, not
// merely structurally similar. That evidence is preserved in this package's
// own commit history; metroplat has since been deleted, so these tests now
// assert the same hard-coded expected values directly instead of
// re-deriving them from a live comparison. The named-surface half of the
// original module (namedString/compileNamedSen/etc.) moved to
// @red-cup-engineering/computer-code-engineering-services-section/semiotic-expression-notation/named-codec along with its
// own copy of this differential-testing pattern; this file keeps only the
// admission-gate and HTML/session-gate coverage.

// =============================================================================
// 1. Admission gate — isRelationalTerm / parseSen / settleSen.
// =============================================================================

// A closed term that is inferable directly: `inferTy` has no case for a bare
// `lam` (it is checkable, not inferable, in this bidirectional typer), so a
// positive fixture needs an `app` whose function position is a `lam` — the
// one path `inferTy`'s "app" case takes to bootstrap a type for a lambda
// from its argument's inferred type. This is the identity function applied
// to a mark, which both infers (base type) and carries a real redex.
const closedWellTypedTerm = tm.app(tm.lam(tm.var(0)), tm.mark("payload"));

test("isRelationalTerm: accepts a closed, well-typed term", () => {
  assert.equal(isRelationalTerm(closedWellTypedTerm), true);
});

test("isRelationalTerm: rejects an open term (a free de Bruijn variable)", () => {
  assert.equal(isRelationalTerm(tm.var(0)), false);
});

test("isRelationalTerm: rejects a closed but ill-typed term (fst of a unit, not a pair)", () => {
  const illTyped = tm.fst(tm.star());
  assert.equal(isRelationalTerm(illTyped), false);
});

test("isRelationalTerm: rejects plain JSON data — an object is data, not a morphism", () => {
  assert.equal(isRelationalTerm({ a: 1 }), false);
});

test("isRelationalTerm: rejects plain JSON data — a non-tag array is data, not a morphism", () => {
  assert.equal(isRelationalTerm([1, 2, 3]), false);
});

test("isRelationalTerm: accepts the unit term (closed and trivially well-typed)", () => {
  assert.equal(isRelationalTerm(tm.star()), true);
});

test("parseSen: round-trips valid SEN source into the same term", () => {
  const source = JSON.stringify(closedWellTypedTerm);
  const parsed = parseSen(source);
  assert.deepEqual(parsed, closedWellTypedTerm);
});

test("parseSen: throws on source that is well-formed JSON but not a well-typed closed term", () => {
  assert.throws(() => parseSen(JSON.stringify({ a: 1 })), TypeError);
});

test("parseSen: throws on source that is not even well-formed JSON", () => {
  assert.throws(() => parseSen("{not valid json"));
});

test("settleSen: actually reduces a term with a real redex (identity applied to a mark)", () => {
  const settled = settleSen(closedWellTypedTerm);
  assert.deepEqual(settled, tm.mark("payload"));
});

test("settleSen: typed admission precedes a bounded reduction", () => {
  assert.throws(() => settleSen(tm.var(0)), /well-typed closed term/u);
  assert.throws(() => settleSen(tm.fst(tm.star())), /well-typed closed term/u);
  assert.deepEqual(settleSen(tm.star(), { fuel: 0 }), tm.star());
  assert.throws(
    () => settleSen(closedWellTypedTerm, { fuel: 0 }),
    error => error?.code === "fuel-exceeded",
  );
  assert.deepEqual(settleSen(closedWellTypedTerm, { fuel: 1 }), tm.mark("payload"));
});

test("HTML and session boundaries propagate the same finite reduction budget", () => {
  const html = `<script type="application/sen+json">${JSON.stringify(closedWellTypedTerm)}</script>`;
  assert.throws(
    () => settleRelationalHtml(html, { fuel: 0 }),
    error => error?.code === "fuel-exceeded",
  );
  assert.throws(
    () => settleRelationalSession([closedWellTypedTerm], { fuel: 0 }),
    error => error?.code === "fuel-exceeded",
  );
  assert.deepEqual(settleRelationalHtml(html, { fuel: 1 }), [tm.mark("payload")]);
  assert.deepEqual(settleRelationalSession([closedWellTypedTerm], { fuel: 1 }), [tm.mark("payload")]);
});

test("SEN_JSON: is the expected media-type string", () => {
  assert.equal(SEN_JSON, "application/sen+json; charset=utf-8");
});

// =============================================================================
// 2. Boundary settlement — the HTML `<script type="application/sen+json">`
//    gate and the message-stream session gate.
// =============================================================================

const senScriptBody = JSON.stringify(closedWellTypedTerm);
const nonSenScriptBody = "console.log('hello');";

function htmlWithOneSenAndOneNonSenScript() {
  return `<!doctype html>
<html>
<head><script type="application/sen+json">${senScriptBody}</script></head>
<body><script type="text/javascript">${nonSenScriptBody}</script></body>
</html>`;
}

test("extractRelationalScripts: pulls only the SEN script body out of a mixed document", () => {
  const html = htmlWithOneSenAndOneNonSenScript();
  const scripts = extractRelationalScripts(html);
  assert.deepEqual(scripts, [senScriptBody]);
});

test("htmlIsRelational: true for a document whose only script is SEN and well-typed", () => {
  const html = `<html><body><script type="application/sen+json">${senScriptBody}</script></body></html>`;
  assert.equal(htmlIsRelational(html), true);
});

test("htmlIsRelational: true for a document with no scripts at all (trivially relational)", () => {
  assert.equal(htmlIsRelational("<html><body><p>static</p></body></html>"), true);
});

test("htmlIsRelational: false when one script is not SEN (a mixed document)", () => {
  const html = htmlWithOneSenAndOneNonSenScript();
  assert.equal(htmlIsRelational(html), false);
});

test("htmlIsRelational: false when the script IS typed application/sen+json but its body is not well-typed", () => {
  const illTypedBody = JSON.stringify({ a: 1 });
  const html = `<html><body><script type="application/sen+json">${illTypedBody}</script></body></html>`;
  assert.equal(htmlIsRelational(html), false);
});

test("settleRelationalHtml: actually settles every SEN script's redex in an all-SEN document", () => {
  const html = `<html><body><script type="application/sen+json">${senScriptBody}</script></body></html>`;
  const settled = settleRelationalHtml(html);
  assert.deepEqual(settled, [tm.mark("payload")]);
});

test("settleRelationalHtml: settles multiple scripts in document order", () => {
  const otherRedex = tm.app(tm.lam(tm.pair(tm.var(0), tm.var(0))), tm.mark("dup"));
  const html = `<html><body>
<script type="application/sen+json">${JSON.stringify(closedWellTypedTerm)}</script>
<script type="application/sen+json">${JSON.stringify(otherRedex)}</script>
</body></html>`;
  const settled = settleRelationalHtml(html);
  assert.deepEqual(settled, [tm.mark("payload"), tm.pair(tm.mark("dup"), tm.mark("dup"))]);
});

test("settleRelationalHtml: throws when the document contains a non-relational (Turing) script", () => {
  const html = htmlWithOneSenAndOneNonSenScript();
  assert.throws(() => settleRelationalHtml(html), TypeError);
});

const senMessage = closedWellTypedTerm;
const nonSenMessage = { a: 1 };

test("sessionIsRelational: true when every message in the stream is an admitted SEN term", () => {
  assert.equal(sessionIsRelational([senMessage, tm.star()]), true);
});

test("sessionIsRelational: false when any single message is not SEN", () => {
  assert.equal(sessionIsRelational([senMessage, nonSenMessage]), false);
});

test("settleRelationalSession: actually settles every message's redex in an all-SEN stream", () => {
  const settled = settleRelationalSession([senMessage, tm.star()]);
  assert.deepEqual(settled, [tm.mark("payload"), tm.star()]);
});

test("settleRelationalSession: throws when the stream contains a non-relational message", () => {
  const stream = [senMessage, nonSenMessage];
  assert.throws(() => settleRelationalSession(stream), TypeError);
});
