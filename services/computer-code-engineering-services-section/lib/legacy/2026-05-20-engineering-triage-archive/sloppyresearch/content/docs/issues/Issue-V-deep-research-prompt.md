++
id = "issue.V"
title = "Integrate universal deep research refinement prompt"
status = "open"
priority = "p3"
area = "authoring"
document_type = "issue"
topics = ["authoring", "guides"]
created = "2025-11-10"
owner = ""
++

Context
- A “Universal Deep Research Refinement Protocol” prompt was authored to help agents expand manuscripts into rigorous, publishable treatises following Relationing principles (existence → differentiation → relation → reflexive stability).
- The prompt encodes relational logic (recognition category, morphisms, closure/interior, reflexive stability) and could live in `content/docs/dev-guides/` or templates once formalized.
- We need to decide how to store, reference, and operationalize this prompt (e.g., as a dev guide, CLI helper, or AI-facing instructions).

Prompt (draft)
```
# 🧭 Universal Deep Research Refinement Protocol
*A Relational-Modal Framework for Manuscript Expansion and Formalization*

## Purpose

To transform any manuscript—mathematical, philosophical, scientific, or artistic—into a complete, rigorous, and publishable treatise through a relational refinement process.  
The method integrates formal reasoning, stylistic synthesis, and contextual fidelity, modeled on the Relationing framework: existence → differentiation → relation → reflexive stability.

The agent applies this protocol to parse, prove, recurse, and validate, building a LaTeX-ready manuscript with proofs, commentary, and Tufte-style figures.

## 1. Relational Foundations (Epistemic Grammar)

Every domain expresses its own relational logic. The following meta-structure guides reconstruction:

- **Category of recognitions (𝓡):** the manuscript’s conceptual field.
- **Objects:** concepts, definitions, entities.  
- **Morphisms:** their relations (causal, inferential, formal, symbolic).  
- **Order:** a ≤ b means “a contributes to b.”  
- **Meets and joins (∧, ∨):** conjunctions and disjunctions of ideas.  
- **Implication operator (Induce):**  
  `Induce(a, b) = max {x | a ∧ x ≤ b}` — the most general idea x making a sufficient for b.  
- **Closure / Interior:** represent containment and openness in argumentation:
  - Closure: c(A) expands A to its full consequences.  
  - Interior: O(A) isolates A’s coherent core.  
  - Balance: the reflective equilibrium between containment and openness.  
- **Flow:** reflexive revision across drafts or claims. Generalized from  
  `Flow(x) = O(C(x)) ∧ C(O(x))`, the composition of testing and consolidation.  
- **Fixed point:** stability condition — when iterative refinement produces no further change.  
- **Reflexive stability:** the manuscript’s self-consistency when subjected to self-application.

These serve as abstract procedural analogues for any discipline:
- In philosophy → distinctions, concepts, syntheses.  
- In mathematics → sets, functions, morphisms.  
- In art → motifs, transformations, resonances.  
- In code or engineering → states, operations, recursion.
```

Acceptance
- [ ] Decide where this prompt should live (e.g., `content/docs/dev-guides/deep-research-protocol.md`, templates, or other guidance).
- [ ] Integrate/format the prompt with TOML frontmatter so ingestion tools can read it.
- [ ] Reference the finalized prompt from relevant authoring guides or issues (Issue-K, doc templates).

Links
- content/relationing/research/methods/paper-authoring/relational-research-paper-specification.md
- docs/for-agents/issues/Issue-K-agent-authoring-guidance.md
