# @561-group/ways

The ways, enforced and midwifed. `ways` lints 561-group packages against
the package invariants (PEP8 for our shit, stricter — see
`dev/docs/explanations/package-invariants.md`, derived from
`dev/docs/explanations/the-ways.md`) and scaffolds new packages so they
are born conformant instead of being linted into shape later.

Findings are **charges, not pass/fail** (contradiction is load-bearing):

- `+ potential` — conforms; positive evidence only.
- `! active` — violation; negative evidence only.
- `# stable` — held: a violation under an inline `// law-allow: <key>`
  annotation. Visible, counted, not fatal.
- `· absurd` — no evidence (not applicable / nothing found).

Exit code is the number of packages with unheld error-grade violations.

## Quick start

```sh
node src/cli.ts list                      # the invariant catalog
node src/cli.ts check ../../lib/news-codecs
node src/cli.ts check --all               # judge the whole workspace
node src/cli.ts scaffold lib example-topology
```

## Naming grammar (M6)

Domain packages parse as `<thing>-<form>`: `lib/<thing>-topology`,
`lib/<thing>-codecs[-<standard>]`, `apps/<thing>-computer`,
`services/<thing>-tics` (trace information & computing service — memetics
was always meme + -tics), with `-wire`, `-room`, and kin specced as they
arrive. Utility packages (like this one) may diverge with cause; the
scaffolder advises, it does not block.

## Objects and morphisms

- `Invariant` / `INVARIANTS` — the catalog as data.
- `Finding` — a charge with evidence (file:line strings).
- `checkPackage(dir)` → `CheckReport` — judge one package. Never throws on
  domain outcomes; throws only on malformed input (no package.json, stray
  directory).
- `scaffold(root, layer, name)` — generate a conformant skeleton.
  Append-only: refuses to overwrite anything.

## Today's depth, and the roadmap

Checks are manifest/regex-grade: manifest shape (M1–M5), layering
direction and the codec zero-dep law (L1–L5), the substrate law guards
(S1–S5, mirroring `@561-group/memetic-law`; inline `law-allow` downgrades
to stable), wall-clock service ticks (S6), boolean-judgment smells in lib
exports (A1), Three-Dots-and-a-Dash kind grammar (A3), README substance
(D1). Hermetic and fast; false positives possible — that is what
`law-allow` and the stable charge are for.

Next: type-aware checks via the tsc API; import-graph layering; compiled
doc examples. Eventually: code ingested as witnessed predication and
lawfulness *settled* by the machinery rather than scanned — the
charge-shaped findings are already the right type, so that step is a
widening, not a rewrite.
