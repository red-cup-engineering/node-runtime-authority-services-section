# Identity document access

This Code application helps an agent develop an evidence path for a person without conventional ID. It takes a case, a source register and a case-bound dependency model. It reports observed evidence, conditional acquisition paths, circular requirements, source problems, a research frontier and a variance evidence matrix. It does not determine legal identity or legal sufficiency.

The [requirements](specifications/requirements.md) trace to the first personal-service consumer's failed generic-inquiry approach. The [design](specifications/design.md) describes the distinction between source assertions, observations, proposed actions and receiver outcomes. Native JSON Schema admission, SignCell source statements and Data's FOUR readings supply the existing data contracts. There is no new evidence database or credential store.

## Run locally

From this directory, the installed runtime is `node bin/identity-access.mjs` with the arguments below. The existing publication service also supplies the source-binding development runner shown here:

```sh
node scripts/run.mjs assess --service /absolute/path/to/service-parameters.json --as-of 2026-10-26 --format markdown
node scripts/run.mjs packet --service /absolute/path/to/service-parameters.json --as-of 2026-10-26 --format markdown
node scripts/run.mjs scenario --service /absolute/path/to/service-parameters.json --as-of 2026-10-26 --assume record-locators --format json
node scripts/run.mjs source-impact --model /absolute/path/to/model.json --before /absolute/path/to/old-sources.json --after /absolute/path/to/new-sources.json
node scripts/run.mjs observe --service /absolute/path/to/service-parameters.json --as-of 2026-10-26 --evidence /absolute/path/to/observation.json
node scripts/run.mjs test
node scripts/run.mjs audit-evidence --service /absolute/path/to/service-parameters.json --as-of 2026-10-26
```

The runner first uses installed dependencies when their versions match the declared providers. If those are unavailable, it uses the existing local source-binding service and restores prior bindings after the command exits. The installed composition and direct CLI were exercised; the older source-binding fallback depends on its own available provider graph. This app remains private development source, not a published or independently deployed service. A consumer with installed dependencies can run `node bin/identity-access.mjs` directly. Do not run simultaneous source-binding invocations in the same app directory.

Analysis commands write to stdout. `init` additionally creates its explicitly selected new private directory. JSON is the default; assess, packet and scenario also render Markdown with ordinary paragraphs. There is no automatic contact, filing, payment, signature, scheduling or source refresh. The explicit assessment date is required. Review intervals are analyst-selected research controls, not government validity periods. The CLI checks saved snapshot hashes against the actual files before assessment.

## Open another client's case

`init` creates a new private case from a reviewed Operations template. It never clones an existing client's record. The destination must not exist; its parent must already be within the client's private custody.

```sh
node bin/identity-access.mjs init --template /absolute/path/to/template.json --destination /client/private/identity-case --case-id client-random-reference --as-of 2026-10-26
node bin/identity-access.mjs assess --service /client/private/identity-case/service.json --as-of 2026-10-26 --format markdown
```

The result names four created JSON files and the unresolved credential goal. Directory permissions are 0700, file permissions 0600. The opaque case reference must not be an SSN, passport number or other identifying number. Initialization refuses an existing destination, input symlinks, traversal, pre-bound client IDs/names, populated client inventories/routes, consent, facts/attempts and evidence observations. It validates the composition before writing and grants no authority. Templates contain operation data in Coesite; client facts, grants and actual receipts belong in the client's own case. A blank template intentionally selects no issuer or jurisdiction and contains no legal assertions. It cannot produce an actionable filing plan until an operator researches and authors those inputs.

## Consumer parameters and evidence

The service parameter record has this contract. Relative paths resolve from its own directory:

```json
{
  "kind": "identity-document-access-service",
  "version": 1,
  "casePath": "../identity-case-records/client.json",
  "modelPath": "../identity-case-records/client-evidence-model.json",
  "sourcesPath": "../research-source-records/current.json"
}
```

Explicit `--case`, `--model` and `--sources` paths can replace `--service`. The model and case must share an exact case ID. The model schema is [analysis.schema.json](data/schemas/analysis.schema.json). A source needs its ID, URL, title, retrievedOn, status=current and reviewAfterDays. A retained artifact also needs its relative path and SHA-256. Source status, clause selection and interpretation are authored judgments; hash checks do not verify their legal accuracy.

An observe input names a node and a witness already present in the case:

```json
{
  "nodeId": "record-locators",
  "observation": {
    "side": "for",
    "basis": "case-report",
    "casePointer": "/facts/12"
  }
}
```

The command returns a proposed updated model and its assessment. It does not write either input. A case-report observation is an attributed analyst mapping, not independent verification that the fact means what the analyst says. A receiver-receipt additionally must match the node's outcome and receiver contract and point to a dated case record with an original receipt reference. A draft or bounce fails that contract. The caller must inspect the underlying original receipt; the engine cannot authenticate a mailbox or government portal from a string reference.

Each step has AND inputs and sourced guards. Alternative steps may produce the same node. Obligations likewise allow common exhibits and alternative groups of exhibits. Proposed acquisitions never change observed possession. Discretionary decisions never create an approval. Source changes identify affected assertions and direct consumers; a changed page is not automatically a changed law. Unknown and contested observations remain distinct, and no amount of repeated supporting material resolves an opposing observation.

A claim's optional `statementId` pins the native source statement received from a Science study. The consumer must preserve that exact text, source identity, capture date and any evidence digest or the guard is blocked. The first study retains admitted native carriers; this does not certify their truth or an individual case's legal sufficiency.

`ready-for-review` means only that a step's modeled inputs and source guards are present. The engine does not compare strategic merit, resolve unmodeled facts, or establish that a ready draft should be sent. The case owner must retain a separate reasoned comparison of credential routes, evidence-acquisition tactics, adverse facts, decisive unknowns, costs and client circumstances. Do not encode one unselected tactic as a universal credential prerequisite.

## Receiving

For locally recovered exhibits, the optional service parameter `evidenceManifestPath` binds the existing private acquisition manifest. The [manifest contract](data/schemas/evidence-manifest.schema.json) requires its case ID and each artifact's source ID, basename, acquisition byte count and SHA-256. Model nodes may name `artifactSourceIds`. Their attributed observations remain intact, but those nodes are unavailable for preparation unless a same-case, same-date audit verifies every named artifact. Missing, changed, duplicate, escaping or symlinked artifacts cannot unlock preparation. An unaudited physical document or client report does not need an invented local file; bind only actual retained digital exhibits.

`audit-evidence` reads originals without modifying them and emits source IDs and issues, without document contents or paths. Its result establishes availability and retained-byte integrity only. It does not establish authenticity, certification, current-person linkage or agency acceptance. The pure assessment API receives an audit as an operator-supplied result; use the CLI loader to perform actual file checks rather than hand-authoring a verified flag.

Tests exercise no-ID cycles, an alternative entry path, source contradictions and supersession, receipt impersonation, physical receipt, missing exhibits, alternative exhibits, case mismatch, snapshot corruption and client isolation. The first real consumer is the personal civilianization service, whose parameter record and generated reports remain in its own checkout. Tests and a successful personal-case run establish local software operation. They do not establish that the proposed evidence will be accepted or that an ID has been obtained.
