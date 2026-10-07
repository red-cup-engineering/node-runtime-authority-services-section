++
id = "guide.research-discipline"
title = "Discipline Taxonomy"
status = "active"
document_type = "guide"
topics = ["research", "taxonomy"]
keywords = ["discipline-order", "schools", "concepts"]
++

# Research Discipline Layout

All non-foundation research now lives under `research/discipline/<discipline>/<school>/<concept>/`.

## Hierarchy

1. **Discipline** – the broad domain (e.g., `mathematics`, `media`, `climate`).
2. **School/Subdiscipline** – a tradition/program or narrower field (e.g., `relationing`, `category-theory`, `critical-media`).
3. **Concept** – the specific object of study (e.g., `proposing-relationing`, `relational-newsroom`, `infinity-topos`).
4. **Cells inside a concept** – `papers/`, `experiments/`, `notes/`, `movements/`, etc.

Only create the levels you need; if there is no school, place the concept directly under the discipline.

## Metadata Convention

Every Markdown file must set:

- `id`, `title`, `status`, `document_type`
- `disciplines`: ordered list where `disciplines[0]` = context/vocabulary, `disciplines[1]` = method, remaining entries = secondary fields
- `concept` (string) and `school` (optional) so the ingestor can reconstruct relationships

Example:

```toml
disciplines = ["media", "method.graph-analysis", "climate"]
school = "relationing"
concept = "relational-newsroom"
```

## Existing Concepts

- `mathematics / relationing / category-theory / relationing / proposing-relationing`
  - `papers/proposing-relationing.md` (legacy monolith)
  - `papers/introduction.md`, `papers/epilogue.md`
  - `movements/` – Movement I–V canonical sections
- `mathematics / relationing / infinity-topos / constructing-relational-infinity-topoi`
  - `papers/constructing-relational-infinity-topoi.md`
- `mathematics / relationing / infinity-topos / relational-infinity-topos-modality`
  - `papers/relational-infinity-topos-modality.md`
- `mathematics / relationing / infinity-topos / stratified-directed-infinity-topos-geometry`
  - `papers/stratified-directed-infinity-topos-geometry.md`

When adding a new discipline or concept, update this guide with a brief description so agents know where to contribute.
