# Bounded exact-source-edit operation body

Status: source specification and candidate implementation. This export is not
an installed or admitted Work operation, a source-write capability, or a receipt
of independent customer acceptance.

## Requirement and scope

The Group's native engineering requirement needs existing deterministic source
construction to enter the original typed Work path without a model carrier.
Code already owns `applyExactSourceEdits(text, edits, options)`. The addressed
JSNode operation dispatcher supplies one input object, followed by its ordinary
arguments/context. The required change is an object-input boundary around that
same primitive, not a second editor or inference service.

The [operation-backed Work LLD, section 5a](https://github.com/red-cup-engineering/agent-organization-engine/blob/f6de12f982f871ba1e597410d2f7d8dec559805a/lib/organizing/docs/specifications/typed-office-procedure.md)
owns the consuming byte/resource contract. This specification specializes it
at the Code provider. The [accepted Metrologic repair](https://github.com/red-cup-engineering/computer-data-engineering-services-section/pull/247)
is one historical source-construction example, not evidence of autonomous
diagnosis, a native Work proposal, or a production receiving act.

## Architecture and public interface

`@red-cup-engineering/computer-code-engineering-services-section/exact-source-edit-operation`
exports:

- `applyExactSourceEditOperation(input)`: the pure object-input body, returning
  only the resulting source string or throwing before delivery on refusal;
- `inputSchema`, `outputSchema`: closed boundary schemas;
- `effects`: the existing operation-family effect shape, with `class: "pure"`,
  `replay: "safe"`, `coordination: "coordination-free"`, `deterministic: true`,
  and `totality: "partial"`.

Partiality is intentional: byte identity, span agreement, overlap, scalar and
NFC conditions exceed the preliminary JSON schemas. Effects characterize this
qualified source path on its admitted input; they do not prove arbitrary
JavaScript pure or provide a sandbox.

The original positional primitive and public export remain unchanged. The body
imports only that primitive and the existing JSON canonical codec. Code does
not depend upward on Relating, register an operation, create a host callback,
or duplicate a descriptor/signature/dispatch mechanism. The existing higher
source-transform operation owner captures this exact body through the original
JSNode module-closure provider and passes the captured `program`, these schema
contracts and effects to the original operation constructor. Its normal
descriptor and typed Work signature identify the reached source and boundary.
Publication, source closure qualification, coherent dependency installation,
authority, dispatch and independent receiving remain separate gates.

## Detailed input and algorithm

Input has exactly `{text, edits, expectedSourceSha256}`. `edits` contains 1..128
records, each exactly `{start, end, text, original}`; every field is mandatory.
`expectedSourceSha256` is a lowercase 64-hex digest of the exact UTF-8 preimage.
`start` and `end` are nonnegative safe-integer UTF-16 code-unit offsets, not
Unicode character/grapheme or UTF-8 byte offsets.

1. Use `canonicalizeJson(input, JSON_RESOURCE_ENVELOPE)` from the original
   JSON provider to obtain an inert frozen copy before reading fields, hashing
   or encoding. Its envelope limits canonical input to 1 MiB, depth to 64,
   nodes to 100,000 and individual strings to 262,144 UTF-8 bytes. Accessors,
   non-JSON values and lone surrogates refuse. Source JSON byte admission is
   performed by the actual ingress before an object reaches this function.
2. Enforce closed fields, edit cardinality and mandatory digest syntax. Bound
   source, each original span and each replacement to 65,536 UTF-8 bytes.
   Require all of them already NFC-stable; never normalize source bytes.
   Schema `maxLength: 65536` is only a preliminary character bound.
3. Require both edit endpoints between Unicode scalar values. A position
   splitting an astral surrogate pair refuses. The original primitive retains
   its end-before-start, out-of-source, exact-original, stale-SHA, overlap and
   ambiguous-insertion guards.
4. Delegate exactly once to the unchanged `applyExactSourceEdits`.
5. Re-admit the resulting string through the strict JSON codec and require
   output within 65,536 UTF-8 bytes and already NFC-stable. Joining individually
   NFC-stable pieces can create a non-NFC boundary, so input checks alone are
   insufficient. Return only the string, without any file or journal effect.

This domain is intentionally narrower than the general primitive. Valid
non-NFC source, more edits, or larger source is unsupported by this operation,
not declared meaningless or impossible to edit.

The receiving/transport owner must decode source with fatal UTF-8 decoding,
preserve a leading BOM and compare re-encoded bytes to custody before hashing.
This string-input body performs no byte decoding. It preserves admitted BOM,
line endings and untouched bytes; it does not claim a lossy ingress can be
repaired after decoding.

## Qualification and acceptance

The focused native source tests import the new public package export through
ordinary package resolution and retain the original primitive suite. Cases
cover closed/missing fields, mandatory stale-byte and original-span guards,
overlap, insertions/deletions, 128 edits, UTF-16 astral positions and forbidden
split endpoints, lone surrogates in each input slot, non-NFC input and composed
output, multibyte byte limits, output overflow, canonical input budget, inert
JSON admission, and exact preservation of BOM/CRLF/untouched bytes.

These tests qualify the bounded source body with the exact dependency closure
used for that run. They do not establish the higher owner's captured descriptor,
frozen registry installation, private semantic assay availability, operating
authority, native Work admission or independent customer receiving. An existing
accepted artifact may supply an exact-delivery oracle only through the original
protected target custody and native proposal/receiving rules; the producer does
not choose its own acceptance.
