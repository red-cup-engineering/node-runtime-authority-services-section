# Legacy capability reallocation service

For an unchanged legacy subtree moved in the index before its relocation is
committed, a reviewed plan can specify `workingLegacyRoot` alongside its original
`legacyRoot` and immutable `revision`. The same command checks both cuts, removes
the selected new staged additions, commits their original-path deletions and
publishes the original source cut. Changed files or index entries are held;
unrelated relocation work stays staged. Omit the field for an ordinary retirement.

<!-- 561-group-standards:badges:start -->
[![Red Cup Engineering](https://img.shields.io/badge/561%20Group-Red%20Cup%20Engineering-c0392b)](https://github.com/red-cup-engineering)
[![License: MIT](https://img.shields.io/badge/license-MIT-c0392b)](LICENSE)
[![Indigenous data: CARE](https://img.shields.io/badge/Indigenous%20data-CARE-4b6f44)](https://github.com/red-cup-engineering/.github/blob/main/GOVERNANCE.md)
[![Tips welcome](https://img.shields.io/badge/tips-welcome-d4a017)](https://github.com/561-group/.github/blob/main/TIPS.md)
<!-- 561-group-standards:badges:end -->
## Lightweight committed-folder review

Compare the folder's purpose with the living owner's responsibility. Once actual
living source establishes that home, the Leader's legacy-revival instruction
assumes its implementation is better. Exact parity with every historical helper,
endpoint, test or dependency is not a retirement prerequisite. Keep genuine
missing capabilities and unique information for integration; do not turn this
review into reconstruction of the old implementation. Record any unverified
endpoint, installation or production property as a limitation of the claim.
Repository/package conformance is separate work at the living owner.

If origin has already relocated the subtree while the local review and index
still name its earlier cut, declare `sourceLegacyRoot` for its current upstream
location. `legacyRoot` and `revision` keep the native review identity;
`workingLegacyRoot` independently selects the unchanged staged local move.
The command checks every mapped upstream mode/blob before local deletion and
publishes only those mapped paths. It never infers a move or changes the mapping
of a retained publication; replay keeps its original source identity.

For a local legacy folder, start with `inventoryTrackedLegacyCapabilities`.
It reads only the explicitly selected Git subtree's metadata. Review folder
capabilities against actual living source, including installed suppliers
resolved from their real consumer. Different package names, edited source,
or unfinished repository conformance do not establish a missing capability.
Preserve useful missing information in its existing owner before retirement.

Before drafting replacement prose, inspect the selected owner's existing
character or instance library as well as its general content directories.
For example, a character's diary and semantic anchors may already live under
`lib/agency/characters/<name>/`, with its principal and index explaining how
they are used. A content-only listing cannot establish that they are missing.
Read the actual bodies and reader entry points; reuse that living home when
it receives the job. An archive or migration receipt alone does not receive it.

Follow current repository ownership through the selected Gitlinks and resolve
renamed repositories before declaring a capability absent. An older native
mount can differ from current original source after a split. Record that
difference and preserve unrelated native work; do not restore source-only
files as a presumed glitch or claim installed parity from their source presence.

Generated harness context is a separate job from its authored office, skill or
memory sources. Check the complete wrapper shape and explicit generated-output
marker before comparing its projection job with the current projector. Keep
authored exceptions for their own receiving review; a nearby generated file
does not make the whole directory disposable.

Generated admission claims can also embed source. Two reviewed platform-node
claims each contained a base64 manifest of sixteen files, including authored
charters, characters and contracts. Their surrounding preparation and receipt
records looked like runtime state. Inspect the declared file list, encodings,
sizes and hashes before choosing a disposition; compare useful embedded content
with its living owner as well as the wrapper's bookkeeping job. A generated
label does not establish that those contents are received. Historical authority
claims remain historical, and examining a manifest does not require executing
its embedded files or reconstructing its old installation.

`retire-tracked-legacy-capabilities PLAN.json [--apply] [--output=RESULT.json]`
previews or removes just reviewed committed files. The plan names
`kind: "legacy-capability-retirement-plan/v1"`, `repositoryRoot`, exact commit
`revision`, `legacyRoot` and `capabilities`. Each capability names `id`,
`disposition` (`covered` or `deprecated`), `reason`, exact legacy-relative
`sourcePaths`, and living `evidence: [{path, sha256}]` or deprecation
`authorization`. Evidence paths are repository-relative actual source files.
Bind their SHA-256 after inspection. Git history provides recoverability;
the reviewer provides the capability judgment.
When the living evidence belongs to another repository, its item additionally
names that actual Git `repositoryRoot`; `path` stays relative to that owner.
The same confinement, symlink refusal and byte checks apply there. The service
does not copy receiving records or living code into the archive to satisfy a
same-repository path constraint.

Apply checks committed blobs, index identity, working bytes and native Git
executable/symlink modes. It preserves local changes, unknown files and
untracked siblings, and reports per-file holds without blocking other eligible
files. It unlinks individual files and never recursively removes a directory.
With `--output`, stdout is compact. Result files retain the complete receipt.
With `--apply`, the CLI immediately attempts an exact-path Git commit while
preserving unrelated staging. Check its exit status and `landing` before
reporting success: a positive `removed` count alone is insufficient. Report
`landing.commit` for committed paths and keep holds explicit. An `uncommitted`
or `committed-with-recreated-files` landing needs resolution before handoff.
Commit the receiving evidence, plan and result in their owning repository too.
With `--apply --publish --output=RESULT.json`, the same command commits locally
and sends its exact reviewed mode/blob set to Fabrication's existing source
maker. It lands the source review and receives the complete immutable merge,
preserving unselected source changes. A changed reviewed source preimage refuses
publication. The receipt retains any completed effect awaiting readback; rerun
the same command and output to receive it without another push or review.
Publication requires a durable output; a local commit alone remains available
without `--publish`. Before restoring an unexpected deletion, consult its
commit and receiving record.

The command qualifies those original preimages at the advertised remote main
before deleting locally. Its immutable plan revision may be a local-only
review cut: `sourcePreparation` retains that review identity separately from
the remote lease used by Fabrication. An unavailable or mismatched original
source refuses before deletion/commit. Local-only apply needs no remote.

The package's public root also exports `prepareTrackedLegacySourcePublication`
for library consumers. Prepare before applying; publication refuses a fresh
retirement without this witness and never silently prepares after deletion:

```js
const preview = retireTrackedLegacyCapabilities({plan});
const sourcePreparation = await prepareTrackedLegacySourcePublication({result: preview});
const result = retireTrackedLegacyCapabilities({plan, apply: true});
result.sourcePreparation = sourcePreparation;
result.landing = commitTrackedLegacyRetirement({result});
// Save result in the owner's durable output before the external source effect.
result.publication = await publishTrackedLegacyRetirement({result});
// Save the returned receiving result, including any retained candidate.
```

For replay, pass the retained `publication` as `previousPublication` to both
preparation and publication, and retain its original `sourcePreparation`.
An existing candidate is received as originally named rather than re-leased
or pushed again. The ordinary CLI performs this custody automatically.

Add `--publish-records=REQUEST.json --records-output=RECEIPT.json` to finish
the plan/result/supporting-record publication in the same invocation.
REQUEST contains their actual `repositoryRoot` and Fabrication's ordinary
`paths`, `message`, `push: true` and exact `reviewedSource` fields. Select
the plan and result plus any supporting records explicitly. RECEIPT must
remain outside that cut: it holds the record merge and any unresolved effect,
while the published retirement result stays fixed. Repeating this invocation
receives a retained record candidate without rerunning retirement or changing
the published result. Changed record bytes or custody require reconciliation.

The same command accepts a `legacy-capability-retirement-batch/v1` JSON input
to prepare and consume a batch without a separate composition script:

```sh
retire-tracked-legacy-capabilities batch.json          # prepare + preview
retire-tracked-legacy-capabilities batch.json --apply --publish
```

The batch names `id`, the actual record-owner `repositoryRoot`, owner-relative
`plans` and `supportingRecords` arrays, and `outputs` with five owner-relative
paths: `plan`, `receiving`, `result`, `publicationRequest`, `publicationReceipt`.
Its `publication` contains the existing maker's `message` and optional `candidate`.
Omit `reviewedSource` for fresh outputs: the command observes origin/main and
checks the three exact destinations are absent before writing prepared files.
It retains that immutable lease in the generated publication request and reuses
it on every replay, even after main advances or the records land. Existing
source destinations require an explicitly reviewed `reviewedSource`.
These output files and the batch manifest must have separate addresses;
their parent directories already exist. Do not add output flags in batch mode.

Preparation combines only the same immutable source cut with disjoint paths
and capability identities. Its receiving snapshot preserves exact original
UTF-8 plans and supporting JSON bytes with SHA-256. Explicitly embedded record
witnesses require their original reviewed digest; direct living-code witnesses
remain direct. This is mechanical assembly, not another capability judgment.
The generated maker request always includes `push: true` and is decoded by
the original Git Source Reading provider before preparation writes anything.

Up to32 plans and64 supporting records may total one MiB; the resulting snapshot
is at most two MiB. Named files, owner boundaries, aliases and existing output
bytes are checked first. Identical prepared files are reused; different files
are preserved and refused. Partial preparation may resume. Publication/recovery
then uses the same ordinary path described above. A retained source-publication
result can only be replayed with `--apply --publish`; a later preview or local
apply cannot overwrite it. For a separate preview, use a separate result path.

If the record owner's physical directory moves and its old address remains a
symlink to the same Git root, completed batches can replay with their original
bytes. All five output files and both fully received publications must exist.
This path only reobserves the original immutable merges. New or incomplete
operations must use the current physical root.
A failed read-only recheck returns its failure while preserving the last
completed record receipt for another attempt.

The older full-ledger verifier below performs a repository reference walk;
use this bounded path on Bare Cedar Fog. A source witness and file removal
do not assert independent deployment or living-owner architectural conformance.

The first actual consumer is Bare Cedar Fog's
`data/records/source-maintenance-records/legacy-revival/` record family.
The Leader explicitly deprecated Lean on 2026-10-23; that local decision does
not silently deprecate meaningful mathematical knowledge elsewhere.

This service prevents an archive being called “processed” merely because it was read or described.
Integration flows from legacy into living owners. `retire-wave --write` uses the
existing reconciler to integrate its selected wave into those owners.
It inventories every source carrier below a supplied legacy root, derives explicit carrier and destination candidates from the source itself, and writes a ledger whose records begin `unallocated`.

A record becomes `retired` only when it names a modern, non-legacy implementation witness and the verifier finds no remaining non-legacy route to that archive source.
A family is `fully-reallocated` only when every discovered source carrier is retired.
New or changed archive files invalidate that result.

When a legacy file is itself the carrier that must survive, an allocation may also declare a `materializations` entry with its `sourcePath` and modern `destinationPath`.
`materialize-legacy-capability-carriers` moves only those declared files after checking their ledger SHA-256 identity.
The verifier then accepts the source's absence from the archive only if exactly one retired materialization exists and its modern bytes still match the original carrier.

The service owns migration accountability for code.
It does not decide the domain meaning of a scientific document, nor does it copy code between services.
The ledger makes those decisions and their evidence durable so an agent can continue the reallocation without asking a person to reconstruct the previous audit.

```sh
inventory-legacy-capabilities path/to/lib/legacy/project --write data/project.ledger.json
allocate-legacy-capabilities data/project.ledger.json data/project.allocations.json
materialize-legacy-capability-carriers data/project.ledger.json --repo-root /home/emsenn/info
verify-legacy-capability-reallocation data/project.ledger.json --repo-root /home/emsenn/info
purge-legacy-capability-archive data/project.ledger.json --repo-root /home/emsenn/info
```

`readArchiveDirectories` reads the directories named `archive` or `_archive` among repository-relative file paths, as a tracked listing gives them, each with the archive enclosing it and the legacy root holding it, named as a ledger names its `legacyRoot`.
An archive outside every legacy root is legacy material that no ledger can inventory until it is placed under one.

For every Markdown record, the carrier home is the canonical Markdown engineering section downstream of SignCell.
A scientific or organizational subject owner may additionally be proposed; that never relocates the Markdown carrier machinery into a system application.

Allocation declarations name an effect, carrier, destination, state, and the one or more discovered source paths that evidence it.
The allocation command rejects unknown source paths, and the verifier rejects any archive source that is not covered by a declaration; an agent cannot mark a whole package complete while leaving one of its source effects unaccounted.

`purge-legacy-capability-archive` is destructive.
It verifies the current ledger, deletes that exact ledger-root, and records `archiveDisposition: "purged"`. Source verification alone does not establish useful consumer receiving.
The verifier then continues to check the ledger's original source hashes, retired witnesses, and any required byte-preserved materializations; an absent archive without that disposition is still a verification failure.

## Restorations from history

`data/main-history-loss-forensics.json` records every first-parent commit of main that deleted content no longer present at HEAD, with its pull request, date and title, and how much of what it deleted survives edited at HEAD, was restored from history, exists in an owner repository, or was not restored (generated data, caches, build output, trivial files).
Each `data/restorations/*.ledger.json` names the files one restoration returned byte-for-byte from history under a legacy tree: original path, restored path, git blob, SHA-256, mode, and the deleting commit.
`data/legacy-unit-inventory.json` lists every legacy unit with source code, its languages, tests, package names and any active package of the same name; a unit's `activation` stays `pending` until its capability is carried into its owner and that migration is recorded here.

## Copies retired for their owners

For bounded discovery, `observe-tracked-legacy-owners REQUEST.json [NEW-OUTPUT.json]`
reads selected committed files and explicitly named living modules. The request
contains `repositoryRoot`, `legacyRoot`, exact `revision`, `sourcePaths` (1–64),
and `owners` (1–64 `{repositoryRoot, path}` records). Optional `maximumFileBytes`
and `maximumTotalBytes` bound the read. No directory tree is walked.

One owner table carries actual paths, source signals and SHA-256 identities;
each source lists indexed candidates with shared directly declared JavaScript
exports. Private helper names do not create candidates. An unmatched
source remains visible. These are review hints, including same-name functions
whose behavior differs; the report always carries `retirementAuthorized: false`.
After comparison, use the existing reviewed retirement and publication command.

A package defined both here and in a repository that owns it (DRC-2, one owner) is reconciled into the owner and its copy here retired, wave by wave.

```sh
census-owned-copies --owner-forest <mounted owner> --copy-repo <this repository> --open-pr-files <changed files of open pull requests> --write data/forest-migration/<owner>.census.json
reconcile-wave --census data/forest-migration/<owner>.census.json --wave <n> --copy-repo <this repository> --owner-root <owner/repository=dir>... --reports <dir> [--apply]
```

The census names each shared package's owner (repository and path), each copy here, whether it is byte-identical, its dependency level, and the open pull requests that touch it (such a copy is held until they are rehomed).
Waves are whole dependency levels, leaves first.
`reconcile-copy-with-owner` reads exact Git blobs and path histories. Selected copy-only source is integrated even when the owner previously deleted it. `--copy-revision <commit>` reads historical source directly, avoiding another `restored-from-main` copy. `--resolutions` supplies per-path `{keep: "owner" | "copy", because: "the sourced judgment"}` decisions.
With `--apply`, clean files proceed independently of other conflicts. Concurrent owner edits are merged with the selected changes; overlapping edits remain intact and appear as `worktree-conflict`. Executable and symbolic-link modes are preserved. A wave may supply each copy's `revision` in its existing census.
`retire-wave --write` composes that same integration operation for the selected wave. It writes into the mounted living owners rather than moving files into legacy or rewriting workspace admission. Remaining conflicting source stays available for continued integration.
`data/forest-migration/computer-services-section.census.json` is the census of the computer-services-section forest mounted at `engineering-services-section/services/computer-services-section`.

## External GitHub archive intake (2026-10-15)

The `emsenn/emsenn-archive` repository is an intake shell, **not** the corpus to consume. The two substantive carriers are `emsenn/emsenn-archive-code` (7,700 Git tree entries at `main` when inspected) and `emsenn/emsenn-archive-org` (GitHub's recursive tree response exceeded its completeness limit). Do not interpret a truncated recursive tree as an exhaustive census: traverse child trees until each subtree is complete before asserting a source inventory.

For these and other external archive repositories, first read open issues, PRs, and branches of the source and each prospective receiver. Extract the *distinct capabilities and content*, not their archive directory hierarchy. At minimum classify source blobs as mathematical/scientific knowledge (Lenticule), executable implementation and tests (Red Cup; Data → Code → Networking → Systems), declarative operating procedure/configuration (Coesite), or enterprise/customer content (its actual Corporate/Public owner). A service-section Gitlink belongs in its correct parent only when the child is a genuine independently owned repository. **Never Gitlink the archive itself as a substitute for allocation.**

For each chosen capability, work with exact source Git commit, relative paths, blob IDs or hashes, recipient revision and paths, existing overlapping implementations, acceptance requirements, and the affected consumers. Use the existing inventory/allocation/reconcile/materialize machinery wherever its preconditions apply. Preserve unique features; make an actual change in the living owner and update that owner's consumers before claiming retirement. A copied source file in another archive or an isolated migration note is not receiving evidence. A successful source commit, even with a linked Gitlink, is not proof of tested installation or independent customer acceptance.

Concrete discovered unit: `emsenn/emsenn-archive-code/topical/science/mathematics/predication-categories/bucket-3-lean/` contains a 22-file Lean/Lake project (19 Lean source modules plus package metadata) with fiber algebra, adjoints, residuation and distributed-settling convergence. Assess its mathematical statements against `lenticule-science/obsmetrologia` first, especially the latter's existing package constraints and import spine. It is **not** safe to copy a single importing module as a standalone proof or call this integrated without proof elaboration. The research and proof author controls mathematical admission; any reusable supporting engineering implementation belongs to the appropriate Red Cup owner. Existing source and owner must be compared before deleting or superseding either.

Completion is separately witnessed at four boundaries: source accounted for; owner implementation integrated; consuming parent/section relationship corrected; and qualified installation independently received. Record each boundary distinctly, and leave downstream statuses unknown where execution or customer receiving is unavailable.

The ordinary owner matcher accepts pinned and published owner receipts: an `owners` entry
`{"repositoryRoot":"/actual/record/repository","path":"records/owner.json","receivedSource":{"owner":"owner","path":"src/owner.mjs"}}`
selects a pinned owner ID and source member. Published-owner receipts use their
package name as `receivedSource.owner`. Multiple entries can select different
members of one receipt, which is read and charged against the byte budget once.
Results retain the receipt hash and source identity; candidates still require
capability review and grant no retirement authority.

Receive owner implementations that are not checked out locally with `receive-pinned-legacy-owners REQUEST.json NEW-OUTPUT.json`. For example:

```json
{"kind":"legacy-pinned-owner-evidence-request/v1","sources":[{"id":"owner","repository":"https://github.com/example/owner.git","commit":"0123456789012345678901234567890123456789","paths":["package.json","src/owner.mjs"]}]}
```

The command uses the original pinned Git source reader without checking out or evaluating code. It requires every named file at that exact owner pin, retains text/mode/object identity and SHA-256, bounds acquisition, and cleans its own temporary object stores after success or failure. Authentication stays in the caller's Git environment. Optional `scratchParent` must name an existing unredirected absolute directory. Optional `maximumFileBytes`, `maximumTotalBytes` and `maximumTreePaths` lower or finitely raise the documented defaults. The output requires capability review and grants no deletion authority. Add it to the existing retirement batch's `supportingRecords` and use its exact SHA-256 as the living witness after reviewing the capability; ordinary retirement and publication stay unchanged.
