import { semanticId } from "@red-cup-engineering/computer-content-address-engineering-services-section/semiotic-content-address";
import { sha256Hex } from "@red-cup-engineering/cryptographic-computer-data-engineering-services-section/integrity";
import { base64ToBytes, bytesToBase64 } from "@red-cup-engineering/cryptographic-computer-data-engineering-services-section/portable-bytes";

const sha256 = sha256Hex;
const HEX = /^[a-f0-9]{64}$/u;
const COMMIT = /^[a-f0-9]{40}(?:[a-f0-9]{24})?$/u;
const exactHex = value => typeof value === "string" && HEX.test(value);
const exactSHA512 = value => {
  if (typeof value !== "string" || !value.startsWith("sha512-") || value.length !== 95) return false;
  const encoded = value.slice(7);
  try {
    const bytes = base64ToBytes(encoded);
    return bytes.length === 64 && bytesToBase64(bytes) === encoded;
  } catch { return false; }
};
const executable = (mode) => (mode & 0o111) !== 0;
const fact = value => ["string", "number", "boolean"].includes(typeof value) ? value : null;
const frozen = value => {
  if (value && typeof value === "object") {
    for (const child of Object.values(value)) frozen(child);
    Object.freeze(value);
  }
  return value;
};
const literalPath = (path) => typeof path === "string" && path.length > 0
  && !path.startsWith("/") && !/[\\\x00-\x1f\x7f]/u.test(path)
  && !path.split("/").some(part => part === "" || part === "." || part === "..");

function exactFields(value, allowed, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new TypeError(`${label} requires a record`);
  for (const key of Object.keys(value)) if (!allowed.includes(key)) throw new TypeError(`${label} has an unexpected evidence field: ${key}`);
}

function members(entries, limits, label) {
  exactFields(limits, ["members", "bytes"], "limits");
  if (!limits || !Number.isSafeInteger(limits.members) || limits.members < 1
    || !Number.isSafeInteger(limits.bytes) || limits.bytes < 1) throw new TypeError("finite member and byte limits are required");
  if (!Array.isArray(entries) || entries.length > limits.members) throw new TypeError(`${label} exceeds its member bound`);
  const seen = new Set();
  let bytes = 0;
  for (const entry of entries) {
    exactFields(entry, ["path", "kind", "bytes", "sha256", "mode"], label + " member");
    if (!entry || !literalPath(entry.path) || seen.has(entry.path)) throw new TypeError(`${label} has an unsafe or duplicate path`);
    seen.add(entry.path);
    if (entry.kind !== "file") throw new TypeError(`${label} requires regular files, not links or special members`);
    if (!exactHex(entry.sha256) || !Number.isSafeInteger(entry.bytes) || entry.bytes < 0
      || !Number.isSafeInteger(entry.mode) || entry.mode < 0 || entry.mode > 0o777) throw new TypeError(`${label} has an invalid file identity or mode`);
    bytes += entry.bytes;
    if (!Number.isSafeInteger(bytes) || bytes > limits.bytes) throw new TypeError(`${label} exceeds its byte bound`);
  }
  return entries.map(({ path, kind, bytes, sha256, mode }) => ({ path, kind, bytes, sha256, mode }))
    .sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
}

function manifestText(text, entries, label) {
  if (typeof text !== "string") throw new TypeError(`${label} manifestText is required`);
  const member = entries.find(entry => entry.path === "package.json");
  if (!member || text.length > member.bytes || member.bytes !== Buffer.byteLength(text)
    || member.sha256 !== sha256(text)) throw new TypeError(`${label} manifest bytes do not match its member identity`);
  const value = JSON.parse(text);
  manifestIdentity(value);
  return value;
}

function binTargets(manifest) {
  const bins = typeof manifest.bin === "string"
    ? [[manifest.name.split("/").at(-1), manifest.bin]] : Object.entries(manifest.bin ?? {});
  return bins.map(([name, path]) => {
    if (typeof name !== "string" || name === "" || typeof path !== "string") throw new TypeError("invalid bin declaration");
    const target = path.replace(/^\.\//u, "");
    if (!literalPath(target)) throw new TypeError("bin target is not package-relative");
    return { name, target };
  });
}

/** Pure comparisons of caller-received native facts; no acquisition or installation. */
function admitMemberStage(input) {
  const { stage, registry, archive, limits } = input;
  exactFields(input, ["stage", "registry", "archive", "limits", ...(stage === "source-archive" ? ["source", "publisher"] : ["installed", "installation"])], "partial stage");
  exactFields(archive, ["integrity", "manifestText", "members"], "archive");
  if (typeof registry !== "string" || registry === "" || !archive
    || !exactSHA512(archive.integrity)) throw new TypeError("registry and exact canonical SHA512 archive identity are required");
  const packed = members(archive.members, limits, "archive");
  const packedManifest = manifestText(archive.manifestText, packed, "archive");
  const findings = [];
  const at = { registry, package: packedManifest.name, releaseVersion: packedManifest.version, integrity: archive.integrity };
  let compared, evidence;
  if (stage === "source-archive") {
    const { source, publisher } = input;
    exactFields(source, ["repository", "commit", "manifestText", "members"], "source");
    if (publisher !== undefined) exactFields(publisher, ["gitHead", "format"], "publisher");
    if (!source || typeof source.repository !== "string" || !source.repository || (typeof source.commit !== "string" || !COMMIT.test(source.commit))) throw new TypeError("immutable source repository and commit are required");
    compared = members(source.members, limits, "source");
    const sourceManifest = manifestText(source.manifestText, compared, "source");
    let expectedManifest = source.manifestText;
    if (publisher && (publisher.gitHead !== source.commit || publisher.gitHead !== packedManifest.gitHead || publisher.format !== "json-2-newline")) {
      findings.push({ code: "publisher-git-head-mismatch", path: "package.json" });
    }
    if (source.manifestText !== archive.manifestText) {
      if (!publisher || publisher.gitHead !== source.commit || publisher.format !== "json-2-newline") {
        findings.push({ code: "unreceived-manifest-projection", path: "package.json" });
      } else {
        expectedManifest = `${JSON.stringify({ ...sourceManifest, gitHead: publisher.gitHead }, null, 2)}\n`;
        if (expectedManifest !== archive.manifestText) findings.push({ code: "manifest-projection-mismatch", path: "package.json" });
      }
    }
    if (sourceManifest.name !== packedManifest.name || sourceManifest.version !== packedManifest.version) findings.push({ code: "manifest-release-mismatch", path: "package.json" });
    evidence = { source: { repository: source.repository, commit: source.commit }, publisher: publisher ? { gitHead: fact(publisher.gitHead), format: fact(publisher.format) } : null,
      sourceManifestSHA256: sha256(source.manifestText), expectedManifestSHA256: sha256(expectedManifest) };
    compared = compared.map(entry => entry.path === "package.json"
      ? { ...entry, sha256: sha256(expectedManifest), bytes: Buffer.byteLength(expectedManifest) } : entry);
  } else {
    const { installed, installation } = input;
    if (!installed) throw new TypeError("installed members are required");
    exactFields(installed, ["manifestText", "members"], "installed");
    if (installation !== undefined) {
      exactFields(installation, ["kind", "status", "platform", "manager", "requestSHA256", "receipt", "receiptSHA256", "manifestSHA256", "lockSHA256", "installedManifestSHA256", "artifactIntegrity", "package", "version", "normalization", "operation", "umask", "normalizationProvider", "bins"], "installation");
      if (installation.manager !== undefined) exactFields(installation.manager, ["name", "version", "entrySHA256"], "manager");
      if (installation.normalizationProvider !== undefined) exactFields(installation.normalizationProvider, ["path", "sha256"], "normalization provider");
      if (Array.isArray(installation.bins)) for (const bin of installation.bins) exactFields(bin, ["name", "target", "registered", "targetSHA256"], "native bin");
    }
    compared = members(installed.members, limits, "installed");
    manifestText(installed.manifestText, compared, "installed");
    if (installed.manifestText !== archive.manifestText) findings.push({ code: "installed-manifest-mismatch", path: "package.json" });
    // A declaration or extract is not a package-manager effect. The native
    // adapter owns and retains this exact operation/provider/lock receipt.
    if (!installation || installation.kind !== "native-package-installation" || installation.status !== 0
      || !["npm", "pnpm"].includes(installation.manager?.name)
      || typeof installation.manager.version !== "string" || !installation.manager.version
      || !exactHex(installation.manager.entrySHA256)
      || !exactHex(installation.requestSHA256)
      || !exactHex(installation.receiptSHA256) || typeof installation.receipt !== "string" || !installation.receipt
      || !exactHex(installation.manifestSHA256) || !exactHex(installation.lockSHA256)
      || !exactHex(installation.installedManifestSHA256)
      || installation.artifactIntegrity !== archive.integrity || installation.package !== packedManifest.name
      || installation.version !== packedManifest.version || installation.platform !== "linux") {
      findings.push({ code: "unreceived-native-installation" });
    }
    if (installation?.installedManifestSHA256 !== sha256(archive.manifestText)) findings.push({ code: "installation-manifest-mismatch" });
    const bins = binTargets(packedManifest);
    const seenBins = new Set();
    for (const bin of installation?.bins ?? []) {
      if (seenBins.has(bin.name) || !bins.some(target => target.name === bin.name && target.target === bin.target)) findings.push({ code: "unexpected-native-bin", name: fact(bin.name) });
      seenBins.add(bin.name);
    }
    for (const bin of bins) {
      const received = Array.isArray(installation?.bins)
        ? installation.bins.find(entry => entry?.name === bin.name && entry.target === bin.target && entry.registered === true) : undefined;
      const member = compared.find(entry => entry.path === bin.target);
      if (!received || !member || !executable(member.mode) || received.targetSHA256 !== member.sha256) findings.push({ code: "unreceived-installed-bin", path: bin.target, name: bin.name });
    }
    evidence = { installation: installation ? {
      kind: fact(installation.kind), status: fact(installation.status), platform: fact(installation.platform),
      manager: installation.manager ? { name: fact(installation.manager.name), version: fact(installation.manager.version), entrySHA256: fact(installation.manager.entrySHA256) } : null,
      receipt: fact(installation.receipt), receiptSHA256: fact(installation.receiptSHA256),
      requestSHA256: fact(installation.requestSHA256),
      manifestSHA256: fact(installation.manifestSHA256), lockSHA256: fact(installation.lockSHA256),
      installedManifestSHA256: fact(installation.installedManifestSHA256),
      artifactIntegrity: fact(installation.artifactIntegrity), package: fact(installation.package), version: fact(installation.version),
      normalization: fact(installation.normalization),
      operation: fact(installation.operation), umask: fact(installation.umask),
      normalizationProvider: installation.normalizationProvider ? { path: fact(installation.normalizationProvider.path), sha256: fact(installation.normalizationProvider.sha256) } : null,
      bins: Array.isArray(installation.bins) ? installation.bins.map(entry => ({ name: fact(entry?.name), target: fact(entry?.target), registered: fact(entry?.registered), targetSHA256: fact(entry?.targetSHA256) })) : [],
    } : null, modeChanges: [] };
  }
  const archiveMap = new Map(packed.map(entry => [entry.path, entry]));
  const comparedMap = new Map(compared.map(entry => [entry.path, entry]));
  for (const entry of compared) {
    const other = archiveMap.get(entry.path);
    if (!other) { findings.push({ code: stage === "source-archive" ? "absent-from-archive" : "extra-installed-member", path: entry.path }); continue; }
    if (entry.sha256 !== other.sha256 || entry.bytes !== other.bytes) findings.push({ code: "payload-mismatch", path: entry.path });
    if (stage === "source-archive") {
      if (executable(entry.mode) !== executable(other.mode)) findings.push({ code: "source-executable-intent-mismatch", path: entry.path });
    } else if (entry.mode !== other.mode) {
      const bin = binTargets(packedManifest).some(bin => bin.target === entry.path);
      const lost = executable(other.mode) && !executable(entry.mode);
      const acquired = !executable(other.mode) && executable(entry.mode);
      // One finite, witnessed POSIX projection, not an arbitrary chmod map.
      // Preserve all complete observed modes and its native context receipt.
      const native = input.installation;
      const pnpmProjection = native?.manager?.name === "pnpm"
        && native.normalization === "posix-package-files-0644-0755"
        && entry.mode === (executable(other.mode) || bin ? 0o755 : 0o644);
      // Native npm file-directory linking preserves non-bin file modes;
      // bin-links applies exactly 0777 & ~umask to its registered targets.
      // The adapter receives this primitive from the actual manager closure.
      const npmBinProjection = bin && native?.manager?.name === "npm"
        && native.normalization === "npm-file-directory-bin-umask"
        && native.operation === "npm-ci-file-directory"
        && Number.isSafeInteger(native.umask) && native.umask >= 0 && native.umask <= 0o777
        && native.normalizationProvider?.path === "bin-links/lib/fix-bin.js"
        && exactHex(native.normalizationProvider.sha256)
        && entry.mode === (0o777 & ~native.umask);
      const normalized = pnpmProjection || npmBinProjection;
      if (lost || (acquired && !bin) || !normalized) findings.push({ code: "unreceived-installed-mode", path: entry.path });
      evidence.modeChanges.push({ path: entry.path, archiveMode: other.mode, installedMode: entry.mode,
        executablePromotion: acquired, declaredBin: bin, normalization: normalized });
    }
  }
  for (const entry of packed) if (!comparedMap.has(entry.path)) findings.push({ code: stage === "source-archive" ? "extra-archive-member" : "absent-from-installed-package", path: entry.path });
  const identity = semanticId({ type: "ArtifactMemberAdmission", version: 1, stage, ...at,
    archive: packed, compared, evidence });
  if (findings.length) return frozen({ ok: false, refusal: { code: "artifact-member-mismatch", identity, stage, findings } });
  return frozen({ ok: true, value: { type: "ArtifactMemberAdmission", version: 1, stage, identity,
    ...at, archive: packed, compared, evidence, installationClaimed: stage === "archive-installed" } });
}

function inventory(value, name) {
  if (!Array.isArray(value) || value.some((path) => typeof path !== "string" || path === "")) {
    throw new TypeError(`${name} must be an array of nonempty paths`);
  }
  return Object.freeze([...new Set(value)].sort());
}

function difference(left, right) {
  const rightSet = new Set(right);
  return Object.freeze(left.filter((value) => !rightSet.has(value)));
}

function manifestIdentity(manifest) {
  if (manifest === null || typeof manifest !== "object" || Array.isArray(manifest)
    || typeof manifest.name !== "string" || manifest.name === ""
    || typeof manifest.version !== "string" || manifest.version === "") {
    throw new TypeError("artifact manifest must name a package and immutable version");
  }
  return semanticId(manifest);
}

/** One full admission composes the existing two partial comparisons. */
function admitFullRelease(input) {
  const required = ["registry", "limits", "source", "archive", "installed", "installation", "imports"];
  const missing = required.filter(key => input[key] === undefined || input[key] === null);
  if (missing.length) return frozen({ ok: false, refusal: {
    code: "artifact-release-evidence-incomplete", stage: "release",
    findings: missing.map(side => ({ code: "incomplete-evidence", side })),
  } });
  exactFields(input, ["stage", ...required, "publisher"], "full release");
  if (!Array.isArray(input.imports)) throw new TypeError("imports must record supplied imported observations");
  const imports = input.imports.map(row => {
    exactFields(row, ["specifier", "status", "exports"], "import observation");
    if (typeof row.specifier !== "string" || !row.specifier || row.status !== "imported"
      || !Array.isArray(row.exports) || row.exports.some(name => typeof name !== "string"))
      throw new TypeError("imports must record supplied imported observations");
    return { specifier: row.specifier, status: row.status, exports: [...row.exports].sort() };
  });
  const common = { registry: input.registry, limits: input.limits, archive: input.archive };
  const sourceArchive = admitMemberStage({ ...common, stage: "source-archive", source: input.source,
    ...(input.publisher === undefined ? {} : { publisher: input.publisher }) });
  const refused = result => frozen({ ok: false, refusal: {
    code: "artifact-release-mismatch", stage: "release",
    findings: [{ code: result.refusal.code, stage: result.refusal.stage, findings: result.refusal.findings }],
  } });
  if (!sourceArchive.ok) return refused(sourceArchive);
  const archiveInstalled = admitMemberStage({ ...common, stage: "archive-installed",
    installed: input.installed, installation: input.installation });
  if (!archiveInstalled.ok) return refused(archiveInstalled);
  const source = sourceArchive.value, installed = archiveInstalled.value;
  if (["registry", "package", "releaseVersion", "integrity"].some(key => source[key] !== installed[key])
    || semanticId(source.archive) !== semanticId(installed.archive)) return frozen({ ok: false, refusal: {
    code: "artifact-release-mismatch", stage: "release", findings: [{ code: "release-identity-mismatch" }],
  } });
  const scope = { suppliedObservations: true, nativeEffectsAuthenticated: false,
    completeImportsEstablished: false, publicationAuthorized: false };
  const identity = semanticId({ type: "ArtifactRelease", version: 2, stage: "release",
    registry: source.registry, package: source.package, releaseVersion: source.releaseVersion,
    integrity: source.integrity, sourceArchive: source.identity, archiveInstalled: installed.identity, imports, scope });
  return frozen({ ok: true, value: { type: "ArtifactRelease", version: 2, stage: "release", identity,
    registry: source.registry, package: source.package, releaseVersion: source.releaseVersion,
    integrity: source.integrity, sourceArchive: source, archiveInstalled: installed, imports, scope } });
}

/** Pure full byte/native-fact admission, or an explicitly selected partial stage.
 * Custody, native authority and complete import execution remain external. */
export function admitArtifactRelease(input = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new TypeError("artifact release requires a record");
  if (["source-archive", "archive-installed"].includes(input.stage)) return admitMemberStage(input);
  if (input.stage !== undefined && input.stage !== "release") throw new TypeError("unknown artifact comparison stage");
  return admitFullRelease(input);
}

/** Retain the original version-1 inventory observations under an explicit name.
 * This never establishes payload, native effects or complete import receiving. */
export function compareArtifactInventories(input = {}) {
  const { registry, manifest, tarballManifest, tarballInventory, installedManifest, installedInventory, imports } = input;
  if (typeof registry !== "string" || registry === "") throw new TypeError("registry is required");
  const sourceManifestIdentity = manifestIdentity(manifest);
  const tarballManifestIdentity = manifestIdentity(tarballManifest);
  const installedManifestIdentity = manifestIdentity(installedManifest);
  const packed = inventory(tarballInventory, "tarballInventory");
  const installed = inventory(installedInventory, "installedInventory");
  if (!Array.isArray(imports) || imports.some((entry) => !entry || typeof entry.specifier !== "string" || entry.specifier === "" || entry.status !== "imported" || !Array.isArray(entry.exports))) {
    throw new TypeError("imports must record each declared export as imported");
  }
  const releaseIdentity = semanticId(Object.freeze({
    type: "ArtifactRelease",
    version: 1,
    registry,
    package: manifest.name,
    releaseVersion: manifest.version,
    manifest: sourceManifestIdentity,
  }));
  const refusal = Object.freeze({
    manifestMismatch: sourceManifestIdentity !== tarballManifestIdentity || sourceManifestIdentity !== installedManifestIdentity,
    inventory: Object.freeze({
      absentFromTarball: difference(installed, packed),
      absentFromInstalledPackage: difference(packed, installed),
    }),
  });
  if (tarballManifest.name !== manifest.name || tarballManifest.version !== manifest.version
    || installedManifest.name !== manifest.name || installedManifest.version !== manifest.version
    || refusal.manifestMismatch || refusal.inventory.absentFromTarball.length > 0 || refusal.inventory.absentFromInstalledPackage.length > 0) {
    return Object.freeze({ ok: false, refusal: Object.freeze({ code: "artifact-release-mismatch", releaseIdentity, ...refusal }) });
  }
  return Object.freeze({ ok: true, value: Object.freeze({
    type: "ArtifactRelease",
    version: 1,
    identity: releaseIdentity,
    registry,
    package: manifest.name,
    releaseVersion: manifest.version,
    manifest: Object.freeze({ identity: sourceManifestIdentity, value: manifest }),
    tarball: Object.freeze({ manifestIdentity: tarballManifestIdentity, inventory: packed }),
    installed: Object.freeze({ manifestIdentity: installedManifestIdentity, inventory: installed }),
    imports: Object.freeze(imports.map((entry) => Object.freeze({ specifier: entry.specifier, status: entry.status, exports: Object.freeze([...entry.exports].sort()) }))),
  }) });
}
