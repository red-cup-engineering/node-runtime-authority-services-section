/** Bounded object-input source proposal for the existing addressed operation family.
 * This is the pure body and its boundary declaration, not a registered Operation.
 * A higher operation owner captures this export with the original JSNode closure
 * provider and supplies these schemas/effects to the original operation constructor.
 */
import { canonicalizeJson, JSON_RESOURCE_ENVELOPE } from "@red-cup-engineering/json-services-section/canonical-json";
import { applyExactSourceEdits } from "./exact-source-edits.mjs";

const MAX_BYTES = 65_536;
const MAX_EDITS = 128;
const encoder = new TextEncoder();

// maxLength is only a preliminary character bound; the body enforces UTF-8 bytes.
export const inputSchema = canonicalizeJson({
  type: "object", additionalProperties: false,
  required: ["text", "edits", "expectedSourceSha256"],
  properties: {
    text: { type: "string", maxLength: MAX_BYTES },
    expectedSourceSha256: { type: "string", minLength: 64, maxLength: 64, pattern: "^[0-9a-f]{64}$" },
    edits: {
      type: "array", minItems: 1, maxItems: MAX_EDITS,
      items: {
        type: "object", additionalProperties: false,
        required: ["start", "end", "text", "original"],
        properties: {
          start: { type: "integer", minimum: 0, maximum: Number.MAX_SAFE_INTEGER },
          end: { type: "integer", minimum: 0, maximum: Number.MAX_SAFE_INTEGER },
          text: { type: "string", maxLength: MAX_BYTES },
          original: { type: "string", maxLength: MAX_BYTES },
        },
      },
    },
  },
}, JSON_RESOURCE_ENVELOPE).value;

export const outputSchema = Object.freeze({ type: "string", maxLength: MAX_BYTES });
export const effects = Object.freeze({
  class: "pure", replay: "safe", coordination: "coordination-free",
  deterministic: true, totality: "partial",
});

function exactRecord(value, keys, name) {
  if (value === null || typeof value !== "object" || Array.isArray(value) ||
      Object.keys(value).length !== keys.length || keys.some(key => !Object.hasOwn(value, key)))
    throw new TypeError(`${name} must carry exactly ${keys.join(", ")}`);
}

/** The strict original JSON codec has already admitted Unicode scalar strings. */
function boundedStableText(value, name) {
  if (typeof value !== "string") throw new TypeError(`${name} must be a string`);
  if (encoder.encode(value).byteLength > MAX_BYTES)
    throw new RangeError(`${name} exceeds ${MAX_BYTES} UTF-8 bytes`);
  if (value.normalize("NFC") !== value)
    throw new TypeError(`${name} must already be NFC-stable; normalization is not a source edit`);
}

function scalarBoundary(text, offset) {
  if (offset <= 0 || offset >= text.length) return true;
  const before = text.charCodeAt(offset - 1), after = text.charCodeAt(offset);
  return !(before >= 0xd800 && before <= 0xdbff && after >= 0xdc00 && after <= 0xdfff);
}

/** Propose exact source bytes; never write, register, receive or grant authority.
 * Offsets are UTF-16 code units into the admitted preimage, at scalar boundaries.
 * The fixed JSON envelope and per-text bounds are not a sandbox for arbitrary JS.
 */
export function applyExactSourceEditOperation(input) {
  // Snapshot before field access, hashing or UTF-8 encoding. This rejects getters,
  // non-JSON values, malformed scalars and over-budget canonical input unchanged.
  const value = canonicalizeJson(input, JSON_RESOURCE_ENVELOPE).value;
  exactRecord(value, ["text", "edits", "expectedSourceSha256"], "exact source edit input");
  boundedStableText(value.text, "source text");
  if (typeof value.expectedSourceSha256 !== "string" || value.expectedSourceSha256.length !== 64 ||
      !/^[0-9a-f]{64}$/u.test(value.expectedSourceSha256))
    throw new TypeError("expectedSourceSha256 must be a lowercase 64-hex SHA-256 digest");
  if (!Array.isArray(value.edits) || value.edits.length < 1 || value.edits.length > MAX_EDITS)
    throw new RangeError(`edits must contain 1..${MAX_EDITS} records`);
  for (const edit of value.edits) {
    exactRecord(edit, ["start", "end", "text", "original"], "source edit");
    for (const offset of [edit.start, edit.end]) {
      if (!Number.isSafeInteger(offset) || offset < 0)
        throw new RangeError("source edit offsets must be nonnegative safe UTF-16 integers");
      if (!scalarBoundary(value.text, offset))
        throw new RangeError("source edit offset splits a Unicode scalar value");
    }
    boundedStableText(edit.original, "original span");
    boundedStableText(edit.text, "replacement text");
  }
  // Exactly one delegation. The original preimage/span/overlap/insertion guards
  // remain authoritative, including end-before-start and out-of-source bounds.
  const output = applyExactSourceEdits(value.text, value.edits, {
    expectedSourceSha256: value.expectedSourceSha256,
  });
  canonicalizeJson(output, JSON_RESOURCE_ENVELOPE);
  // Separately NFC-stable pieces can compose into a non-NFC output at a join.
  boundedStableText(output, "output text");
  return output;
}
