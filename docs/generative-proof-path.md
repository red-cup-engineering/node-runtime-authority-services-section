# Qualified generative proof paths

The existing Code SEN owner exports `./semiotic-expression-notation/proof-path`. This closes the boundary left explicit by Data's proof-path identity: canonical route spelling and matching endpoints do not establish generator edges.

`identifyFiniteGenerativeStructure({value,witnessRoot})` checks the raw finite structure before delegating identity to the original Data SEN envelope. `qualifyGenerativeProofPath({structureBytes,structureRoot,witnessBytes,witnessRoot})` reconstructs the committed structure and proof witness through Data, reproduces exact witness bytes, qualifies every declared edge, then checks every requested step. A transported result object is not a substitute for requalification of its committed carriers.

## Finite profile

A version1 structure has exactly `nodes`, `edges` and `predicateMaps` in addition to `version`. It admits1–256 named three-coordinate cells, at most1024 edges and256 finite predicate maps. Inputs are each bounded to1MiB. Node and map coordinates must be nonempty NFC strings; cells hold bounded strings. Duplicate or ambiguous coordinates, maps, predicate images and edge tuples refuse.

For a source cell `(s,p,o)`, the four actions are:

- converse: `(o,p,s)`
- subject-projection: `(s,p,s)`
- object-projection: `(o,p,o)`
- specialization by an explicit finite predicate function: `(s,f(p),o)`

The mapping from hyphenated Data route names to SEN subjectProjection/objectProjection marks is explicit. The Data reader owns canonical UTF-8 path decoding and its fixed library segment. Code supplies no second path grammar or content-addressing law.

## Unicode and evidence

Raw coordinate admission precedes SEN Unicode normalization. Qualification of a committed normal form cannot recover or reject the pre-normalization spelling that produced it. The tests distinguish these boundaries: raw decomposed coordinates refuse, while an independently admitted canonical normal form is checked as that normal form. Code does not normalize payload strings itself. Preserve original corpus bytes in the original Data byte-carrier envelope and retain source-derived RDF lexical readings separately.

The structure envelope and path witness retain their evidence roots. Qualification establishes structural consequences relative to that source material; it does not establish external corpus truth, OWL entailment or possession of a quantum witness. Distinct ordered routes retain distinct witness commitments even when interpretation reaches the same cell.

## Science and receiving

Science's QualifiedGeneratorRoutes proves category laws, Yoneda full faithfulness, restrictions and naturality for typed edge certificates. QualifiedRouteInterpretation proves composition and contravariant restriction for their interpretation. These parameterized Lean results do not prove digest injectivity or certify this JavaScript implementation by themselves.

Native receiving uses actual published Data0.7.2-dev.1405 commitments and grammar, all four actions, identity and multi-step routes, exact roots/bytes, Unicode, unused bad declarations and prototype-sensitive keys. It retains the85 existing SEN tests. Implementation came from bounded Nemotron source and native scoped CodeMission edits; unaccepted intermediate proposals and resource refusals remain in their original engineering records.
