/** Apply validated non-overlapping edits from right to left. All code units outside
 * the approved spans survive exactly, unlike a whole-file pretty-printer. */
export function applyExactSourceEdits(text, edits) {
  if (typeof text !== "string") throw new TypeError("source text must be a string");
  const ordered = [...edits].sort((left, right) => left.start - right.start || left.end - right.end);
  let previousEnd = 0;
  for (const edit of ordered) {
    if (!Number.isSafeInteger(edit.start) || !Number.isSafeInteger(edit.end) || edit.start < 0 || edit.end < edit.start || edit.end > text.length) throw new RangeError("source edit span is outside the source text");
    if (typeof edit.text !== "string") throw new TypeError("source edit text must be a string");
    if (edit.start < previousEnd) throw new RangeError("source edits overlap");
    previousEnd = edit.end;
  }
  let result = text;
  for (const edit of [...ordered].reverse()) result = result.slice(0, edit.start) + edit.text + result.slice(edit.end);
  return result;
}

