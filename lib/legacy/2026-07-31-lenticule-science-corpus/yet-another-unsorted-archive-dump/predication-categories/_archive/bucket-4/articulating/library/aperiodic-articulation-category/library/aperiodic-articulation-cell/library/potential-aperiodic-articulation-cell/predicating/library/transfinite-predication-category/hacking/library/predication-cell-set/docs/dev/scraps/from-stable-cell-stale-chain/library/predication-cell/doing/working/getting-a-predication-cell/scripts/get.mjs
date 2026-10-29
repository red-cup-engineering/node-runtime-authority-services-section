// Returns a predication cell — the oriented triple (subject, predicate, object) — given
// its coordinates. A predication cell IS its three coordinates; there is no further
// substance to it as a mathematical object. This script validates that the inputs are
// well-formed (kebab-case slugs for subject and predicate; slug or literal for object)
// and returns the cell.
//
// What this script does NOT do, by mathematical necessity:
//
// - It does not read the substrate. The cell's identity is fixed by its coordinates;
//   substrate state has nothing to do with whether (s, p, o) is the cell (s, p, o).
// - It does not compute a value. The cell's value at any valuation lives in the
//   predication fiber algebra A_p, not in the cell. Getting the value is a different
//   operation (evaluating-against-a-valuation), on a different transformer, requiring
//   apparatus not yet earned at the substrate.
// - It does not attach provenance. Source-records and witnesses are not part of the cell;
//   they belong to a separate (also not-yet-earned) witness apparatus.

const SLUG_RE = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/;

function validateArgs(args) {
  for (const key of ["subject", "predicate"]) {
    if (typeof args[key] !== "string" || !SLUG_RE.test(args[key])) {
      throw new Error(
        `argument '${key}' must be a kebab-case slug (lowercase ASCII letters, digits, hyphens; no leading or trailing hyphen)`
      );
    }
  }
  if (args.object === undefined) {
    throw new Error("argument 'object' is required");
  }
  // object may be a kebab-case slug or a literal value of any JSON type admissible to
  // the predicate's codomain. Codomain-typing is the predicate's concern, not this
  // script's; we accept any non-undefined JSON value.
}

export default async function (args) {
  validateArgs(args);
  const { subject, predicate, object } = args;
  return { subject, predicate, object };
}
