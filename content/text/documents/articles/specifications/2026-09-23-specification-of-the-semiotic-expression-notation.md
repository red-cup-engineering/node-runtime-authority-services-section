---
title: "Specification of the semiotic expression notation"
date-created: 2026-09-23
status: core stated from the 2026-06-18 reference and the Lean development; the implementation admits exactly the core and the four executable forms
part-of: computer-code-engineering-services-section
version: 0.1.0
stability: draft
authors:
  - emsenn
  - claude-fable-5-1
---

# Specification of the semiotic expression notation

The semiotic expression notation (SEN, formerly relation model notation, RMN)
is the house's one term language: a total, typed LISP carried over JSON. A
term is data, a frozen JSON array such as `["lam", ["var", 0]]`, never a
closure, so any body can be serialized, content-addressed, inspected and
replayed. Its statics are data and its dynamics are code:

- the grammar, the typing judgment and the JSON bridge live in
  `@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation`
  (with `/typing` and `/json-codec`), because a term, its type and the term of a
  JSON value are values that no evaluation produces;
- reduction, the reader, the named codec and the runtime live in
  `@red-cup-engineering/computer-code-engineering-services-section/semiotic-expression-notation/*`
  (`eval`, `reader`, `named-codec`, `runtime`).

## The core is the proved calculus

The term and type forms that the Lean development proves things about are
the core, and nothing is added to them without a law to answer to.

`Obsmetrologia/Language/Predicating/CurryHowardLambek.lean` defines

```text
Ty = base | arrow Ty Ty | prod Ty Ty | unit
Tm = var n | lam t | app t u | pair t u | fst t | snd t | star
```

with de Bruijn renaming and substitution, the typing relation `HasTy`, one-step
reduction (beta and the two projections, congruent everywhere) and
`church_rosser`: reduction is confluent, so a term's normal form, when it has
one, is unique. That uniqueness is what lets a normal form be an address.

## The executable language

SEN is the core plus exactly four executable forms and one type, as fixed by
the 2026-06-18 reference note on relation model notation:

```text
Ty = base | arrow Ty Ty | prod Ty Ty | unit | list Ty

Tm = var n | lam t | app t u | pair t u | fst t | snd t | star
   | mark s                opaque atom, type base; the only place a value enters
   | coincide l r          structural equality of two values, a truth-axis mark
   | cond test then else   branch on a truth-axis mark
   | fold f init list      left fold over a pair spine; the one recursion
```

A value is a `mark`, `star`, or a `pair` of values. A list is
array-encoded: `pair(mark(tag), spine)`, its spine a right-nested `pair`
chain ending in `star`. `fold` recurses over that spine, and `list T` is
the type of an array-encoded list whose spine holds only `T`. Consing onto a
list is `pair(fst xs, pair(h, snd xs))` (`tm.consArray`); the typer gives
that shape `list T` when `xs : list T` and `h : T`. `church_rosser` covers the seven core forms;
`mark`, `coincide`, `cond` and `fold` are executable extensions whose
reduction rules are local and deterministic, and the Lean side does not yet
range over them (the "mark : base" atom rule is research-grade).

A semiotic content address enters a term as a `mark` whose surface is the
address's `ni:` token. That is how SEN carries SCAs as terms: the token is
opaque, and the claim it commits to is read from the envelope it names, never
decoded from the mark.

## Everything else is a composition

These are functions of the grammar layer that build core terms. The reducer
has no case for any of them.

| operation | built from |
|---|---|
| FOUR charge values `unknown`, `held`, `denied`, `contested` | four distinguished `mark`s |
| `negate`, `conflate`, `joinK`, `meetK`, `joinT`, `meetT`, `leK`, `leT` | `cond`/`coincide` dispatch over the four charge marks (Lean's `Charge` operations case by case) |
| booleans | the truth axis of the charge encoding (`held`, `denied`) |
| `field` (named field of an object) | `fold` over the object's entry spine with `coincide` on keys |
| `consArray`, `reverseArray`, `append` | `pair` and `fold` |
| JSON values | the JSON bridge: `pair(mark(tag), payload)`, objects as sorted entry spines |

## Forms that are derived, not primitive

An earlier grammar (profile `org.emsenn.rmn.core.v3`) admitted forms the
core does not have. Each is now a composition in the core, built where it is
used; the reducer and typer have no case for any of them:

| v3 form | core derivation |
|---|---|
| `four t f` (type `charge`) | the charge `mark` named by its two bits, type `base` |
| `ascribe T t` | `t`; a type annotation is input to the checker. `["ascribe", T, t]` survives only as the conformance wire envelope, never inside a term |
| `left v T`, `right T v` (type `sum`) | a tagged pair `pair(mark(tag), v)`, typed by the branch it carries |
| `nil T`, `cons h t` (type `list`), `vector T [..]` | the array-encoded list (`typedListTerm`) and `tm.consArray` |
| `constant T ni` | `mark(ni)` |
| `predicate name A B` | `mark(name)` |
| `ground p s o`, `witness …` (types `grounded`, `wit`, `relation`) | the predication cell `pair(s, pair(mark(p), o))`; a WIT is `pair(cell, pair(before, pair(after, mark(evidence))))` with the two charges as marks, its one-cover law checked by the assay, not the grammar |
| `effect cell` (type `effect`) | the cell's JSON bridge term (`effectTerm`); a bundle is `pair(effectTerm(cell), operation)` typed by `effectBundleType` |

Removing these changed the normal form, and so the semantic identity, of every
term that used them. Identities already issued over v3 terms (pinned contract
addresses, circuit identities, published agent-card addresses) are content
addresses of those exact bytes and still verify as bytes; content re-issued
under the core receives a new address. A v3 envelope is never rewritten in
place.

## Layers around the notation

- Carrier bytes and the `ni:` token: the semiotic content address, in the data
  section (see its specification).
- Semantic identity of a typed claim: the typed envelope. Its law and JSON
  content identity are content's
  (`@red-cup-engineering/computer-content-engineering-services-section/semantic-content-identity`),
  because a JSON value's term is already normal and typed by inference; the
  identity of an arbitrary term, which must first be normalized, is the code
  runtime's (`semiotic-expression-notation/semantic-content-identity`).
- Readable path surfaces: semiotic resource names, which read to SEN terms.
