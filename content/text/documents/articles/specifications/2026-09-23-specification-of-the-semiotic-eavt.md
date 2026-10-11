---
title: "Specification of the semiotic EAVT"
date-created: 2026-09-23
status: realized; the semiotic-eavt modules of the code section
part-of: computer-code-engineering-services-section
version: 0.1.0
stability: draft
authors:
  - emsenn
  - claude-fable-5-1
---

# Specification of the semiotic EAVT

A semiotic EAVT (SEAVT) row is an EAVT row `{e, a, v, t}` whose entity,
attribute and value are each a closed, well-typed term of the semiotic
expression notation, and whose `t` is the time it was witnessed. The semiotic
content address names content, the notation relates it, and SEAVT temporalizes
it: together they are the carrier metrologic settles over.

SEAVT is plain EAVT underneath: rows are JSONL lines in dated journals
(`data/logs/YYYY/MM/DD/<feed>.jsonl`), written and read by the EAVT section.
SEAVT adds only the admission that e, a and v are notation terms, which is why
it lives in the code section beside the notation
(`@red-cup-engineering/computer-code-engineering-services-section/semiotic-eavt/*`)
and depends downward on EAVT in the data section.

## Rows

- `seavtRow({e, a, v, t})` admits a row; `normalizeSeavtRow` normalizes then admits.
- `seavt(e, a, v, t)` builds a row from notation terms.
- `seavtOfJson(entity, attribute, value, time)` builds a row from JSON
  coordinates through the notation's JSON bridge, for a boundary that
  receives plain JSON.

## Journals

- `appendSeavtEntries({root, feed, entries, at})` admits and appends rows.
- `readSeavtEntries({root, feed, at})` and `readSeavtEntriesAtPath({path})`
  read and admit rows. A reader that must accept journals written before
  admission existed reads them with the EAVT journal reader instead.

## Semantic records

`createSemanticRecordJournal({root, objectKind})` binds a custody root and
default object kind; its `record` and `query` are
`recordSemanticRecord` and `querySemanticRecords` with those filled in.

## Operations

Each operation is implemented in its named module of `src/semiotic-eavt/`, with exported input/output schemas and a command face accepting one JSON value on stdin.

| Effect | Script |
| --- | --- |
| Admit semantic coordinates | `admit-seavt-row.mjs`, `normalize-seavt-row.mjs` |
| Append or read dated journals | `append-seavt-entries.mjs`, `read-seavt-entries.mjs` |
| Read a named journal file | `read-seavt-entries-at-path.mjs` |
| Record and query semantic content | `record-semantic-record.mjs`, `query-semantic-records.mjs` |
| Validate a domain record before recording | `admit-semantic-record.mjs` |
| Bind JSON parameters and record a configured request | `bind-json-template.mjs`, `record-configured-semantic-record.mjs` |
| Check references and responses | `check-semantic-record-references.mjs`, `check-semantic-record-responses.mjs` |
| Inventory and replay historical record stores | `inventory-semantic-record-retirement.mjs`, `replay-semantic-record-retirement.mjs` |

Recording takes `{root, objectKind, category, record, recordedAt, charge, relation?}`. `charge` contains independent `support` and `refutation` booleans. The record receives its semantic-content identity, and the journal stores RMN coordinates. Querying by `{root, objectKind, category}` verifies those identities before returning content.

Template binding takes `{template, parameters}` and replaces a sole `{$pointer:"/path"}` object with the referenced parameter value. Missing pointers refuse the request. Domain admission checks the supplied JSON Schema before any journal write.

Retirement preserves original bytes and records which historical rows can be admitted; a replay does not turn missing source evidence into accepted semantic content.
