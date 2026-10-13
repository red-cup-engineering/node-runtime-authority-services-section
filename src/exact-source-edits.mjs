import { createHash } from "node:crypto";

/** Apply non-overlapping source edits from right to left. Every source code
 * unit outside the approved spans survives unchanged.
 *
 * A source-generation caller can supply a snapshot SHA-256 and an original
 * substring for each span; stale or ambiguous edits then fail before any
 * candidate output is returned. This primitive never writes files.
 */
export function applyExactSourceEdits(text, edits, { expectedSourceSha256 } = {}) {
  if (typeof text !== "string") throw new TypeError("source text must be a string");
  if (!Array.isArray(edits)) throw new TypeError("source edits must be an array");
  if (expectedSourceSha256 !== undefined) {
    const validDigest = typeof expectedSourceSha256 === "string" &&
      /^[0-9a-f]{64}$/u.test(expectedSourceSha256);
    const actual = createHash("sha256").update(text, "utf8").digest("hex");
    if (!validDigest || expectedSourceSha256 !== actual)
      throw new Error("source changed since exact edits were prepared");
  }
  const ordered = [...edits].sort((left, right) => left.start - right.start || left.end - right.end);
  let previousEnd = 0;
  for (const edit of ordered) {
    if (!edit || !Number.isSafeInteger(edit.start) || !Number.isSafeInteger(edit.end) ||
      edit.start < 0 || edit.end < edit.start || edit.end > text.length)
      throw new RangeError("source edit span is outside the source text");
    if (typeof edit.text !== "string") throw new TypeError("source edit text must be a string");
    if (edit.original !== undefined &&
      (typeof edit.original !== "string" || text.slice(edit.start, edit.end) !== edit.original))
      throw new Error("source edit original span does not match admitted source");
    if (edit.start < previousEnd) throw new RangeError("source edits overlap");
    previousEnd = edit.end;
  }
  let result = text;
  for (const edit of [...ordered].reverse())
    result = result.slice(0, edit.start) + edit.text + result.slice(edit.end);
  return result;
}
