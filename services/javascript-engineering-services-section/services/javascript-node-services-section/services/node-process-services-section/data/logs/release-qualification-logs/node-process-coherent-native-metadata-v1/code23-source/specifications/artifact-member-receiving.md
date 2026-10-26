# Artifact member receiving

`admitArtifactRelease` keeps its existing inventory-release input and result unchanged. Two
explicit stages compare native observations about one immutable release:
`source-archive` and `archive-installed`. These are partial receiving stages.
An archive result never claims that a package was installed. The original
no-stage version-1 interface compares supplied manifest/path-inventory/import-row
observations; it is retained for compatibility, not upgraded to byte, native
installation, complete import execution or publication proof.

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
Legacy no-stage inputs retain their original contract. A real directory named `package/`
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

Native adapters must retain all archive headers and reject unsafe members
before extracting. They must bind installed observations to the actual native
operation, provider, original consumer input projection and registered-bin
target. A declaration, hand chmod or successful extraction is not that effect.
Code, Git and GitHub receiving callers must use the same model/CLI for these
comparisons while preserving their distinct native reader and execution
contracts. Model fixtures alone do not establish migration or actual use.

Original PR24 at ad08ad8ceb3aec4247a760feee848f259eac437e supplies additional
strict-stage/byte-decoding counterexamples. This coherent path preserves those
controls without adopting its compatibility-impacting replacement of the legacy
interface or its narrower644→755-only installation rule. Full version-2 release
refinement/caller migration, SHA256-repository producer inputs, a separately
qualified alternate publisher serialization, and original reusable native
archive/installation adapters remain distinct open obligations on that PR and
issue22. Supplied selection/receipt addresses alone cannot authenticate native
selection or effects. Adapters must bind original independently selected source
members; deriving that set only from output archive names proves correspondence
and can conceal omissions.
