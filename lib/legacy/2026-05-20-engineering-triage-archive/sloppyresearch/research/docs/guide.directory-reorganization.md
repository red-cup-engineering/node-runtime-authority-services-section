+++
id = "guide.directory-reorganization"
title = "Corpus Directory Reorganization (2025-11)"
status = "active"
document_type = "guide"
topics = ["corpus", "structure"]
+++


Purpose: document the post-reorganization layout so agents know where canonical papers and exploratory drafts live today. All prior references to `internal-theory/` are historical; do not add new files there.

## Current layout

```
research/
├── papers/                    # Canonical + near-canonical treatises
│   ├── discipline/
│   │   └── category-theory/
│   │       └── relationing/
│   │           ├── category-theory/
│   │           │   └── proposing-relationing/
│   │           │       ├── papers/proposing-relationing.md
│   │           │       └── movements/
│   │           └── infinity-topos/
│   │               ├── constructing-relational-infinity-topoi/
│   │               │   └── papers/constructing-relational-infinity-topoi.md
│   │               ├── relational-infinity-topos-modality/
│   │               │   └── papers/relational-infinity-topos-modality.md
│   │               └── stratified-directed-infinity-topos-geometry/
│   │                   └── papers/stratified-directed-infinity-topos-geometry.md
│   └── papers/
│       ├── formal-axioms-of-relationing.md
│       ├── foundations-of-relation.md
│       ├── relational-posets.md
│       └── composing-/proposing- exploratory pieces (status = active/exploratory)
│
├── notes/                     # Exploratory/archival notes and backlog
├── references/                # External sources, bibliography, transcripts
└── docs/                      # Planning and infrastructure documentation

txt/scientific-texts/
└── relations/                 # Historical or domain-specific drafts
    ├── sociology/
    ├── intelligence/
    └── other lanes as needed
```

`internal-theory/` has been retired. Any lingering files should be moved into `research/papers/` (if canonical) or `research/notes/` (if exploratory).

## Legacy moves (for reference)

| Legacy path (pre-2025) | Current location |
|------------------------|------------------|
| `internal-theory/proposing-a-reflexive-existence.md` | `research/discipline/mathematics/relationing/category-theory/formal-axioms-of-relationing/papers/formal-axioms-of-relationing.md` |
| `internal-theory/deriving-a-reflexive-infinity-topos.md` | `research/discipline/mathematics/relationing/infinity-topos/constructing-relational-infinity-topoi/papers/constructing-relational-infinity-topoi.md` |
| `internal-theory/relational-infinity-topos-modality.md` | `research/discipline/mathematics/relationing/infinity-topos/relational-infinity-topos-modality/papers/relational-infinity-topos-modality.md` |
| `internal-theory/introducing-stratified-directed-infinity-homotopy-geometry.md` | consolidated into `research/discipline/mathematics/relationing/infinity-topos/stratified-directed-infinity-topos-geometry/papers/stratified-directed-infinity-topos-geometry.md` |
| `internal-theory/foundations-of-relation.md` | `research/discipline/mathematics/relationing/category-theory/foundations-of-relation/papers/foundations-of-relation.md` |
| `internal-theory/relational-posets.md` | `research/discipline/mathematics/relationing/category-theory/relational-posets/papers/relational-posets.md` |

Exploratory drafts such as `composing-proposing-a-relational-existence.md` and `proposing-a-modality-of-relationing-existence.md` now live under `research/papers/` with explicit frontmatter (status `active`/`exploratory`).

## Guidance

- Canonical research belongs in `research/papers/` with full frontmatter and lineage fields (`cites_internal`, `depends_on`, `builds_on`, `supersedes`).
- Exploratory work should live in `research/notes/` (free-form) or `txt/scientific-texts/relations/<domain>/` if it needs to stay near the historical corpus. Promote to `research/papers/` once it gains proper frontmatter and lineage.
- Planning and infrastructure documents (like this reorg note) belong in `research/docs/`.
- Update `research/docs/plan.corpus-evaluation-matrix.md`, `research/docs/plan.consolidation-decisions.md`, and `research/docs/plan.deletion-consolidation.md` whenever files move so references stay accurate.

## Next steps

1. Audit git history for any remaining references to `internal-theory/` and either move or archive those files.
2. Ensure ingestion, lint, and publish scripts only target `research/papers/` and `txt/scientific-texts/`.
3. Whenever a paper changes status (draft → canonical) reflect that change in the frontmatter and update the planning docs accordingly.
