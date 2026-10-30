// The package-invariant catalog. Authoritative prose lives in
// dev/docs/explanations/package-invariants.md; this is the same catalog as
// data the checker and `ways list` run from. Findings are charges, not
// pass/fail (way 3): a violation under a law-allow annotation settles to
// stable — held, visible, not fatal.

export type Layer = "lib" | "apps" | "services" | "sites";

export type ChargeName = "potential" | "active" | "stable" | "absurd";

export type Severity = "error" | "warning" | "info";

export type Finding = Readonly<{
  invariant: string;
  charge: ChargeName;
  severity: Severity;
  message: string;
  evidence: readonly string[];
}>;

export type Invariant = Readonly<{
  id: string;
  way: string;
  severity: Severity;
  layers: readonly Layer[];
  claim: string;
}>;

const ALL: readonly Layer[] = ["lib", "apps", "services", "sites"];
const LIB: readonly Layer[] = ["lib"];

export const INVARIANTS: readonly Invariant[] = [
  { id: "M1", way: "the name is a morphism", severity: "error", layers: ALL,
    claim: "name is @561-group/<dir> (or @emsenn/<dir>) and matches the directory exactly" },
  { id: "M2", way: "programs are evidence", severity: "error", layers: ALL,
    claim: "type:module, private:true, sideEffects:false" },
  { id: "M3", way: "the name is a morphism", severity: "error", layers: ALL,
    claim: "exports map present with '.' and './package.json'; the map IS the boundary" },
  { id: "M4", way: "hygiene", severity: "error", layers: ALL,
    claim: "scripts include check and test (verify for lib)" },
  { id: "M5", way: "one descent, many worlds", severity: "warning", layers: ALL,
    claim: "workspace deps use workspace:*; external runtime deps in lib need human sign-off" },
  { id: "M6", way: "the name is a morphism", severity: "info", layers: ALL,
    claim: "domain packages parse as <thing>-<form>: lib/<thing>-topology | lib/<thing>-codecs[-<standard>], apps/<thing>-computer, services/<thing>-tics (trace information & computing service; memetics = meme-tics), with -wire/-room and kin as they are specced; utility packages may diverge with cause" },
  { id: "L1", way: "one descent, many worlds", severity: "error", layers: LIB,
    claim: "lib depends only on lib (no lib→service/app/site inversions)" },
  { id: "L2", way: "one descent, many worlds", severity: "error", layers: ["apps"],
    claim: "apps depend on lib only" },
  { id: "L3", way: "one descent, many worlds", severity: "error", layers: ["services", "sites"],
    claim: "services depend on lib + apps (a <thing>-tics is its <thing>-computer made available; the human, 2026-06-11); sites depend on lib + services" },
  { id: "L4", way: "one descent, many worlds", severity: "error", layers: LIB,
    claim: "codec packages (*-codecs*) have zero runtime dependencies" },
  { id: "L5", way: "one descent, many worlds", severity: "warning", layers: ALL,
    claim: "direct dependency count over 8 is the god-package smell" },
  { id: "S1", way: "time only accumulates", severity: "error", layers: ALL,
    claim: "no wall-clock as ordering (clockDefault guard)" },
  { id: "S2", way: "time only accumulates", severity: "error", layers: ALL,
    claim: "no destructive deletes; retraction is assertion (destructiveDelete guard)" },
  { id: "S3", way: "the name is a morphism", severity: "error", layers: ALL,
    claim: "no JSON.stringify as identity; canonical bytes only (stringifyIdentity guard)" },
  { id: "S4", way: "no witness, no world", severity: "error", layers: ALL,
    claim: "no ungated admission (ungatedAdmit guard)" },
  { id: "S5", way: "contradiction is load-bearing", severity: "warning", layers: ALL,
    claim: "no domain-outcome throws; exceptions are for malformed shapes only (domainThrow guard)" },
  { id: "S6", way: "time only accumulates", severity: "warning", layers: ["services"],
    claim: "no wall-clock interval as a service's primary tick; a tick is a witness-driven advance" },
  { id: "A1", way: "contradiction is load-bearing", severity: "error", layers: LIB,
    claim: "lib root exports no boolean-returning is*/has*/can* judgments; judgments carry witness or obstruction" },
  { id: "A3", way: "the name is a morphism", severity: "error", layers: ALL,
    claim: "kind strings are Three-Dots-and-a-Dash conformant (lowercase atoms joined by . : - ; _ only as declared escape)" },
  { id: "A4", way: "everything is a trace", severity: "warning", layers: LIB,
    claim: "carriers frozen; no exported mutable state" },
  { id: "D1", way: "documentation", severity: "warning", layers: ALL,
    claim: "README.md exists and is substantive (what it IS, contract, quick-start)" },
];

export function invariantsFor(layer: Layer): readonly Invariant[] {
  return INVARIANTS.filter((i) => i.layers.includes(layer));
}

export function finding(
  invariant: Invariant,
  charge: ChargeName,
  message: string,
  evidence: readonly string[] = [],
): Finding {
  return Object.freeze({
    invariant: invariant.id,
    charge,
    severity: invariant.severity,
    message,
    evidence: Object.freeze([...evidence]),
  });
}
