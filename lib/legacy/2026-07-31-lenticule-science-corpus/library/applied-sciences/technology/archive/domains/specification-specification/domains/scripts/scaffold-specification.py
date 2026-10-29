#!/usr/bin/env python3
"""Scaffold a new specification directory and index.md.

Usage:
    python scaffold-specification.py SPEC_ID [--category FORMAT|CONVENTION] [--title TITLE]

Creates:
    technology/specifications/{SPEC_ID}/index.md

The generated index.md includes all sections required by
specification-specification (A.1-A.10 normative scaffold) with TODO
markers. This eliminates the need for agents to read
specification-specification each time they write a specification.

Convention specifications may omit A.2, A.7, A.9 per
specification-specification §0.
"""

import argparse
import os
import sys
from datetime import date


CONVENTION_TEMPLATE = """\
---
title: "{title}"
date-created: {date}T00:00:00
authors:
  - emsenn
  - claude
type: specification
spec-id: {spec_id}
version: 0.1.0
stability: draft
tags:
  - Specification
  - TODO-add-tags
description: "TODO: one-sentence description of what this specification defines."
requires:
  - ../specification-specification/index.md
part-of: technology/specifications
---

TODO: opening paragraph — what this specification defines, in 1-3
sentences. State what category it is.

This is a **convention specification** (per specification-specification §0).
Conformance scaffold per specification-specification A.1-A.10
(A.2, A.7, A.9 omitted — convention specs).

## 0. Scope

TODO: what this specification applies to. Be concrete — name the
directories, file types, or practices it governs.

## 1. What {spec_id} is

TODO: define the core concept. What is it? Why does it exist? What
problem does it solve? Keep this to 2-4 paragraphs.

## 2. TODO-section-name

TODO: the specification's main normative content. Use numbered rules
with MUST/SHOULD/MAY (per RFC 2119). Prefer tables and lists over
prose. Each rule should be independently testable.

Per A.10: each MUST/SHOULD/MAY is normative and test-mapped.

## 3. TODO-section-name

TODO: additional normative sections as needed. Each section should
cover one coherent aspect of the specification.

## 4. Error semantics

<!-- specification-specification A.3 -->

TODO: define what constitutes a violation and at what severity
(error vs. warning). Define error classes relevant to this spec.
Ambiguities MUST be treated as errors.

Error schema fields (per A.3): code, name, severity, where, when,
fault, retryable, data.

## 5. Conformance

<!-- specification-specification A.4 -->

TODO: provide a conformance matrix listing each normative
MUST/SHOULD/MAY and the actor(s) it binds.

| ID | Statement | Actor | Level | Test |
|----|-----------|-------|-------|------|
| C1 | TODO | TODO | MUST | TODO |

## 6. Upgrade path

<!-- specification-specification A.5 -->

TODO: define deprecation process and migration guidance.

## 7. Registries

<!-- specification-specification A.8 -->

TODO: if extension points exist, define registration policy.
Otherwise state "No registries defined."

## Glossary

<!-- specification-specification A.10 -->

TODO: define every term used normatively in this specification.
Format as a bulleted list:

- **Term**: definition

## Rationale (non-normative)

TODO: explain design decisions. Why these rules and not others?
What existing practice does this codify? Keep it concise.

## Relationship to other specs

- **Requires**: [specification-specification](../specification-specification/index.md).
- TODO: add other relationships (extends, informed-by).
"""

FORMAT_TEMPLATE = """\
---
title: "{title}"
date-created: {date}T00:00:00
authors:
  - emsenn
  - claude
type: specification
spec-id: {spec_id}
version: 0.1.0
stability: draft
tags:
  - Specification
  - TODO-add-tags
description: "TODO: one-sentence description of what this specification defines."
requires:
  - ../specification-specification/index.md
part-of: technology/specifications
---

TODO: opening paragraph — what this specification defines, in 1-3
sentences. State what category it is.

This is a **format specification** (per specification-specification §0).
Full conformance scaffold per specification-specification A.1-A.10.

## 0. Scope

TODO: what this specification applies to. Be concrete — name the
file types, data formats, or wire protocols it governs.

## 1. What {spec_id} is

TODO: define the core concept. What is it? Why does it exist?

## 2. TODO-section-name

TODO: main normative content. Use MUST/SHOULD/MAY (per RFC 2119).

Per A.10: each MUST/SHOULD/MAY is normative and test-mapped.

## 3. Canonicalization

<!-- specification-specification A.2 -->

TODO: define CANON(x) -> bytes. Specify:
- Field ordering and omission rules
- String normalization (Unicode NFC), whitespace, number formatting
- Deterministic map/dict ordering
- Binary encoding and endianness

The reference function MUST be testable with golden vectors.

## 4. Error semantics

<!-- specification-specification A.3 -->

TODO: define error classes with a stable schema.

Error schema fields (per A.3):
- `code` (stable, machine-readable), `name`
- `severity` in {{info, warn, error, fatal}}
- `where` (component/module), `when` (UTC timestamp)
- `correlation-id`, `fault` (producer/consumer)
- `retryable` (bool), `data` (opaque)

Error classes: Input/validation, Canonicalization, Version/feature,
State/consistency, I/O/transport, Security/authz.

Each algorithm step MUST specify which errors it can emit.
Ambiguities MUST be errors (not "unspecified behavior").

## 5. Conformance

<!-- specification-specification A.4 -->

TODO: provide a conformance matrix.

| ID | Statement | Actor | Level | Test |
|----|-----------|-------|-------|------|
| C1 | TODO | TODO | MUST | TODO |

Implementations MUST declare a conformance-profile referencing
matrix rows and test IDs.

Publish an executable conformance suite with: golden inputs/outputs,
negative cases, fuzz corpus seeds, determinism checks.

## 6. Upgrade path

<!-- specification-specification A.5 -->

TODO: define deprecation windows (announcement → dual-stack →
removal) and migration tools with idempotency guarantees.

## 7. Security and privacy

<!-- specification-specification A.6 -->

TODO: enumerate attacker models and trust boundaries.
State confidentiality/integrity expectations.
Specify required mitigations (authn/authz, replay protection,
input limits, timing channels).
Define data retention and minimization requirements.

## 8. Determinism

<!-- specification-specification A.7 -->

TODO: all observable outputs for the same canonical inputs MUST be
bit-for-bit identical across conforming implementations.
Randomness MUST be explicitly parameterized and seeded via inputs.

## 9. Registries

<!-- specification-specification A.8 -->

TODO: if extension points exist, define registration policy, review
process, collision handling, and permanence. Each entry MUST include:
identifier, status, spec reference, and security notes.

## 10. Formal artifacts

<!-- specification-specification A.9 -->

TODO: provide machine-readable schemas (JSON Schema/ASN.1/IDL) and
reference TCK hooks. Include pseudo-code that is executable or
trivially transpilable.

## Glossary

<!-- specification-specification A.10 -->

TODO: define every term used normatively.

- **Term**: definition

## Rationale (non-normative)

TODO: explain design decisions.

## Relationship to other specs

- **Requires**: [specification-specification](../specification-specification/index.md).
- TODO: add other relationships.
"""


def spec_id_to_title(spec_id: str) -> str:
    """Convert kebab-case spec-id to Title Case."""
    return spec_id.replace("-", " ").title()


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new specification per specification-specification."
    )
    parser.add_argument("spec_id", help="Spec identifier (kebab-case, e.g. my-specification)")
    parser.add_argument(
        "--category",
        choices=["format", "convention"],
        default="convention",
        help="Specification category (default: convention)",
    )
    parser.add_argument("--title", help="Human-readable title (derived from spec-id if omitted)")
    parser.add_argument(
        "--base-dir",
        default="technology/specifications",
        help="Base directory for specifications (relative to cwd)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing")

    args = parser.parse_args()

    title = args.title or spec_id_to_title(args.spec_id)
    today = date.today().isoformat()

    template = FORMAT_TEMPLATE if args.category == "format" else CONVENTION_TEMPLATE
    content = template.format(
        title=title,
        date=today,
        spec_id=args.spec_id,
    )

    if args.dry_run:
        print(content)
        return

    spec_dir = os.path.join(args.base_dir, args.spec_id)
    os.makedirs(spec_dir, exist_ok=True)

    index_path = os.path.join(spec_dir, "index.md")
    if os.path.exists(index_path):
        print(f"ERROR: {index_path} already exists. Use --dry-run to preview.", file=sys.stderr)
        sys.exit(1)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Created {index_path}")
    print(f"  spec-id: {args.spec_id}")
    print(f"  category: {args.category}")
    print(f"  title: {title}")
    print(f"\nNext: fill in TODO sections, then validate against specification-specification.")


if __name__ == "__main__":
    main()
