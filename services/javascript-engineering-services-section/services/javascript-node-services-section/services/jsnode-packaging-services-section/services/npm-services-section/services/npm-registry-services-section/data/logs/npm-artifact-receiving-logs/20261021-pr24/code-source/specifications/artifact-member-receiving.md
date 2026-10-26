# Artifact member receiving

`admitArtifactRelease` compares full byte-backed release observations by default
or with `stage: "release"`. Two explicit partial stages compare native
observations about one immutable release: `source-archive` and
`archive-installed`. Their established inputs and results remain unchanged.
An archive result never claims that a package was installed. The original
version-1 manifest/path-inventory/import-row comparison is retained under the
explicit `compareArtifactInventories` export at this same owner. Its input and
result remain unchanged. Inventory-only input to full release admission refuses
as incomplete; it cannot establish payload, native installation, complete import
execution or publication proof.

The model performs no Git, TAR, registry, filesystem or package-manager effects.
The original native readers and installers own those effects and their source,
artifact, credential, capacity, timeout and provider admission. The model does
not authenticate a caller's observations or confer publication authority.
Keep their actual raw receipts and bind the facts supplied here to them.

Both stages require `registry`, `limits: {members, bytes}` and
`archive: {integrity, manifestText, members}`. Integrity is exact SHA512;
the 64-byte digest must decode and re-encode to the exact canonical padded Base64,
so pad-bit aliases and wrong lengths refuse. manifestText is the actual UTF8
package.json representation, bound by its exact UTF8 byte length and digest.
The native reader must decode original bytes losslessly; replacement decoding
cannot stand in for those bytes. Each member is
`{path, kind: "file", bytes, sha256, mode}`, with a literal package-relative
POSIX path, byte length, SHA256 hex digest and numeric permission bits.
The member carrying package.json must match manifestText's actual digest and
length. Duplicate, escaping, absolute, nonregular/link, excess-count, excess-byte
and special-permission members refuse. Control characters in paths, unknown
fields, wrong-stage evidence and mixed raw-Git/native mode fields refuse in the
new partial-stage contract. Adapters retain original Git mode/blob evidence
before projecting executable intent into the numeric source-member mode.
The explicit inventory operation retains its original contract. A real directory named `package/`
is not stripped as though it were the TAR container.

For `source-archive`, add `source: {repository, commit, manifestText, members}`
from the exact received source and the selected source members. Git adapters
retain the original Git modes/blob IDs and project regular-file permissions
to numeric mode values. Every selected source member must be present once in
the archive; payload and executable intent must match. Declaring a bin does
not permit changing executable intent at this stage.

An explicitly received publisher stamp may be supplied as
`publisher: {gitHead, format: "json-2-newline"}`. The head must equal the
source commit and archived gitHead. This projection is exactly
`JSON.stringify({...sourceManifest, gitHead}, null, 2) + "\n"`.
Only that exact representation is admitted; wrong stamp, changed version,
extra field or another serialization refuses. Original source and projected
manifest digests are retained separately.

For `archive-installed`, add `installed: {manifestText, members}` and an
actual `installation` context:

- `kind: "native-package-installation"`, status 0, platform `linux`;
- manager name `npm` or `pnpm`, exact version and entrySHA256;
- actual native operation requestSHA256, retained receipt locator and receiptSHA256;
- original consumer manifestSHA256 and frozen lockSHA256;
- installedManifestSHA256 for the released package, separate from its consumer;
- exact artifactIntegrity, package and version;
- actual registered bins as `{name, target, registered: true, targetSHA256}`;
  the received target bytes must equal the installed member's digest. Duplicate
  or foreign registered-bin observations refuse.

A native PNPM manager may be received under the finite
`normalization: "posix-package-files-0644-0755"` context. This records the
observed full modes while admitting only the witnessed regular-file 0644 and
executable-file 0755 projection. It cannot authorize a per-member chmod map.
It permits new executable intent only for a manifest-declared target whose
actual native registered bin is received. Payload changes, undeclared
execute changes, lost executable intent, other normalization, absent/failed/
foreign native evidence and another platform refuse. Existing identical modes
do not require normalization but still require the native installation context.

This read/write distinction follows the actual PNPM 11 CAFS behavior and
received Code 0.14.21 installation: 59 non-bin0600→0644,6 declared-bin0600→0755,
20 declared-bin0755→0755 and 1 non-bin0755→0755, with all 86 payloads equal.
The CAFS reader separates executable intent; new regular files use native
creation permissions, while an existing same-integrity store member may retain
its original mode. A current process umask does not reconstruct that history.
For actual native NPM file-directory consumers, the distinct
`normalization: "npm-file-directory-bin-umask"` context requires manager `npm`,
`operation: "npm-ci-file-directory"`, the actual numeric `umask` (0–0777),
and `normalizationProvider: {path: "bin-links/lib/fix-bin.js", sha256}` from
that manager's received source closure. Its original native receipt binds those
facts. NPM's bin-links primitive chmods registered targets to `0777 & ~umask`;
under a private 0077 umask the result is 0700. Only declared, actually registered
bin targets may receive that exact mode. Non-bin modes must remain equal;
this context cannot normalize all files, invent a chmod map, or permit lost
executable intent or changed payload. The model receives these native facts;
it does not authenticate the manager source or manufacture an installation.
Other native contexts require their own receiving rather than an assumed
cross-platform permission rule.

The existing registered CLI adds
`receive-packed-registry-artifact compare INPUT [OUTPUT]`.
It reads at most 8 MiB of primitive observations with fatal native UTF8 decoding
(no replacement-character equivalence), calls this shared model,
prints the typed result and exits 0/1 for admitted/refused. An optional result
path is written exclusively and never replaced. It does not read registry
credentials, download, extract, install or publish in compare mode.
The original before/after/publish environment-based contract is unchanged.

## Full release and retained inventory contracts

Full input has `registry`, finite `limits`, `source`, `archive`, `installed`,
`installation`, optional `publisher`, and `imports`, with optional
`stage: "release"`. Source, archive, installed and native installation facts use
the same representations and finite mode laws as the two partial contracts.
Full immutable Git identities may be 40-character SHA1 or 64-character SHA256
lowercase hexadecimal strings; their native acquisition belongs to the original
Git source-reading primitive, not this comparison. Missing evidence or legacy
inventory-only input returns `artifact-release-evidence-incomplete`.

Full admission invokes the existing source/archive comparison and then the
existing archive/installed comparison, binding their exact registry, package,
release version, SHA512 and normalized archive member identities. Any refusal
prevents full success. Its result is `ArtifactRelease`, version 2, stage `release`,
with both admitted partial values and a deterministic identity. Import rows remain
only supplied structural observations. Scope explicitly disclaims authenticated
native effects, complete import execution and publication authority. Input data
is never frozen or mutated. Partial source publication remains independent of an
installation that can occur only later.

The compare CLI accepts full input or either explicit partial stage under the
same fatal UTF8 8 MiB input bound and exclusive optional output. It performs no
registry, credential, installer or publisher effects. Unknown/mixed-stage fields
and unsupported representations refuse. Actual native receiving still originates
at its original source/installer ports; JSON cannot assert that authority.

Moving legacy no-stage acceptance to full admission is a breaking contract change.
Its original release selector must choose a compatible pre-1.0 minor boundary and
qualify actual caller migration before publication. `compareArtifactInventories`
preserves the useful legacy observation capability without presenting inventory
as full release admission. Known partial publisher/installer callers stay partial;
they must not acquire a future-installed prerequisite.

Native adapters must retain all archive headers and reject unsafe members
before extracting. They must bind installed observations to the actual native
operation, provider, original consumer input projection and registered-bin
target. A declaration, hand chmod or successful extraction is not that effect.
Code, Git and GitHub receiving callers must use the same model/CLI for these
comparisons while preserving their distinct native reader and execution
contracts. Model fixtures alone do not establish migration or actual use.

Original PR24 at ad08ad8ceb3aec4247a760feee848f259eac437e supplies additional
strict-stage/byte-decoding counterexamples. This coherent path preserves those
controls while reconciling its full-release requirement through the same partial
comparators and retaining the actual received manager mode laws. Its narrower
644→755-only installation rule cannot replace those witnessed contexts.
Full version-2 release/caller receiving and actual SHA256 producer receiving remain
separate from source qualification. A separately selected alternate publisher
requires its own genuine producer and exact byte contract; unsupported alternate
serialization still refuses rather than accepting asserted expected JSON.
The native adapters below address the reader/installation gap for
their finite supported contexts; publication and actual caller receiving remain
separate completion conditions. Supplied selection/receipt addresses alone cannot authenticate native
selection or effects. Adapters must bind original independently selected source
members; deriving that set only from output archive names proves correspondence
and can conceal omissions.


## Original native member receiving and prepared carriers

The native source/archive entrance MUST select exact original Git inputs before
reading archive names. Its original Git reader MUST refuse selected nonregular
entries and decode native paths fatally. The native NPM dry-run pack operation,
with lifecycle scripts disabled and bounded output, owns npm selection and ignore
precedence; carrierSourceIncludes is an acquisition allowance, not an exact pack
list. Every independently selected native pack path MUST bind to an exact Git
observation or an actual successful Code build product. Unknown paths refuse.
The original bounded package acquisition allowance MUST include its relevant
native ignore inputs without entering unrelated package/gitlink owners. The source
directory MUST contain only those verified original/prepared inputs and qualified
products; archive-derived membership cannot define completeness.

The Code caller MUST obtain Git reading and command codecs from the existing
dependency-free git-source-reading-service primitive. The Git networking umbrella
may re-export those same implementations, but MUST NOT enter Code's dependency
closure. Source qualification against an umbrella fixture does not establish the
released primitive's identity or the installed Code dependency graph.

The receive CLI MUST supply the primitive's original child-repository resolver.
It may receive only uniquely declared composed Gitlinks beneath the independently
selected package allowance, at their exact recorded commits. Its finite native
context accepts credential-free absolute HTTPS declarations. Absolute native
paths and local file URLs are supported only beneath an acquiring native/file
repository, preserving real local source fixtures without allowing a remote
declaration to select local custody. Relative, SSH and other opaque child locators
remain explicitly unread; Code MUST NOT invent Git-relative or GitHub resolution
rules. The primitive retains the original child repository, commit, raw source
path and blob identity. An unselected or uncomposed Gitlink MUST NOT be acquired.

The maintained declared TAR parser owns framing. Native receiving MUST verify the
canonical SHA512, stable descriptor and named-path identity, compressed/expanded
bounds, every interpreted member and diagnostic, one npm package container and
end-of-archive padding before extraction. Unsupported extensions, ambiguous
replacement-character names, links, special entries, duplicates and path aliases
are explicitly unread/refused. This finite context does not change the pure
model's wider supplied-fact interfaces. Native archive observation alone MUST NOT
claim installation, approval, publication or activation.

The existing release-wave owner owns planLandedPackageRelease, preserving the
original GHS occupied-version/history allocation. The Code carrier producer
preparePublicationCarrierManifest binds the exact original Git manifest to that
allocation. Its only prepared changes are the selected version and, solely when
repository is absent, a supplied finite npm repositoryFallback value. The fallback
is the networking caller's already-qualified repository value; Code MUST NOT
derive a GitHub address from a Git acquisition locator. Original acquisition
repository/commit and original/prepared manifest digests remain separate evidence.
Native receiving MUST recompute this projection from original source and the
original publisher allocation inputs. A caller-supplied prepared manifest is not
source evidence. The pure comparison still permits only its separate exact
gitHead/json-2-newline publisher projection. The original clean publisher may explicitly omit only its project .npmrc in a
retained finite publisherConfiguration declaration; native NPM selection and actual
packing MUST use the same empty user/global configuration and no inherited
credentials. This is a carrier-input preparation, not an archive membership or
manifest exception. Original build qualification, credential, occupied-set and publication authority gates remain in force.

Native installed receiving MUST originate in the actual successful original
package-manager operation after its complete frozen input/graph checks and before
prior-installation replacement. A JSON status, extracted tree or hash collection
cannot authenticate historical installation. These package-specific contracts do
not require a workspace, lockfile or package manifest in every repository.


The original frozen consumer receiver's optional artifactReceiving selection
MUST identify a unique exact independently received direct dependency per
consumer. It MUST admit every selected archive's limits, integrity and manifest
before launching any native installation. Only the actual successful child and
unchanged full frozen inputs may supply the in-process nativeInstallation port.
The complete native request/result and actual manager entry/manifest/distribution
hashes MUST be retained in an exclusive private receipt before comparison.
Comparison MUST precede replacement of any prior installation.

The initial installed context is Linux PNPM11.28.5. Its original native
`dist/pnpm.mjs` cmd-shim supplier emits `# cmd-shim-target=`; its own readShimTarget
consumes that metadata. Receiving MUST bind that single native registration to
the exact confined executable package target and retain the shim digest. A
native direct symlink MUST resolve to that same target. No package or shell
program is evaluated to inspect registration. Missing, foreign, ambiguous or
unsupported registration refuses. Another manager/shim context remains unread
until separately qualified; this adds no global shim/filename policy. The
existing pure model's PNPM mode normalization remains unchanged. A retained JSON
receipt alone cannot reopen a historical installation as a fresh native claim.
The actual bin directory MUST resolve to a directory inside the original native
installation before its registrations are read. A lexically contained path that
redirects to outside custody does not establish confined registration.


New native source/archive receiving requires an explicit real private
scratchDirectory supplied by its original operational owner, separate from source
inputs. It MUST NOT derive an operational data owner from the installed package
or silently use an account/system temp default. The ordinary receive CLI selects
this resource explicitly in its input; preparation/build evidence remains excluded
from that JSON entrance. An unsuccessful Git read retains its bounded scratch for
the original owner's disposition. Native installed receiving separately requires
an explicit artifactReceiptDirectory; logs, durable operation records and disposable
staging remain distinct resources chosen by the original receiving owner.
