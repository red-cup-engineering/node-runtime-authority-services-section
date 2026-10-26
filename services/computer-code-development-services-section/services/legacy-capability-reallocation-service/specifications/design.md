# Bounded committed-source retirement

The native review root, native working root and remote source root are separate
explicit coordinates. `sourceLegacyRoot`, when supplied, changes only the prefix
used for preimage qualification and the existing maker's publication paths.
Original local inventory and commit paths retain `legacyRoot`; staged-move checks
retain `workingLegacyRoot`. The same source mode/blob checks admit the mapping.
Preparation/result snapshots bind it, and retained receipt and batch common-cut
checks prevent substitution on replay. Omitting the field preserves old bytes
and behavior, including already completed publications at the previous location.

Extend the existing reallocation service, preserving its allocation and
reconciliation exports. Git's native `ls-tree -rz` on an exact commit and
explicit legacy path supplies inventory. No directory enumeration or
whole-host reference search is needed for this mode. NUL-delimited output
preserves literal filenames. The existing reviewer supplies capability
judgments; filename/name matches alone never authorize deletion.

A plan uses the service's ordinary JSON carrier and lists capability groups
with exact legacy-relative source paths. Covered groups cite actual living
files; deprecated groups quote authority. All paths are confined to the
selected repository. Before unlinking, compare the selected commit's blob
and mode with the current stage-zero index and native worktree bytes/mode.
Reject symlink ancestors. Hash symlink target bytes without following them.
Derive the Git executable flag from the owner execute bit (`0o100`), as native
Git does; group or other execute permission cannot mask an owner-mode edit.
Do not recursively remove a directory, copy an archive, fetch history, or
rewrite source. Return per-path outcomes so held files do not block clean
ones. Repeated apply reports absent sources without deleting anything else.
Receiving after a deletion commit also reports absence when both index and
worktree lack the selected path. A recreated untracked file remains held;
committing retirement must not prevent processing the next capability group.

Evidence files are independently inspected by the reviewer and hashed in
the receiving result. Their existence is a source witness, not a proof of
semantic parity or live installation. The plan records those judgments and
their limitations. Source classification recognizes the estate's MTS,
Elisp, Racket, Scheme and Lean as code, rather than opaque binaries.

Capability judgment compares the old folder's purpose against the actual living
owner's responsibility. Under the originating Leader instruction, that owner's
implementation is assumed better; reviewing every old endpoint is unnecessary.
The existing plan's reason records this assumption and any known limitations.
An unverified historical detail is not silently promoted to a missing capability
or a current production claim. Preserve genuinely unique jobs/information, and
handle the living owner's repository/package conformance at that owner. This is
a review rule over the existing plan, not new automatic deletion authority or a
change to its Git, custody, publication or receiving checks.
When writing the full result to a named output, CLI stdout contains only counts
and source identity; large per-capability witnesses stay in that result file.

The CLI's apply operation finishes by landing the exact removed/previously
absent tracked paths in Git. Recheck their original index identities and
worktree absence, then use native NUL-delimited literal pathspec input with
`git add -u` and `git commit --only`. Other staged work remains staged.
Already committed removals need no new commit; recreated files stop landing.
A commit failure leaves an explicit uncommitted result and failing exit code,
so the caller resolves it before starting another batch. The lower-level
unlink function remains available for controlled composition and tests.
If a hook or another actor recreates a selected file while committing, preserve
it and report `committed-with-recreated-files` with the actual commit and paths;
the CLI exits unsuccessfully so the caller reconciles those files before
continuing. A completed commit is never misreported as uncommitted.

The tracked-retirement CLI resolves and checks a named result parent and any
existing regular output file before invoking the unlink operation. Named
symlinks are refused without following their targets. Missing result
parents remain caller errors; the CLI does not invent a records directory.
These checks cover known destination defects, not later filesystem races.
The refusal leaves the source, index and HEAD untouched.

A witness may explicitly select another actual Git `repositoryRoot`. Resolve
its relative path only within that owner and use the same no-linked-ancestor,
regular-file, non-legacy and SHA-256 checks. Record its owner in the witness
receipt. Omitted owners retain the original same-repository behavior.

`--apply --publish --output=RESULT.json` composes the existing local retirement
and Fabrication's public source maker. Before its first deletion, source
preparation reads the original origin's advertised main commit and uses the
existing Fabrication/Git source reader to compare every selected original
mode/type/blob against that independently acquired commit. The accepted plan
revision remains the local review identity; the distinct remote revision and
origin become a retained source-preparation witness and the maker's
`reviewedSource`. A local-only immutable plan cut therefore does not have to
be fetchable from the original remote. Unknown remote state or mismatched
selected preimages refuses before local effects. Removed and previously
absent selected paths form the complete publication cut. This
service contains no GitHub publication or merge algorithm. Save the local
receipt before publication and the returned source result afterwards.
The receiving root is the plan's validated actual `repositoryRoot`, passed
explicitly as Fabrication's `packageRoot`; process cwd does not choose the
retirement or publication owner. The selected Fabrication0.4.15-dev.243
provider owns `git-objects.mjs` and its bounded immutable metadata transport.
Resolve that exact sibling from its public `git/github-candidate` selection;
do not copy its fetch/shallow/readback machinery. This is an explicitly
qualified internal supplier boundary, not a claim that the helper has a
published public export. Promoting that shared reader to a public API remains
a separate conformance concern.
Retain a failed receiving result's candidate and merge identity; on replay,
check the retained root and path set, then ask the same maker to receive that
candidate. No working-tree reinterpretation or replacement review is needed.

`--publish-records=REQUEST.json --records-output=RECEIPT.json` extends that
ordinary invocation after retirement publication succeeds. REQUEST contains
`repositoryRoot` and the existing maker request fields `paths`, `message`,
`push: true` and `reviewedSource`. Git Source Reading's canonical decoder
validates the request. Both the plan and retirement result must be selected
inside that actual Git owner; supporting records are explicit regular files.
Record paths cannot traverse links, enter legacy, or include RECEIPT.

Persist the exact selected file modes and byte identities in RECEIPT before
calling Fabrication. The result file is final before that separate publication:
its source-publication result goes only in RECEIPT. On replay, validate all
retained file identities and reuse the already completed retirement result;
continue the original maker candidate using the same shared publication path.
An unresolved record effect retains its own original candidate and leaves
the completed retirement source effect intact. No new GitHub algorithm,
source acquisition, repository census or cross-repository transaction is added.

The same CLI also accepts a `legacy-capability-retirement-batch/v1` input.
Its actual record `repositoryRoot` owns relative `plans`, `supportingRecords`
and five `outputs`: `plan`, `receiving`, `result`, `publicationRequest` and
`publicationReceipt`. `publication` supplies the existing maker's message,
optional candidate and optional reviewedSource. When omitted, source preparation
uses the already selected Fabrication source reader to acquire origin/main and
check that only the three named publication destinations are absent. The exact
remote lease is persisted in the ordinary generated request. On partial or
completed replay, read that retained request's preimages instead of acquiring a
new lease; all existing generated-byte equality checks still apply. Occupied
source destinations require explicit preimages. No field requests execution;
the existing CLI flags still select preview, apply and publication.

A pure composer validates the canonical plan declarations, common source cut
and disjoint selections. It retains exact UTF-8 plan/record text and SHA-256
in a bounded receiving snapshot, without promoting a review status. Explicitly
embedded record witnesses are rebound to that snapshot after their original
digest is checked; all other witnesses remain unchanged. The existing canonical
Git Source Reading decoder validates the complete three-record maker request.

Preparation reads only named regular files inside the actual record owner.
It validates every output and input alias before any write. The three generated
files are created exclusively, or reused only when byte-identical; result and
publication-receipt files remain owned by the existing CLI. A partial preparation
can therefore resume. Changed input or prepared bytes refuse before retirement.
No checkout, dependency graph, directory census, private dispatcher or alternate
source integration path is introduced. Pure counterexamples exercise mismatched
cuts, overlaps, authority and evidence failures; the ordinary CLI consumes the
prepared products on the actual pending legacy work.
A record-owner root alias is admitted only for retained, fully received
retirement and record publications, with all five existing output files and the
same physical Git root. Prepared bytes still pass the ordinary exact equality
checks. Fresh or incomplete custody retains the canonical-root requirement.
Completed source effects use Fabrication's existing immutable merge receiver;
uncertain effects keep its existing candidate-landing recovery. Historical
absolute addresses and receipt bytes are preserved rather than rewritten after
a workspace move.
Read-only reobservation never replaces a previously completed record receipt,
including when its provider is temporarily unavailable; its returned outcome
still reports that failure. New or uncertain effects retain durable progress
writes through the existing record-publication path.


Source preparation constructs the same fixed-message, push-enabled selected-path
request used by retirement publication and calls the canonical
readGitCommitPathsRequest before acquiring selected remote metadata or returning
a preparation witness. The decoder validates every selected path and exact lease;
the copied admitted reviewedSource is retained. Thus a native retirement cannot
commit first and discover a supplier path-contract refusal afterwards. Existing
candidate replay stays on its original receiving path. Git filenames remain
literal throughout; neither this service nor the codec unquotes them.

## Retirement during an uncommitted subtree relocation

Optional `workingLegacyRoot` names a second confined, nonoverlapping legacy
subtree in the same Git root. `legacyRoot` and `revision` continue to identify
the immutable reviewed originals and the original remote publication cut.
The ordinary inventory and publisher therefore keep their existing contracts.

The existing retirement consumer observes only the two named index subtrees
and their HEAD metadata. For each selected file it admits an exact staged
relocation: old working/index entries absent, unchanged old HEAD blob/mode,
new HEAD entry absent, and new index/working blob/mode equal to the original.
It unlinks only the new working file. The same commit consumer rechecks that
cut, removes only selected new index additions through native `update-index`,
and uses its existing path-limited commit for original deletions. Other staged
changes remain staged. A failed commit retains the same missing-file cut for
recovery; a completed replay requires both sides absent and creates no commit.
The result carries `workingLegacyRoot`; the batch composer includes it in its
common-cut comparison and passes it to the ordinary consumer unchanged.

## Bounded owner candidates

An owner descriptor may add `receivedSource: {owner, path}` to select a member
from its named JSON receipt. The same confined actual-Git-root reader holds the
record bytes once; a receipt cache parses them once for all selected members.
The combined budget charges the full record once and all native/source reads;
each selected member separately obeys the file bound. The pure received-source
decoder admits the existing pinned-owner and published-owner record shapes,
checks the selected bytes and their recorded Git/archive identity, and returns
source provenance without evaluating code. The ordinary matcher then uses the
same direct-export comparison and owner table. Root/directory Git ownership
observations are reused within the invocation. No acquisition, alternate package
installer or retirement path is introduced.

The ordinary source-record builder accepts bytes as well as a native path, so
selected committed blobs use the same imports, symbols and capability hints as
the existing inventory. The tracked inventory supplies immutable path/blob/mode
metadata; only the caller's selected regular blobs are read through native Git.
Check blob sizes before reading and cap both individual and cumulative bytes.

Named living modules belong to explicit actual Git owners. Read only their
confined regular files, reject linked ancestors, and retain their byte hashes.
The comparison returns shared direct-JavaScript-export hints and indexes into
one owner table. Private helper names do not manufacture owner candidates.
It deliberately supplies no semantic-equivalence or deletion decision. The
existing reviewed plan, retirement and publication operations remain unchanged.
The CLI takes one bounded JSON request and optionally creates one new output;
it never enumerates a package workspace or resolves a presumed owner by name.

Pinned owner receiving uses receivePinnedLegacyOwnerEvidence and the receive-pinned-legacy-owners CLI. The request names 1–32 HTTPS source identities, exact SHA-1 or SHA-256 commits and 1–64 paths per owner (512 overall). Defaults bound each file to 256 KiB, aggregate text to 8 MiB, and each original tree to 5,000 entries. All selections are validated before a caller-owned disposable child directory is created. createPinnedSourceReader is the sole Git acquisition/decoding mechanism; its selection never enters gitlinks. The consumer verifies complete selection, source provenance and Git blob identity before returning any evidence. Fatal UTF-8 decoding preserves a BOM and refuses lossy conversion. The result carries reviewRequired and retirementAuthorized:false. The existing batch composer can snapshot this JSON evidence and rebind a qualifying witness into canonical publication; no second retirement or publication path is introduced. Credentials are supplied only through the existing process or injected reader environment and are absent from results. A finally block waits for receiving to finish and removes only this invocation's scratch.
