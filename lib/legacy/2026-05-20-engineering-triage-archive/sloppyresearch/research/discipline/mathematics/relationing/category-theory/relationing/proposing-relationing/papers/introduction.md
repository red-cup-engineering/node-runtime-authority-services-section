++
id = "proposing-relationing-introduction"
title = "Introduction — Why Relationing?"
status = "canonical"
document_type = "foundational_section"
topics = ["relationing", "foundations", "lakota-cosmogeny"]
disciplines = ["mathematics", "category-theory"]
concept = "proposing-relationing"
school = "relationing"
keywords = ["introduction", "motivation", "roadmap"]
+

Relationing is a program to formalize the Lakota insight that being is constituted by relation, not by atomized parts. This introduction explains why the treatise proceeds through five movements, what problems each solves, and how they bind technical work (category theory, ∞-topoi, dynamics) back to indigenous epistemology and contemporary research needs.

## Why a Relational Modality?

1. **Cultural Imperative** – Lakota cosmogeny models existence as continuous acts of differentiation and recognition. Relationing translates that worldview into precise operations so it can converse with present-day mathematics without being subsumed by it.
2. **Scientific Gap** – Contemporary logic and physics split structure (logic), stabilization (algebra/geometry), motion (dynamics), cohesion (topology), and measurement (physics). Relationing rethreads these as phases of a single modality so that “what exists,” “how it stabilizes,” and “how it moves” are co-specified.
3. **Pragmatic Need** – We apply the framework to research infrastructure: knowledge graphs, publish pipelines, educational curricula, and experiments. The treatise therefore doubles as both metaphysics and an engineering specification.

## Reading the Movements

| Movement | Focus | Questions Answered |
| --- | --- | --- |
| I. Logical Origination | Differentiation, recognition, inclusion/exclusion | How does being appear? How do regions of possibility relate? |
| II. Structural Stabilization | Closure/interior, balance, modal translation | How does coherence persist? How do necessity/possibility negotiate? |
| III. Directed Dynamics | Flow, residuation, arithmetic of processes | How does relation move without tearing coherence? |
| IV. Geometric Cohesion | Cohesive adjoints, stratification, ambidexterity | How do local observations aggregate into global invariants? |
| V. Relational Physics | States, observables, transport, action/symmetry | How does the logic map to measurable physics and experiment design? |

Each movement can be read independently, yet they are intended as a ladder. The Introduction anchors the ladder in cultural provenance and research use cases, while the Epilogue (now a standalone document) traces the implications for future disciplines.

## Working With This Corpus

- The movement manuscripts live in `movements/` and are graph-ingestable thanks to TOML frontmatter.
- Appendices are being promoted into their own concept files where appropriate (e.g., knowledge graph practice, cosmological readings).
- Publishing is a Relationing act: use `rrpr-relationing-filter` in Pandoc so scoped syntax survives, then run `rrpr publish docs ...` to build canonical bundles.

The remainder of Proposing Relationing should now be read as five connected but modular treatises. When citing, reference the movement IDs or this introduction’s ID (`proposing-relationing-introduction`) so the knowledge graph can recognize the section being invoked.
