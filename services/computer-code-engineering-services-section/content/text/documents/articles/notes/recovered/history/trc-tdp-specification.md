# TRC/TDP Specification

Status: first normative skeleton for the on-disk SPOTCOMP program/catalog
sub-specification.

TRC stands for **Typed Resource Catalog**. TDP stands for **Theory Derivation
Program**. In SPOTCOMP these are two readings of the same on-disk object: the
typed resource catalog is the running theory derivation program. SPOTCOMP is a
TRC/TDP when the catalog is shaped so its typed resources, traces, morphism
scripts, path identities, and closure rules are the executable proof tree.

## 1. Position In SPOTCOMP

PAM is the Predicate Algebra Modeling kernel: it supplies the predication
algebra and instruction surface. TRC/TDP is the on-disk running form of a
SPOTCOMP computer: it places types, trace evidence, and morphism witnesses in a
POSIX-shaped path category.

The handrolled source calls the program view TDP: category is program, a
program is a closure-rule set, execution is iteration of `Cl` to least fixed
point, and the trace is the execution log. The same source calls the memory
view TRC: typed resources with schemas, logs, scripts, dual filing, and
catalog replay. This specification treats those as one object, not two layers.

## 2. TRC Reading

The TRC reading says every managed resource is typed and addressable:

- a schema is the resource's type, proposition, and object witness;
- a trace log is the resource's fiber evidence;
- a morphism resource has a script witness for its closure-rule behavior;
- package import aliases bind canonical schema and script identities;
- path identity is categorical identity by the POSIX path-category/Yoneda
  reading;
- admitted trace rows are dually filed at subject and predicate anchors;
- value-position indexes are caches only.

A catalog that stores files without these witnesses is not yet a SPOTCOMP
TRC/TDP. A catalog that validates shapes but cannot replay trace evidence into
settling is also incomplete.

## 3. TDP Reading

The TDP reading says the catalog is an executable theory derivation program:

- resources are objects, predicates, and morphisms in the proof tree;
- scripts are morphism witnesses, not arbitrary host utilities;
- a closure-rule set is the program;
- execution repeatedly applies the declared closure operator to the trace
  frontier;
- a final result is the least fixed point or a declared non-final trajectory
  prefix under the active regime;
- the execution log is the trace, not an external debug artifact.

TDP therefore does not name a separate subsystem beside TRC. It is the running
view of the typed catalog when the catalog is used to derive, settle, and
replay theory.

## 4. Shared Object Laws

A conforming TRC/TDP profile MUST preserve all of the following:

- exactly one catalog root for local path resolution;
- POSIX-safe path segments or a declared identifier mapping;
- co-located schema/log witnesses for each resource;
- co-located script witnesses for morphism resources;
- declared monotonicity for morphism scripts;
- exact EAVT event rows after illocution;
- canonical row identity for dual filing and replay;
- append-only trace growth;
- replay from traces into working state;
- closure-rule execution through the declared settling regime;
- downgrade when fixed-point evidence is unavailable.

These are one set of laws. Splitting "program" from "catalog" is allowed only
as an explanatory projection, not as a mathematical separation.

## 5. Boundary To PAM

PAM and TRC/TDP are adjacent but distinct:

- PAM owns predication algebra, fiber parameters, instruction classes,
  reified messages, and witness geometry;
- TRC/TDP owns the on-disk path/category placement of schemas, traces,
  scripts, imports, dual filings, and replayable closure-rule programs.

PAM wavefront behavior may execute rules that live in TRC/TDP. TRC/TDP may
store and dispatch PAM-shaped morphism witnesses. Neither side may hide the
other's obligations. A host script is not a PAM instruction merely because it
is executable, and a PAM morphism is not a catalog resource until its
schema/log/script/path witnesses are declared.

## 6. Boundary To Other Sub-Specifications

SHP is a projection/packet surface produced from settled trace frontiers; it is
not the TRC/TDP object itself. Wire/federation transports signed traces,
profiles, or projections; it does not define the catalog. Operations records
processes, procedures, budgets, ledgers, and stationarity evidence around the
running catalog. Modeled-player and CGS specifications use TRC/TDP resources
as trace-governed local settling and strategy evidence, but player identity is
not reduced to catalog path identity.

## 7. Runtime Obligations

A TRC/TDP runtime MUST make the following phases explicit:

1. Resolve a typed resource through the catalog root and path category.
2. Validate input against the resource's schema witness.
3. Interpret the target as object, predicate, or morphism.
4. For morphisms, load the script witness through the declared import alias.
5. Execute only the declared morphism behavior.
6. Validate output when an output schema is declared.
7. Append resulting trace events to the required subject and predicate logs.
8. Replay or continue closure according to the active regime.
9. Report fixed point, trajectory prefix, or downgrade with evidence.

Bundling these phases in one command is permitted only when conformance
evidence names the component morphisms and preserves their boundaries.

## 8. Declaration Probe

[../../TRC-LAYOUT.md](../../TRC-LAYOUT.md),
[../../schema/trc-layout.schema.json](../../schema/trc-layout.schema.json),
[../../examples/trc-layout.json](../../examples/trc-layout.json), and
[../../src/trc-layout.mjs](../../src/trc-layout.mjs) are the current
declaration-level probe for this sub-specification.

The probe checks resource co-location, import aliases, morphism script
placement, monotonicity declarations, exact EAVT row shape, subject/predicate
dual filing, non-authoritative value indexes, and canonical row identity. It
does not inspect live POSIX files, prove path hom-functor equality, run schema
validation, prove behavioral monotonicity, execute closure, or prove
least-fixed-point settlement.

## 9. Non-Conformance Cases

A TRC/TDP profile is not conformant when:

- TDP is treated as a subsystem separate from TRC;
- SPOTCOMP is treated as an application layered over a generic catalog;
- schemas, logs, and scripts are not co-located or path-typed;
- scripts are host utilities without morphism witness obligations;
- rows have fields beyond exact EAVT without a proved refinement rule;
- value-position indexes are authoritative;
- dual filing loses canonical row identity;
- replay depends on hidden mutable working state;
- fixed-point claims lack closure/regime evidence.

## 10. Immediate Derivation Work

The next TRC/TDP pass needs:

- a full path-hom-functor proof for POSIX resource identity;
- a live catalog inspection checker beyond declaration profiles;
- behavioral monotonicity tests for morphism scripts;
- schema validation and output-validation contracts for script witnesses;
- exact replay law from dual-filed traces into PAM geometry;
- closure execution handoff into [../../CLOSURE-SETTLING.md](../../CLOSURE-SETTLING.md);
- relationship between TRC/TDP and token/claim/utterance ingress for outside
  systems and LLM-hosted handlers;
- relationship between TRC/TDP replay and proof-tree irresolution in
  [../../PROOF-TREE-IRRESOLUTION.md](../../PROOF-TREE-IRRESOLUTION.md).
