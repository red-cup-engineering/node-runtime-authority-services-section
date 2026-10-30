// @561-group/ways — the ways, enforced and midwifed.
//
// Objects: Invariant, Finding (a charge with evidence), CheckReport.
// Morphisms: checkPackage (judge a package; findings are charges, the
// linter never throws on domain outcomes), scaffold (packages born
// conformant; append-only), invariantsFor.
//
// Today the checks are manifest/regex-grade (hermetic, fast, fallible);
// the roadmap in dev/docs/explanations/package-invariants.md deepens them
// to type-aware and eventually to settled mathematical lawfulness. The
// charge-shaped findings are already the right type for that widening.

export { INVARIANTS, invariantsFor, finding } from "./invariants.ts";
export type { Invariant, Finding, ChargeName, Severity, Layer } from "./invariants.ts";
export { checkPackage, layerOf } from "./check.ts";
export type { CheckReport } from "./check.ts";
export { scaffold } from "./scaffold.ts";
export type { ScaffoldResult } from "./scaffold.ts";
