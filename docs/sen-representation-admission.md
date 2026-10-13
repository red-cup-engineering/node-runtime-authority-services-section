# SEN representation admission

The existing public reader `parseSen(source)` parses JSON and requires a closed,
well-typed SEN term using `isClosed` and `inferTy`. It returns the original
unreduced term. Recognition alone is not admission: `senProjector.read(resource)`
actually invokes this parser. The projector remains a restriction of the JSON
projector, with type `sen` and corner `assertion`.

Its `strict` rung grades this finite syntax/type-checking operation. It does not
grade a subsequent evaluation of the term, prove that an omega-limit is reached
in finitely many steps, or promise a uniform time/memory bound. Deep or oversized
syntax may exhaust resources and refuse admission. `settleSen` and the evaluator
remain separate APIs. Current settleSen uses the existing runtime reducer with
a default budget of 10,000 accepted contractions (or an explicit nonnegative
integer fuel), and refuses with fuel-exceeded when a next contraction would
exceed it. HTML/session settlement applies that budget per term. This preserves
the current bounded settlement implementation, without a wall-clock/memory bound
per step, a guarantee of successful normalization, or a termination theorem.
The lower-level eval.normalize API remains separate and has no fuel argument.

The projector reads one term and writes its first item in the existing canonical
JSON plus newline form. Empty item lists retain the existing empty document.
Nonempty writes check the exact serialized document with `parseSen`; they cannot
label arbitrary JSON data as admitted SEN. The communicating adapter retains its
existing multi-item, newline-joined form without a final newline, checking each
emitted document. Its read still accepts one SEN document, not a JSONL stream.

The System Engine SEN wire inherits these checked read/write operations. Its
name and media type remain `sen` and `application/sen+json; charset=utf-8`, and
valid syntax crosses without reduction or changed canonical bytes. Selecting the
SEN wire for plain JSON now refuses; use the separate JSON wire for generic data.
No named caller requiring plain JSON under the SEN label was found in the
inspected constructor/RPC/catalog source. Runtime argv selection remains possible,
so this correction intentionally closes that formerly permissive behavior.

The generic wire admission predicate still delegates to the actual closure-regime
supplier. There is no Scott exception or decoder override that blesses a semantic
completing read. Correct strict-only `regimeDecidable` may therefore be adopted
without making SEN syntax transport depend on evaluator completion.

RPC input refusal occurs before invocation/witness/authority/handler admission.
Ordinary output encoding occurs after the handler and does not promise rollback.
Handlers needing pre-effect output validation must use the existing host-provided
result projection interface. This change does not introduce one or alter authority.
