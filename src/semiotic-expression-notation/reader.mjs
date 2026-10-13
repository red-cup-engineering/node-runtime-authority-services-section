/**
 * notation — Semiotic Expression Notation (SEN)'s finite syntax/type admission
 * gate for closed terms, and its extension to HTML documents
 * and message-stream sessions.
 *
 * parseSen admits only closed, well-typed core syntax and returns it unreduced.
 * This is a finite syntax/type check, not evaluation and not a proof of a
 * uniform resource bound. settleSen separately uses the runtime's finite
 * reduction budget and may refuse with fuel-exceeded. That bounds accepted
 * contractions, not time or memory per step, and is not a strong-normalization
 * theorem or a promise that every admitted term settles within the budget.
 *
 * HTML/session admission below checks which script bodies have this syntax.
 * Their settlement calls preserve the same per-term reduction-budget boundary.
 *
 * NOTE (scoping, not yet acted on): `extractRelationalScripts`/`htmlIsRelational`/
 * `settleRelationalHtml` and `sessionIsRelational`/`settleRelationalSession` are
 * application-boundary logic (how a web document or a session admits SEN
 * content), not notation — per the operator's "an SEN services section needs
 * codecs and an evaluator, nothing else," these arguably don't belong in this
 * section at all. Flagged, not moved: no established home for them was found
 * yet. `isRelationalTerm`/`parseSen`/`settleSen` (the bare admission gate) stay
 * here regardless, composing typing + the reducer.
 *
 * The named-variable surface syntax (`compileNamedSen`/`parseNamedSen`/
 * `namedString`/`namedArray`/`namedObject`/`namedBool`/`namedGenerator`/
 * `namedOfCompiled`/`canonicalNamedSen`/`digestNamedSen`) has moved to its own
 * package, `@red-cup-engineering/computer-code-engineering-services-section/semiotic-expression-notation/named-codec`, under
 * `semiotic-expression-notation-codecs-services-section` — it is a codec (named
 * surface ↔ de-Bruijn `Tm`), this package is the admission gate; they were
 * bundled together before this split, which is exactly the "several functions,
 * several packages" scoping error being corrected.
 *
 * Originally transcribed from metroplat's `src/lib/language/reader/index.mts`
 * with TypeScript annotations replaced by JSDoc. Bounded settlement now uses
 * the existing runtime reducer;
 * `inferTy`/`isClosed` come from
 * `@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation/typing` in place of the
 * relative `../check/index.mts`.
 *
 * `parseJson` comes from the upstream JSON carrier's direct parse script, so
 * this reader has no codec-package dependency.
 */
import { evaluate as evaluateBounded } from "./runtime.mjs";
import { inferTy, isClosed } from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation/typing";
import { parse as parseJson } from "@red-cup-engineering/json-services-section";

/**
 * @typedef {import("./notation/types.mjs").Tm} Tm
 * @typedef {import("@red-cup-engineering/json-services-section").JsonValue} JsonValue
 */

/** The IANA-style media type for an SEN body. */
export const SEN_JSON = "application/sen+json; charset=utf-8";

/** Whether a value is a closed, well-typed SEN term. Plain JSON data (objects,
 *  non-tag arrays) is rejected: it is `data`, not a morphism.
 * @param {unknown} value
 * @returns {boolean}
 */
export function isRelationalTerm(value) {
  try {
    return isClosed(value) && inferTy([], value) !== null;
  } catch {
    return false;
  }
}

/** Parse and type-check SEN source into a term; throws unless it is a closed,
 *  well-typed SEN program.
 * @param {string} source
 * @returns {Tm}
 */
export function parseSen(source) {
  const value = parseJson(source);
  if (!isRelationalTerm(value)) throw new TypeError("sen: not a well-typed closed term");
  return value;
}

/** Settle an admitted SEN term using the runtime's existing bounded reducer.
 * The old reader called eval.normalize without any fuel limit; claiming a
 * bound in prose was not an operational bound. This adapter now requires a
 * closed, inferable term and reports exhaustion as `fuel-exceeded`, without
 * mistaking bounded execution for a strong-normalization theorem.
 * @param {Tm} term
 * @param {{ fuel?: number }} options
 * @returns {Tm}
 */
export function settleSen(term, { fuel = 10_000 } = {}) {
  if (!isRelationalTerm(term)) throw new TypeError("sen: not a well-typed closed term");
  return evaluateBounded(term, fuel).normalForm;
}

const SEN_SCRIPT = /<script\b[^>]*\btype\s*=\s*["']application\/sen\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
const ANY_SCRIPT = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;

function safeParse(source) {
  try {
    return JSON.parse(source);
  } catch {
    return undefined;
  }
}

/** Extract the source bodies of every `<script type="application/sen+json">` block.
 * @param {string} html
 * @returns {string[]}
 */
export function extractRelationalScripts(html) {
  return [...html.matchAll(SEN_SCRIPT)].map((match) => (match[1] ?? "").trim());
}

/** Whether EVERY script in the document is SEN and each body is a closed,
 *  well-typed term. A single non-SEN script (JavaScript, etc.) fails the gate; a
 *  document with no scripts is trivially relational (static).
 * @param {string} html
 * @returns {boolean}
 */
export function htmlIsRelational(html) {
  for (const match of html.matchAll(ANY_SCRIPT)) {
    const attrs = match[1] ?? "";
    const typeMatch = /\btype\s*=\s*["']([^"']*)["']/i.exec(attrs);
    const type = (typeMatch?.[1] ?? "").trim().toLowerCase();
    if (type !== "application/sen+json") return false;
    if (!isRelationalTerm(safeParse((match[2] ?? "").trim()))) return false;
  }
  return true;
}

/** Parse, type-check, and settle every SEN script in an HTML document. Throws if
 *  any script is not admitted by the SEN gate.
 * @param {string} html
 * @returns {Tm[]}
 */
export function settleRelationalHtml(html, options = {}) {
  if (!htmlIsRelational(html)) throw new TypeError("html: contains a non-relational (Turing) script");
  return extractRelationalScripts(html).map((source) => settleSen(parseSen(source), options));
}

/** Whether every message exchanged in a session is an admitted SEN term. This
 *  makes an open session locally settle message-by-message even when the session
 *  itself remains open. A single non-SEN message fails the gate. Messages are the
 *  parsed values carried on the wire.
 * @param {readonly unknown[]} messages
 * @returns {boolean}
 */
export function sessionIsRelational(messages) {
  return messages.every(isRelationalTerm);
}

/** Settle every message of a relational session; throws if any message is not an
 *  admitted SEN term.
 * @param {readonly unknown[]} messages
 * @returns {Tm[]}
 */
export function settleRelationalSession(messages, options = {}) {
  if (!sessionIsRelational(messages)) {
    throw new TypeError("session: contains a non-relational (Turing) message");
  }
  return messages.filter(isRelationalTerm).map((message) => settleSen(message, options));
}
