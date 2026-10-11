+++
# ===== IDENTITY =====
id = "composing-proposing-a-relational-existence"
title = "Composing Proposing a Relational Existence"
aliases = ["Relationing Composition Protocol"]

# ===== AUTHORIAL =====
authors = ["emsenn"]
date_created = "2025-11-09"
date_modified = "2025-11-10"
status = "active"

# ===== CLASSIFICATION =====
document_type = "style_guide"
topics = ["writing-protocol", "composition", "documentation"]
disciplines = ["meta-research"]

# ===== CITATIONS - INTERNAL =====
cites_internal = []
cited_by_internal = []

# ===== RELATIONAL METADATA =====
depends_on = []

# ===== NOTES =====
# Writing protocol for composing relationing papers. Independent documentation asset.
# Future consideration: Merge into research/docs/guide.corpus-style.md during documentation cleanup.

# ===== PUBLICATION =====
published = false
+++

# Function and Scope

This protocol standardizes how we compose sections of **Proposing a Relational Existence**.
Every section has two faces:

-   `Internal`: the minimal, constructive derivation inside our framework.
-   `External`: the precise correspondence to established results in adjacent fields.

A section is complete only when both faces are present and an `Interlock` statement
explicitly binds them.


# Initiating Composition (finding necessity)

Before you write, determine **why this section must exist**.

-   State the gap in one sentence: “We need `Boundary` to stabilize `Recognition`.”
-   Declare engaged fields and roles (write them in the PROPERTIES drawer):
    -   *Origin* (primary framing field),
    -   *Mirror* (closest analogue),
    -   *Contrast* (field we carefully differ from).
-   Require a working title in clause form:
    -   “Describing X …” (for lemma-level results)
    -   “Theorizing X …” (for theorem-level results)
-   Add a brief “Term plan”: list candidate formal terms you expect to use or coin.
    Each candidate appears as `Code` at first mention and every time thereafter.


# Internal Proof Construction

Write the internal face first. Keep it constructive and local.

-   Start with a single `Given` line using only already-established terms.
-   Proceed with short steps that each change **one** thing:
    -   “Since `Includes` is reflexive, …”
    -   “Applying `Iterate` once yields …”
-   End with a closure line that shows stabilization or exact sufficiency.
-   If you need a displayed formula, use LaTeX blocks. Otherwise keep math inline.
-   Never reference authors or external terms in the internal face.


# External Proof Construction

Now anchor the same claim in outside literature with **specific** results.

-   Use *italics* for external terminology and name exact results:
    “See *Heyting implication* (e.g., Johnstone 2002, Prop. 1.2.10).”
-   Quote the result designation precisely (Theorem, Lemma, Proposition) and include a locator
    (book/section number, proposition number, page).
-   If you include a foreign formula, embed it as LaTeX and label it with a short,
    descriptive tag in prose (“residuation law, set-theoretic model”).
-   State scope alignment explicitly:
    -   “Our `Induces` coincides with *residuation* on frames under finite meets.”
    -   “Our `Flow` is a KZ-comonad; correspondence follows the *Kock–Zöberlein* condition.”


# Interlock and Verification

Every section must end with an `Interlock` statement that binds the two faces.

-   One sentence pattern: “=Claim= holds internally by Steps A–C and externally by
    Result R; the two coincide on domain D stated above.”
-   If they do not coincide fully, write a boundary sentence:
    “Externally stronger; internally we require only monotone `Close`; see
    ‘Describing Monotone Closure’.”
-   Add a minimal checklist:
    -   Internal steps are constructive and closed.
    -   External references are specific and sufficient.
    -   Domain and hypotheses match.


# Sentence Logic and Connectors

Keep sentences short. Prefer plain connectors.

-   Causal: “because,” “since.”
-   Step: “then,” “hence,” “therefore.”
-   Guard: “when,” “whenever,” “if.”
-   Disallow rhetorical patterns like “To X is to Y.” Write “Xing is Ying.”


# Cross-referencing and Integration

Cross-references use titles, not numbers.

-   In prose, cite by title:
    “See ‘Describing Boundary Formation’ for re-entry of `Boundary` within `Field`.”
-   When cross-referencing, specify face if needed:
    “See the external face of ‘Theorizing Residuation’.”


# External Correspondence Discipline

No vague author-name drops. Always nail a result.

-   Cite precise items: “Lawvere 1969, Thm. 2,” “Johnstone 2002, Lem. A1.2.10,”
    “Kock–Zöberlein 1970s condition as formulated in Street 1972, §3.”
-   If a result is folklore, name a printed source that states it explicitly.
-   If your claim is weaker/stronger, say how:
    -   “Stronger: we require idempotence only on fixed locus.”
    -   “Weaker: we drop distributivity; compare Johnstone 2002, §I.2.”


# Mathematical and Visual Form (Tufte in Org-mode)

Follow Tufte-style clarity with Org-mode primitives only.

-   One idea per paragraph. Keep paragraphs short.
-   Use footnotes for margin-style notes and source asides; keep them terse.
-   Only figures are formulas too large for inline; embed as LaTeX blocks.
-   Avoid tables entirely; use lists and clear prose.
-   Use scare quotes rarely; emphasize semantics by `Code` for formal terms and *italics* for external terms.


# Extraction and Machine Legibility

Write so a program can extract structure from text.

-   Mark formal terms consistently with `Code` every time.
-   Use the scaffold headings and keep the “Given/Therefore/Hence/Interlock” markers literal.
-   Keep external citations in a predictable inline pattern:
    “(Author Year, Thm./Lemma/Prop. N, page M if needed)”.
-   Prefer one displayed formula per block; avoid multi-page derivations in one block.


# Revision and Coherence Maintenance

When you revise a section:

-   Re-run the internal closure: does the constructive chain still close?
-   Re-check external alignment: are all cited results still the exact ones we rely on?
-   Re-state the `Interlock` if scope changed.
-   Update cross-references by `CUSTOM_ID`, not by title text, then keep the title unchanged
    unless you also update all incoming links.


# Layout and Export

-   Headings are clause titles (“Describing …”, “Theorizing …”).
-   No numbering schemes (no “Lurie-numbering” mimicry).
-   Keep lines short enough to print comfortably.
-   Export math as LaTeX; keep everything else plain.


# Protocol Evolution

When you need a new compositional move, add it here by writing a small `Describing …` and
`Theorizing …` pair that justifies the move itself, then use it.


# Templates (copy-paste scaffolds)


## Section Skeleton (fill every field)


### Describing X (internal face)

Given: …
Therefore: …
Hence: …
Interlock: “=X= holds internally under … and externally under …; domains coincide on …”


### Theorizing X (external face)

We use *…term…* as in (Author Year, Thm. …).  
Statement: …  
Scope: …  
Fit: “Our `X` coincides with *…* under …; differs when …”


## Micro-Scaffold: Internal Lemma


### Describing Boundary Formation

Given: `Differentiate` establishes a two-sided mark.
Therefore: `Includes` is reflexive and `Excludes` is irreflexive and symmetric.
Hence: the `Field` has a reflexive order with incompatibility.
Interlock: matches *form of distinction* (Spencer-Brown 1969, ch. 2) and order/incompatibility
as in (Johnstone 2002, §I.2), restricted to our reflexive field.


## Micro-Scaffold: External Theorem Tie-in


### Theorizing Residuation over Together

We align `Induces` with *residuation*:
(Johnstone 2002, Prop. 1.2.10).  
Statement: “=Includes(Together(a,b),c)= iff `Includes(a,Induces(b,c))`.”  
Scope: frames with finite meets; distributivity used only to move `Together` through closure.  
Fit: coincides on the fixed locus of `Close`; see ‘Describing Fixed Locus’.


## Formula Block Example


## Cross-reference Example

See ‘Describing Boundary Formation’ for the re-entry of `Boundary` within `Field`.


# Term Discovery Rules (how we find and fix vocabulary)

-   Start from necessity: define only when a proof step forces a name.
-   Prefer existing field terms; if you coin, add a one-line crosswalk:
    “=Flow= corresponds to *KZ-comonad* under …”
-   Keep scope tight: if a term’s meaning would broaden, create a new section that proves the broadened form; do not silently drift the old usage.
-   Use the term in `Code` every time, exactly as spelled at its first introduction.


# Tonal Anchors (how they shape style, not content)

-   Shannon: favor minimal statements that carry just enough information to advance the proof.
-   Lurie: adopt structural care and adjoint thinking, but keep our own titling and avoid his numbering schemes.
-   Tufte: ruthless clarity; small, well-placed footnotes; zero ornamental prose.


# Acceptance Checklist (run before you commit a section)

-   Title is a clause: “Describing …” or “Theorizing …”.
-   All formal terms are in `Code`.
-   Internal face closes constructively.
-   External face cites specific results with locators.
-   Interlock statement present and correct.
-   Cross-references use `CUSTOM_ID` links and title text.
-   No tables; only formulas as figures; italics only for external terminology.
