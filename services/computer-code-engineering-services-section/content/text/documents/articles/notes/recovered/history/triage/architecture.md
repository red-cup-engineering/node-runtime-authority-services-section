# architecture — prose under a categorical lens

The converged design for a next-generation prose linter built on the voidmath
kernel. This is a **design document**: it records decisions we reached by talking
through Vale and the kernel, not facts derived from the repo. Where it cites the
kernel, the facts are in `voidmath-notes.md`; where it cites the rule corpus, the
material is in `sources/`. Reads it states as design are design.

Goal stated plainly: do Vale-style prose linting, but represent the text as a
category and run the kernel's descent over it — so rule-implication, rule-conflict,
and "I'm not sure here" come from the math instead of being faked.

## The decision: delimiter-first, parser-later, same base
We do **not** build natural-language understanding. We build "language articulation
parsing": derive the text's structure from its **delimiters** (spaces, periods,
newlines, commas), not from a trained model. This is chosen, not settled-for:

- It is **rederivable from the ground up** — total, mechanical, zero-dependency,
  the kind of floor the kernel was built to sit on. A statistical parser is none of
  those.
- We have to segment on punctuation **anyway** before any linter does anything, so
  none of this work is throwaway.
- A parser is **not excluded** — it is additive later. A tagger/parser, if we ever
  add one, just hangs more predicates (`is-subject`, `agrees-with`) over the **same**
  `after`/`inside` base. The delimiter layer is the foundation, not scaffolding.

## The two relations — everything rests on these
The base carries exactly two structural relations, both computable from delimiters:

- **after** — sequence within a tier. "This word follows that word." Its converse is
  `before`.
- **inside** — containment across tiers. "This word is inside this clause inside this
  sentence." Its converse is `contains`.

These populate the kernel base's relational slots directly: `subject-projection` and
`object-projection` are the two endpoints of an edge; `converse` is the reverse arc
(`predicate.mjs` already carries these fields — empty for one utterance, filled here).

## Tiers are fold-depths
The delimiter ladder (see `delimiter-ladder.md`) segments coarse-to-fine: document →
block → sentence → clause → word. Each tier is a **fold-level** of the kernel's
descent. This gives the fold-tower a concrete meaning it lacked before:

- `articulate` the document → blocks.
- A block that stays `⊥` (a check could not settle on it) **re-articulates** → sentences.
- A sentence still `⊥` → clauses. A clause → words.

So "deeper" = "one delimiter level finer." Progressive disclosure of analysis =
progressive segmentation. The nested posix path = the tier = the fold-depth — one
number. Cheap checks settle at coarse tiers (the LFP terminates fast); only the
genuinely ambiguous residue descends to finer, costlier tiers.

## The shape: a sheaf over a 2D base (the "3D map")
The base is a 2D floor-plan of the prose; the evidence fibers stand up over it:

- **X — reading position:** the `after`-chain, left to right.
- **Y — nesting depth:** the `inside`-tree, document at top, words at bottom.
- **Z — the fiber:** the thick charge over each `(position, depth)` cell — the
  evidence and the verdict.

Each structural predicate (`after`, `inside`, `starts-sentence`, `is-capitalized`,
`precedes-vowel-word`, `repeats-earlier-surface-form`, …) is its own **fiber-algebra**
(one per predicate, per the kernel). The fibers are **thick**: a charge's witness
carries the actual span — characters and `[start, end)` offsets into the source — not
a bare presence bit. That is what lets a diagnostic point back at the exact text.

## What this keeps and loses vs. Vale
`[design read]` Delimiter-only covers most of Vale's check taxonomy (see
`proposed-mapping.md` and the taxonomy walk-through): existence, substitution,
repetition, spelling, capitalization, occurrence (as clause/word counts), conditional
(positional search), readability (counts + a new fold-depth metric), and even `a`/`an`
(via `precedes-vowel-word`, pure adjacency). It **loses** only the checks that need a
word's grammatical role: true subject–verb agreement, split-infinitive detection.
Those re-enter later as predicates over the same base if a tagger is added. Clean 80/20.

## Layering (separation of concerns)
1. **Articulator (the ladder).** Text → the 2D base of spans with `after`/`inside`
   edges and offsets. Pure structure. No charges. (`delimiter-ladder.md`.)
2. **Detectors.** Per-predicate functions `span → charge-slot`, carrying thick
   witnesses. The rule corpus in `sources/` compiles into these.
3. **Descent.** Feed utterances + base to the kernel; get the settled sheaf;
   `⊥`-residue drives the fold to the next tier.
4. **Verdict / render.** Sheaf → diagnostics, including `⊤` (rules conflict, send to
   a human); severity from the bilattice position; document pass/fail via the truth axis.

This document fixes layer 1's design. Layers 2–4 are sketched in `proposed-mapping.md`
and remain to be specified.
