import { readFile, access, readdir, writeFile, mkdir, glob, cp, mkdtemp, rm, link, chmod, lstat, rename, realpath } from "node:fs/promises";
import { resolve, dirname, join, relative, sep, isAbsolute, basename } from "node:path";
import { createHash } from "node:crypto";
import { execFile } from "node:child_process";
import { promisify, isDeepStrictEqual } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { carrierSurfaceViolations } from "./carrier-surface.mjs";
import { SECRET_PATH, secretBearingContentPaths } from "./tarball-guard.mjs";
import { readRegistryPackage, readRegistryPackageVersion, publishConfiguredNpmRegistryArtifact, downloadConfiguredNpmRegistryTarball, receiveRegistryTarball } from "./registry.mjs";
import { packageExportSurfacePaths } from "./carrier-surface.mjs";
import { dependencySpecificationViolations } from "./dependency-policy.mjs";
import { npmPackResult } from "./npm-pack-result.mjs";
import { receiveInstalledArtifactMembers, readRegistryArchiveMembers } from "./artifact-member-receiving.mjs";

const fields = ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"];
const local = /^(workspace:|file:|link:)/u;
const stable = /^(\d+)\.(\d+)\.(\d+)$/u;
const run = promisify(execFile);
const compare = (a, b) => { const aa = a.split(".").map(Number), bb = b.split(".").map(Number); return aa[0] - bb[0] || aa[1] - bb[1] || aa[2] - bb[2]; };

// One canonical source coordinate for both planning and installed receiving.
// Original consumer source may be a directory or an explicit manifest file.
export function sourceRegistryManifestPath(location) {
  if (typeof location !== "string" || !location.trim()) throw new TypeError("source locator must be a nonempty path");
  return resolve(location === "package.json" || location.endsWith("/package.json") ? location : join(location, "package.json"));
}

/** Plan one explicit source selection, never discover a workspace or resolve
 * executable suppliers from source. Locators are authoring custody only.
 * Every changed provider gets a new, unoccupied immutable release identity;
 * this preserves its assessed source API instead of guessing that latest is
 * compatible. Publication remains a separate packed-artifact operation. */
export async function planSourceRegistryClosure({ consumerPaths, providers, publishNames = [], registry = "https://registry.561.group/", readRegistry = readRegistryPackage, concurrency = 6 }) {
  if (!Array.isArray(consumerPaths) || !consumerPaths.length || !Array.isArray(providers)) throw new TypeError("explicit consumers and provider locators required");
  if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 12) throw new TypeError("concurrency must be 1 through 12");
  const consumerFiles = consumerPaths.map(sourceRegistryManifestPath);
  const sources = new Map(), aliases = new Map(), byPath = new Map();
  for (const entry of [...providers, ...consumerPaths.map(path => ({ path }))]) {
    const path = sourceRegistryManifestPath(entry.path);
    let manifest;
    try { manifest = JSON.parse(await readFile(path, "utf8")); } catch (error) { if (error.code === "ENOENT") continue; throw error; }
    const previous = sources.get(manifest.name);
    if (previous && previous.path !== path && !consumerFiles.includes(path)) throw new Error(`duplicate provider identity: ${manifest.name}`);
    const source = { path, dir: dirname(path), manifest };
    sources.set(manifest.name, source); byPath.set(path, source);
    if (entry.name && entry.name !== manifest.name) aliases.set(entry.name, manifest.name);
  }
  const selected = new Map(), required = new Set(), absent = new Set();
  const visit = (name) => {
    name = aliases.get(name) ?? name;
    if (selected.has(name)) return;
    const source = sources.get(name);
    if (!source) { absent.add(name); return; }
    selected.set(name, source);
    for (const field of fields) for (const [dependency, specification] of Object.entries(source.manifest[field] ?? {})) {
      if (!local.test(specification)) continue;
      const canonical = aliases.get(dependency) ?? dependency;
      required.add(canonical); visit(canonical);
    }
  };
  for (const path of consumerFiles) {
    const source = byPath.get(path);
    if (!source) throw new Error(`consumer source not received: ${path}`);
    visit(source.manifest.name);
  }
  for (const name of publishNames) {
    const canonical = aliases.get(name) ?? name;
    required.add(canonical); visit(canonical);
  }
  if (absent.size) return { kind: "npm.source-registry-closure", complete: false, missingProviders: [...absent].sort(), missingEdges: [...selected].flatMap(([name, source]) => fields.flatMap(field => Object.keys(source.manifest[field] ?? {}).filter(dependency => absent.has(dependency)).map(dependency => ({ consumer: name, path: source.path, field, dependency })))), packages: [] };
  const metadata = new Map(), names = [...selected.keys()];
  let cursor = 0;
  await Promise.all(Array.from({ length: concurrency }, async () => {
    while (cursor < names.length) {
      const name = names[cursor++];
      if (!required.has(name)) continue;
      const result = await readRegistry(registry, name);
      if (!result.reachable) throw new Error(`registry metadata unread: ${name}`);
      metadata.set(name, result);
    }
  }));
  const releases = new Map();
  for (const name of required) {
    const source = selected.get(name), result = metadata.get(name);
    const occupied = new Set(Object.keys(result.packument?.versions ?? {}));
    const development = /^(0)\.(\d+)\.\d+-/u.exec(source.manifest.version);
    // A changed development line is not an admitted stable promotion. Start
    // the next 0.x minor line instead of silently downgrading to registry latest.
    const sourceVersion = development ? `0.${Number(development[2]) + 1}.0` : source.manifest.version;
    const candidates = [...occupied, sourceVersion].filter(v => stable.test(v) && Number(v.split(".")[0]) === 0).sort(compare);
    let version = candidates.at(-1) ?? "0.1.0";
    if (occupied.has(version)) { const coordinates = version.split(".").map(Number); coordinates[2]++; version = coordinates.join("."); }
    releases.set(name, version);
  }
  const packages = [];
  for (const [name, source] of selected) {
    const manifest = structuredClone(source.manifest), rewrites = [];
    if (required.has(name)) { manifest.version = releases.get(name); manifest.private = false; }
    for (const field of fields) for (const [dependency, specification] of Object.entries(manifest[field] ?? {})) {
      const canonical = aliases.get(dependency) ?? dependency, version = releases.get(canonical);
      if (!local.test(specification) && version === undefined) continue;
      if (!version) throw new Error(`unplanned provider: ${dependency}`);
      delete manifest[field][dependency]; manifest[field][canonical] = version;
      rewrites.push({ field, name: dependency, canonical, from: specification, to: version });
    }
    delete manifest.workspaces; delete manifest.overrides;
    const missingTargets = [];
    for (const target of packageExportSurfacePaths(manifest)) {
      try { await access(join(source.dir, target)); } catch { missingTargets.push(target); }
    }
    packages.push({ name, path: source.path, publish: required.has(name), from: source.manifest.version, manifest, rewrites, missingTargets, violations: dependencySpecificationViolations(manifest) });
  }
  return { kind: "npm.source-registry-closure", registry, complete: true, consumers: consumerPaths.length, aliases: Object.fromEntries(aliases), packages };
}

const digest = text => createHash("sha256").update(text).digest("hex");
/** Native project policy is part of frozen receiving, alongside its lock. */
export async function nativeRegistryWorkspacePolicy(dir) {
  try { return await readFile(join(dir, 'pnpm-workspace.yaml'), 'utf8'); }
  catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}
function runtimeManifest(manifest) {
  const value = structuredClone(manifest);
  // Repository relocations change source custody metadata independently of
  // the immutable runtime contract; receive the current locator when packing.
  delete value.repository;
  return value;
}
async function receiveCarrierManifest(entry) {
  const manifest = JSON.parse(await readFile(entry.path, "utf8"));
  if (!isDeepStrictEqual(runtimeManifest(manifest), runtimeManifest(entry.manifest))) throw new Error(`source runtime declaration advanced: ${entry.name}`);
  entry.manifest = manifest;
  return manifest;
}

/** Bind a selected carrier to its received authoring bytes and constrain npm's
 * default recursive packlist. An enclosing section never acquires a nested
 * package merely because its source happens to be mounted beneath it. */
export async function prepareSourceRegistryCarriers(plan, { providers = [] } = {}) {
  if (!plan.complete) throw new Error("unresolved source selection");
  const boundaries = [...new Set([...providers.map(p => resolve(p.path.endsWith("package.json") ? dirname(p.path) : p.path)), ...plan.packages.map(p => dirname(p.path))])];
  for (const entry of plan.packages) {
    const dir = dirname(entry.path), text = await readFile(entry.path, "utf8");
    const source = JSON.parse(text);
    if (source.name !== entry.name || source.version !== entry.from) throw new Error(`source identity advanced: ${entry.path}`);
    for (const rewrite of entry.rewrites) if (source[rewrite.field]?.[rewrite.name] !== rewrite.from) throw new Error(`source edge advanced: ${entry.name} ${rewrite.name}`);
    entry.sourceDigest = digest(text);
    if (!entry.publish) continue;
    // npm intentionally excludes a root pnpm-lock.yaml even when files names
    // it. An application declares the carried product and exports that asset;
    // Code generates it from the native lock before judging the final packlist.
    const lockProduct=source.registryConsumption?.frozenLockfile;
    if(lockProduct!==undefined){
      if(lockProduct!=='./release/pnpm-lock.yaml'||source.exports?.['./frozen-lockfile']!==lockProduct)
        throw new Error(`frozen lock product must be the declared release export: ${entry.name}`);
      const lock=await readFile(join(dir,'pnpm-lock.yaml'),'utf8');
      if(!lock.startsWith('lockfileVersion:')||/(?:workspace:|\blink:|\bfile:)/u.test(lock))
        throw new Error(`frozen lock product requires an exact native registry lock: ${entry.name}`);
      await mkdir(join(dir,'release'),{recursive:true});
      if(!(await lstat(join(dir,'release'))).isDirectory())throw new Error('lock product directory must be local');
      try{if(!(await lstat(join(dir,'release','pnpm-lock.yaml'))).isFile())throw new Error('lock product must be a regular file');}
      catch(error){if(error.code!=='ENOENT')throw error;}
      await writeFile(join(dir,'release','pnpm-lock.yaml'),lock);
      entry.generatedProducts=[{path:'release/pnpm-lock.yaml',source:'pnpm-lock.yaml',sha256:digest(lock)}];
    }
    const targets = packageExportSurfacePaths(entry.manifest);
    if (!entry.manifest.files) {
      const files = new Set(["package.json", "README*", "LICENSE*"]);
      for (const target of targets) files.add(target.startsWith("services/") ? dirname(target) : target.includes("/") ? target.split("/")[0] : target);
      for (const asset of ["src", "bin", "scripts", "apps", "content/config", "content/data", "content/schemas", "content/structured-data", "schemas", "conformance", "assets", "public", "web", "dist"]) {
        try { await access(join(dir, asset)); files.add(asset); } catch {}
      }
      entry.manifest.files = [...files];
    }
    entry.embeddedProviders = [];
    for (const child of boundaries) {
      const locator = relative(dir, child).split(sep).join("/");
      if (!locator || locator.startsWith("../") || locator === "..") continue;
      if (targets.some(target => target.startsWith(`${locator}/`))) { entry.embeddedProviders.push(locator); continue; }
      if (!entry.manifest.files.some(pattern => {
        if (pattern.startsWith("!")) return false;
        const prefix = pattern.replace(/^\.\//u, "").split("*")[0].replace(/\/$/u, "");
        return prefix === "" || locator === prefix || locator.startsWith(`${prefix}/`);
      })) continue;
      if (!entry.manifest.files.includes(`!${locator}/**`)) entry.manifest.files.push(`!${locator}/**`);
    }
    entry.missingTargets = [];
    for (const target of targets) { try { await access(join(dir, target)); } catch { entry.missingTargets.push(target); } }
    entry.violations = dependencySpecificationViolations(entry.manifest);
  }
  return plan;
}

/** Apply only an entirely admitted selection, with optimistic source custody.
 * This writes declarations; publication and registry installation are separate. */
export async function applySourceRegistryClosure(plan) {
  if (!plan.complete) throw new Error("unresolved source selection");
  for (const entry of plan.packages) {
    if (entry.missingTargets.length || dependencySpecificationViolations(entry.manifest).length) throw new Error(`unfabricated carrier: ${entry.name}`);
    if (!entry.sourceDigest || digest(await readFile(entry.path, "utf8")) !== entry.sourceDigest) throw new Error(`source bytes advanced: ${entry.path}`);
  }
  const changed = [];
  for (const entry of plan.packages) {
    await writeFile(entry.path, `${JSON.stringify(entry.manifest, null, 2)}\n`);
    const npmrc = join(dirname(entry.path), ".npmrc");
    let text = "";
    try { text = await readFile(npmrc, "utf8"); } catch (error) { if (error.code !== "ENOENT") throw error; }
    // Publication's registry is not the consumer's installation policy.
    // Preserve its explicit public/default and per-scope routing byte for byte.
    // A source without a default retains the original initialization behavior.
    if (!/^registry\s*=/mu.test(text)) {
      await writeFile(npmrc, `registry=${plan.registry}\n${text}`);
      changed.push(npmrc);
    }
    changed.push(entry.path);
  }
  return { kind: "npm.source-registry-closure.applied", manifests: plan.packages.length, changed };
}

/** Port canonical package identities through explicitly selected package bodies.
 * Nested packages are independent owners and are visited only when selected. */
export async function rewriteSourceRegistryAliases(plan, { maxFilesPerPackage = 2000 } = {}) {
  const aliases = new Map(plan.packages.flatMap(entry => entry.rewrites.filter(r => r.name !== r.canonical).map(r => [r.name, r.canonical])));
  const changed = [];
  for (const entry of plan.packages) {
    const root = dirname(entry.path), pending = [root];
    let count = 0;
    while (pending.length) {
      const dir = pending.pop();
      for (const file of await readdir(dir, { withFileTypes: true })) {
        const path = join(dir, file.name);
        if (file.isDirectory()) {
          if (file.name.startsWith(".") || ["node_modules", "data", "services"].includes(file.name)) continue;
          try { await access(join(path, "package.json")); continue; } catch {}
          pending.push(path);
        } else if (file.isFile() && /\.(?:[cm]?js|[cm]?ts)$/u.test(file.name)) {
          if (++count > maxFilesPerPackage) throw new Error(`explicit source body bound exceeded: ${entry.name}`);
          const text = await readFile(path, "utf8");
          let next = text;
          for (const [from, to] of aliases) next = next.replaceAll(from, to);
          if (text !== next) { await writeFile(path, next); changed.push(path); }
        }
      }
    }
  }
  return { kind: "npm.source-registry-closure.identities", aliases: Object.fromEntries(aliases), changed };
}


/** Pack one already selected carrier through the same immutable artifact maker
 * used by source-registry closures. This fabricates and judges the real archive;
 * it neither publishes it nor removes the caller's source directory. */
export async function packRegistryCarrier({ directory, manifest, destination, npmEnvironment = {} } = {}) {
  directory = resolve(directory);
  destination = resolve(destination);
  manifest = await receiveCarrierManifest({ path: join(directory, "package.json"), manifest });
  await mkdir(destination, { recursive: true });
  const packing = await mkdtemp(join(destination, ".pack-"));
  let packed, artifact;
  try {
    const { stdout } = await run("npm", ["pack", "--ignore-scripts", "--workspaces=false", "--json", "--pack-destination", packing], { cwd: directory, env: { ...process.env, ...npmEnvironment }, maxBuffer: 32 * 1024 * 1024, timeout: 60_000 });
    packed = npmPackResult(stdout, manifest);
    const packedPath = join(packing, packed.filename);
    const hash = createHash("sha512").update(await readFile(packedPath)).digest();
    if (`sha512-${hash.toString("base64")}` !== packed.integrity) throw new Error(`npm pack integrity differs from its actual artifact: ${manifest.name}`);
    const store = join(destination, "sha512");
    await mkdir(store, { recursive: true });
    artifact = join(store, `${hash.toString("hex")}.tgz`);
    try { await link(packedPath, artifact); }
    catch (error) { if (error.code !== "EEXIST") throw error; }
    if (!createHash("sha512").update(await readFile(artifact)).digest().equals(hash)) throw new Error(`content-addressed artifact differs from its address: ${manifest.name}`);
    await chmod(artifact, 0o444);
  } finally {
    await rm(packing, { recursive: true, force: true });
  }
  // npm's JSON is log output and may redact apparent credentials in names.
  // Judge the actual archive, rather than treating that log as a file index.
  const listing = await run("tar", ["-tzf", artifact, "--quoting-style=literal"], { maxBuffer: 32 * 1024 * 1024 });
  const files = listing.stdout.split("\n").filter(path => path && !path.endsWith("/")).map(path => path.replace(/^package\//u, ""));
  const surface = carrierSurfaceViolations(manifest, files, { pathFormat: "package-relative" });
  const carrier = await mkdtemp(join(destination, ".packed-"));
  let secrets;
  try {
    await run("tar", ["-xzf", artifact, "-C", carrier, "--strip-components=1"], { maxBuffer: 1024 * 1024 });
    secrets = await secretBearingContentPaths(carrier, files);
  } finally { await rm(carrier, { recursive: true, force: true }); }

  const refusal = surface.length || secrets.length || files.some(path => SECRET_PATH.test(path))
    ? { name: manifest.name, surface, credentialContent: secrets.length > 0, credentialPath: files.some(path => SECRET_PATH.test(path)) }
    : null;
  return { name: manifest.name, version: manifest.version, path: join(directory, "package.json"), manifest,
    artifact, shasum: createHash("sha1").update(await readFile(artifact)).digest("hex"),
    integrity: packed.integrity, size: packed.size, unpackedSize: packed.unpackedSize, files, refusal };
}

/** Fabricate immutable artifacts without substituting local dependencies or
 * running package suites. Actual exported files and credential custody are
 * judged on npm's final packlist. Registry receiving follows separately. */
export async function packSourceRegistryClosure(plan, { destination, onProgress = () => {} } = {}) {
  if (!destination || !plan.complete) throw new TypeError("admitted plan and artifact destination required");
  // npm executes inside each carrier; resolve the caller's locator before that
  // working-directory change so a relative destination retains its meaning.
  destination = resolve(destination);
  for (const entry of plan.packages.filter(entry => entry.publish)) {
    if (!Array.isArray(entry.manifest.files) || entry.missingTargets.length || dependencySpecificationViolations(entry.manifest).length) throw new Error(`provider carrier selection is not prepared: ${entry.name}`);
    await receiveCarrierManifest(entry);
  }
  await mkdir(destination, { recursive: true });
  const receipt = { kind: "npm.source-registry-closure.packed", registry: plan.registry, packages: [], refusals: [] };
  for (const entry of plan.packages.filter(entry => entry.publish)) {
    const dir = dirname(entry.path), manifest = await receiveCarrierManifest(entry);
    const staging = await mkdtemp(join(destination, ".carrier-"));
    const excludes = ["node_modules", "node_modules/**", "**/node_modules", "**/node_modules/**", ".git", ".git/**", ...manifest.files.filter(pattern => pattern.startsWith("!")).map(pattern => pattern.slice(1))];
    const selection = new Set(["package.json"]);
    for (const pattern of manifest.files.filter(pattern => !pattern.startsWith("!"))) {
      for await (const file of glob([pattern, `${pattern}/**/*`], { cwd: dir, withFileTypes: true, exclude: excludes })) {
        if (!file.isDirectory()) selection.add(relative(dir, join(file.parentPath, file.name)));
      }
    }
    for (const file of selection) {
      await mkdir(dirname(join(staging, file)), { recursive: true });
      await cp(join(dir, file), join(staging, file), { preserveTimestamps: true, verbatimSymlinks: true });
    }
    await writeFile(join(staging, "package.json"), `${JSON.stringify(manifest, null, 2)}\n`);
    let result;
    try { result = await packRegistryCarrier({ directory: staging, manifest, destination }); }
    finally { await rm(staging, { recursive: true, force: true }); }
    const { refusal, ...packed } = result;
    if (refusal) receipt.refusals.push(refusal);
    receipt.packages.push({ ...packed, path: entry.path });
    await onProgress(receipt, entry.name);
  }
  return receipt;
}

/** Publish only the fixed artifacts, then independently fetch each exact
 * release through configured registry access and compare SHA512. A conflicting
 * occupied version is retained and refused; it is never overwritten. */
export async function publishSourceRegistryClosure(packed, { receivingDirectory, tag, onProgress = () => {} } = {}) {
  if (packed.refusals.length || !receivingDirectory) throw new Error("fabricated, unrefused artifacts and receiving directory required");
  await mkdir(receivingDirectory, { recursive: true });
  const receipt = { kind: "npm.source-registry-closure.received", registry: packed.registry, packages: [] };
  for (const entry of packed.packages) {
    const actualIntegrity = `sha512-${createHash("sha512").update(await readFile(entry.artifact)).digest("base64")}`;
    if (actualIntegrity !== entry.integrity) throw new Error(`packed artifact changed: ${entry.name}`);
    let metadata = await readRegistryPackageVersion(packed.registry, entry.name, entry.version);
    if (!metadata.reachable) throw new Error(`registry unread: ${entry.name}`);
    if (!metadata.found) {
      await publishConfiguredNpmRegistryArtifact({ registry: packed.registry, name: entry.name, version: entry.version, artifact: entry.artifact, tag });
      metadata = await readRegistryPackageVersion(packed.registry, entry.name, entry.version);
    }
    if (!metadata.found || !metadata.manifest.dist?.integrity?.split(/\s+/u).includes(entry.integrity)) throw new Error(`occupied release differs from selected artifact: ${entry.name}@${entry.version}`);
    const receiving = await mkdtemp(join(receivingDirectory, ".download-"));
    try {
      try {
        await receiveRegistryTarball({ registry: packed.registry, tarball: metadata.manifest.dist.tarball, integrity: entry.integrity, destination: join(receiving, "release.tgz") });
      } catch (error) {
        if (!/HTTP (401|403)/u.test(error.message)) throw error;
        await downloadConfiguredNpmRegistryTarball({ registry: packed.registry, name: entry.name, version: entry.version, integrity: entry.integrity, destination: join(receiving, "release.tgz"), npmEnvironment: { npm_config_cache: join(receiving, "cache") } });
      }
    } finally { await rm(receiving, { recursive: true, force: true }); }
    receipt.packages.push({ name: entry.name, version: entry.version, integrity: entry.integrity, artifactDownloaded: true });
    await onProgress(receipt, entry.name);
  }
  return receipt;
}

// Receiving holds one PNPM installation at a time per process and admits it
// only below the caller's cgroup memory stall. Parallel installs past a cgroup's
// memory.high do not finish sooner: once working sets exceed the budget, reclaim
// evicts what the next instruction needs and every process in the cgroup stalls.
let receivingTail = Promise.resolve();
const receiveExclusively = work => { const turn = receivingTail.then(work); receivingTail = turn.catch(() => {}); return turn; };

/** npm excludes the canonical root lock. Restore only an application's declared
 * exported frozen product before native PNPM receiving; never resolve a graph. */
export async function receiveNativeRegistryLock(dir,manifest,{materialize=false}={}){
  const path=join(dir,'pnpm-lock.yaml');
  let canonical;
  try{canonical=await readFile(path,'utf8');}catch(error){if(error.code!=='ENOENT')throw error;}
  const product=manifest.registryConsumption?.frozenLockfile;
  if(product!==undefined){
    if(product!=='./release/pnpm-lock.yaml'||manifest.exports?.['./frozen-lockfile']!==product)
      throw new Error('frozen lock product must be the declared release export');
    let carried;
    try{carried=await readFile(join(dir,'release','pnpm-lock.yaml'),'utf8');}
    catch(error){if(error.code!=='ENOENT'||canonical===undefined)throw error;}
    if(carried!==undefined){
      if(canonical!==undefined&&canonical!==carried)throw new Error('native and carried locks differ');
      if(canonical===undefined){if(materialize)await writeFile(path,carried,{flag:'wx'});canonical=carried;}
    }
  }
  if(canonical===undefined)throw new Error('native frozen consumer lock is absent');
  return canonical;
}

/** Linux PSI `some avg10` for the calling process's own cgroup v2 memory,
 * else the system figure, else null where the kernel exposes neither. */
async function readOwnMemoryPressure() {
  const paths = ["/proc/pressure/memory"];
  try {
    const entry = (await readFile("/proc/self/cgroup", "utf8")).split("\n").find(line => line.startsWith("0::"));
    if (entry) paths.unshift(join("/sys/fs/cgroup", entry.slice(3), "memory.pressure"));
  } catch {}
  for (const path of paths) {
    try {
      const match = /^some avg10=(\d+(?:\.\d+)?)/mu.exec(await readFile(path, "utf8"));
      if (match) return Number(match[1]);
    } catch {}
  }
  return null;
}

async function awaitMemoryHeadroom({ readMemoryPressure, memoryPressureCeiling, admissionTimeout, pause }) {
  const deadline = Date.now() + admissionTimeout;
  for (let pressure = await readMemoryPressure(); pressure !== null && pressure >= memoryPressureCeiling; pressure = await readMemoryPressure()) {
    if (Date.now() >= deadline) throw Object.assign(new Error(`memory pressure ${pressure} held at or above ${memoryPressureCeiling} for ${admissionTimeout} ms`), { code: "memory-pressure" });
    await pause(5_000);
  }
}

/** Receive the actual selected PNPM entry and its original shim supplier.
 * Arbitrary executable wrappers are not an authenticated manager identity.
 */
async function receiveArtifactPnpmProvider(program, arguments_, cwd) {
  let entry = program === process.execPath && isAbsolute(arguments_[0] ?? "") ? arguments_[0] : program;
  if (!isAbsolute(entry)) {
    if (entry.includes("/")) throw new TypeError("artifact receiving requires an absolute native manager entry");
    let selected;
    for (const path of (process.env.PATH ?? "").split(":")) {
      if (!isAbsolute(path)) continue;
      try { await access(join(path, entry)); selected = join(path, entry); break; } catch {}
    }
    if (!selected) throw new TypeError("native manager executable is not resolved");
    entry = selected;
  }
  entry = await realpath(entry);
  let stat = await lstat(entry);
  if (!stat.isFile() || stat.size > 1024 * 1024) throw new TypeError("native PNPM entry must be a bounded regular file");
  let bytes = await readFile(entry);
  const targets = [...bytes.toString("utf8").matchAll(/^#\s*cmd-shim-target=(.+)$/gmu)];
  if (targets.length === 1) {
    entry = await realpath(resolve(dirname(entry), targets[0][1])); stat = await lstat(entry);
    if (!stat.isFile() || stat.size > 1024 * 1024) throw new TypeError("native PNPM shim target is not bounded");
    bytes = await readFile(entry);
  }
  const root = dirname(dirname(entry)), manifestPath = join(root, "package.json");
  const manifestBytes = await readFile(manifestPath), manifest = JSON.parse(manifestBytes);
  if (manifest.name !== "pnpm" || manifest.version !== "11.28.5" || typeof manifest.bin?.pnpm !== "string"
    || await realpath(join(root, manifest.bin.pnpm)) !== entry) throw new TypeError("artifact receiving requires qualified native PNPM11.28.5");
  const distPath = join(root, "dist", "pnpm.mjs"), distStat = await lstat(distPath);
  if (!distStat.isFile() || distStat.size > 64 * 1024 * 1024) throw new TypeError("native PNPM shim supplier exceeds its bound");
  const dist = await readFile(distPath);
  const version = (await run(program, [...arguments_, "--version"], { cwd, timeout: 10000, maxBuffer: 65536 })).stdout.trim();
  if (version !== manifest.version) throw new TypeError("native selected PNPM version differs from its provider");
  return { manager: { name: "pnpm", version, entrySHA256: digest(bytes) },
    provider: { entry, entrySHA256: digest(bytes), manifestPath, manifestSHA256: digest(manifestBytes),
      distPath, distSHA256: digest(dist), shimTargetFormat: "pnpm11-cmd-shim-target" } };
}

/** Resolve each consumer independently through its configured registry, then
 * receive a frozen installation. Fresh-release admission is limited to exact
 * identities whose actual registry bytes were independently downloaded. */
export async function receiveSourceRegistryConsumers({ consumerPaths, releases, artifactReceiving = [], artifactReceiptDirectory, logDirectory, pnpm = "pnpm", pnpmArguments = [], onProgress = () => {}, readMemoryPressure = readOwnMemoryPressure, memoryPressureCeiling = 10, admissionTimeout = 1_800_000, installationTimeout = 300_000, pause = delay }) {
  if (!Array.isArray(consumerPaths) || !Array.isArray(releases) || !logDirectory) throw new TypeError("explicit consumers, received releases and log directory required");
  if (!Array.isArray(artifactReceiving) || artifactReceiving.length > 64) throw new TypeError("bounded native artifact receiving selection required");
  if (artifactReceiving.length && (typeof artifactReceiptDirectory !== "string" || !isAbsolute(artifactReceiptDirectory)
    || await realpath(artifactReceiptDirectory) !== artifactReceiptDirectory || !(await lstat(artifactReceiptDirectory)).isDirectory()))
    throw new TypeError("native artifact receiving requires an explicit real owner receipt directory");
  if (releases.some(release => release.artifactDownloaded !== true || !release.integrity?.startsWith("sha512-"))) throw new Error("release admission requires independent artifact receiving");
  if (!(memoryPressureCeiling > 0 && memoryPressureCeiling <= 100)) throw new TypeError("memory pressure ceiling must be a stall percentage above zero");
  if (!Number.isSafeInteger(installationTimeout) || installationTimeout < 1 || installationTimeout > 7_200_000)
    throw new TypeError("native frozen installation timeout must be a positive integer no greater than 7200000 ms");
  await mkdir(logDirectory, { recursive: true });
  const admission = ["--config.minimumReleaseAgeStrict=true", ...releases.map(release => `--config.minimumReleaseAgeExclude=${release.name}@${release.version}`)];
  const receipt = { kind: "npm.source-registry-closure.consumers", packages: [], refusals: [] };
  const admittedConsumers = [], selectedNames = new Set(), selectedPaths = new Set(), requestedNames = new Set();
  // Admit the *whole* original consumer set and every committed lock before
  // native installation of any member. A later invalid package cannot leave
  // earlier members of the same enterprise receiving wave modified.
  for (const selected of consumerPaths) {
    let path, manifest, manifestText;
    try {
      path = sourceRegistryManifestPath(selected);
      manifestText = await readFile(path, "utf8");
      manifest = JSON.parse(manifestText);
      if(typeof manifest.name!=="string"||
        !/^(?:@[a-z0-9._-]+\/[a-z0-9._-]+|[a-z0-9._-]+)$/u.test(manifest.name)||
        selectedPaths.has(path)||selectedNames.has(manifest.name))
        throw new TypeError("unique native consumer identity required");
      requestedNames.add(manifest.name);
      if (dependencySpecificationViolations(manifest).length)
        throw new Error(`consumer declarations are not exact: ${manifest.name}`);
      const minimumReleaseAge = manifest.registryConsumption?.minimumReleaseAge;
      if (minimumReleaseAge !== undefined &&
        (!Number.isSafeInteger(minimumReleaseAge) || minimumReleaseAge < 0))
        throw new TypeError("minimum release age must be nonnegative integer minutes");
      const dir = dirname(path), committedLock = await receiveNativeRegistryLock(dir,manifest);
      const workspacePolicy = await nativeRegistryWorkspacePolicy(dir);
      if (/(?:workspace:|\blink:|\bfile:)/u.test(committedLock))
        throw new Error("committed consumer lock contains a local dependency binding");
      const artifacts = artifactReceiving.filter(entry => entry.consumer === manifest.name);
      const artifactNames = new Set();
      for (const entry of artifacts) {
        if (!entry || Object.keys(entry).some(key => !["consumer", "name", "version", "archive", "limits", "registry"].includes(key))
          || artifactNames.has(entry.name) || manifest.dependencies?.[entry.name] !== entry.version
          || !releases.some(release => release.name === entry.name && release.version === entry.version && release.integrity === entry.archive?.integrity))
          throw new TypeError("artifact selection must match a unique exact received native consumer dependency");
        if (typeof entry.registry !== "string" || !entry.registry) throw new TypeError("original artifact registry identity required");
        const packed = await readRegistryArchiveMembers({ ...entry.archive, limits: entry.limits });
        const packedManifest = JSON.parse(packed.archive.manifestText);
        if (packedManifest.name !== entry.name || packedManifest.version !== entry.version)
          throw new TypeError("received native artifact identifies another release");
        artifactNames.add(entry.name);
      }
      selectedPaths.add(path);selectedNames.add(manifest.name);
      admittedConsumers.push({path,manifest,manifestText,dir,committedLock,workspacePolicy,minimumReleaseAge,artifacts,
        log:join(logDirectory,`${manifest.name.replaceAll("/", "-").replace(/^@/u, "")}.log`)});
    } catch (error) {
      receipt.refusals.push({name:manifest?.name??null,path:path??null,
        reason:error.code??error.message});
    }
  }
  if (artifactReceiving.some(entry => !entry || !requestedNames.has(entry.consumer))) receipt.refusals.push({ name: null, path: null, reason: "artifact receiving names an unselected consumer" });
  if (receipt.refusals.length) {
    for (const refused of receipt.refusals) await onProgress(receipt, refused.name);
    return receipt;
  }
  for (const {path,manifest,manifestText,dir,committedLock,workspacePolicy,minimumReleaseAge,artifacts,log} of admittedConsumers) {
    // PNPM command-line arrays REPLACE the committed workspace array. The
    // consumer's authored policy already owns all its exact release exceptions;
    // overlaying only this publication batch drops earlier qualified suppliers.
    // Without a workspace policy, retain the explicit received-release fallback.
    const policyAdmission = workspacePolicy === null ? admission : ["--config.minimumReleaseAgeStrict=true"];
    const settings = minimumReleaseAge === undefined ? policyAdmission :
      [...policyAdmission,`--config.minimumReleaseAge=${minimumReleaseAge}`];
    let output = "", staging, previousInstallation;
    const artifactReceipts = [];
    try {
      if(await receiveNativeRegistryLock(dir,manifest,{materialize:true})!==committedLock)
        throw new Error('native frozen lock advanced after preflight');
      // PNPM does not remove arbitrary links left by an earlier workspace.
      // Receive in a fresh native project, then replace only its disposable
      // installation. Preserve the previous tree separately for disposition.
      staging=await mkdtemp(join(resolve(logDirectory),'.registry-install-'));
      await writeFile(join(staging,'package.json'),manifestText);
      await writeFile(join(staging,'pnpm-lock.yaml'),committedLock);
      if(workspacePolicy!==null)await writeFile(join(staging,'pnpm-workspace.yaml'),workspacePolicy);
      try{await cp(join(dir,'.npmrc'),join(staging,'.npmrc'));}catch(error){if(error.code!=='ENOENT')throw error;}
      const args = ["--dir", staging, ...settings, "install", ...(workspacePolicy===null?["--ignore-workspace"]:[]), "--ignore-scripts",
        "--reporter=append-only", "--frozen-lockfile"];
      const artifactProvider = artifacts.length ? await receiveArtifactPnpmProvider(pnpm, pnpmArguments, staging) : null;
      const nativeRequest = { program: pnpm, arguments: [...pnpmArguments, ...args], cwd: staging, timeout: installationTimeout, manifestSHA256: digest(manifestText), lockSHA256: digest(committedLock), workspacePolicySHA256: workspacePolicy === null ? null : digest(workspacePolicy) };
      const installation = await receiveExclusively(async () => {
        await awaitMemoryHeadroom({ readMemoryPressure, memoryPressureCeiling, admissionTimeout, pause });
        return run(pnpm, [...pnpmArguments, ...args], {
          cwd: staging, env: { ...process.env, CI: "true", PNPM_MAX_WORKERS: process.env.PNPM_MAX_WORKERS ?? "1" },
          timeout: installationTimeout, maxBuffer: 32 * 1024 * 1024
        });
      });
      output += `frozen\n${installation.stdout}${installation.stderr}\n`;
      const [receivedLock, receivedManifest] = await Promise.all([
        readFile(join(dir, "pnpm-lock.yaml"), "utf8"), readFile(path, "utf8")
      ]);
      if (receivedLock !== committedLock || receivedManifest !== manifestText)
        throw new Error("native frozen receiving changed committed consumer declarations");
      if(await nativeRegistryWorkspacePolicy(dir)!==workspacePolicy||await nativeRegistryWorkspacePolicy(staging)!==workspacePolicy)
        throw new Error('native workspace policy changed during frozen receiving');
      if(await readFile(join(staging,'pnpm-lock.yaml'),'utf8')!==committedLock||
        await readFile(join(staging,'package.json'),'utf8')!==manifestText)
        throw new Error('native frozen staging changed selected declarations');
      // A successful process exit can still leave an incomplete import tree.
      // Preserve the prior consumer until PNPM's native graph is present.
      await access(join(staging,'node_modules','.modules.yaml'));
      for(const dependency of Object.keys(manifest.dependencies??{}))await access(join(staging,'node_modules',dependency,'package.json'));
      if (artifacts.length) {
        const afterProvider = await receiveArtifactPnpmProvider(pnpm, pnpmArguments, staging);
        if (!isDeepStrictEqual(artifactProvider, afterProvider)) throw new Error("native manager provider changed during installation");
        const nativeRecord = { kind: "npm.native-frozen-installation", request: nativeRequest,
          result: { code: 0, signal: null, stdout: installation.stdout, stderr: installation.stderr }, provider: artifactProvider };
        const nativeText = `${JSON.stringify(nativeRecord, null, 2)}\n`;
        const nativePath = join(artifactReceiptDirectory, basename(staging) + ".native-installation.json");
        await writeFile(nativePath, nativeText, { flag: "wx", mode: 0o600 });
        const nativeInstallation = async () => ({ installation: { kind: "native-package-installation", status: 0, platform: process.platform,
          manager: artifactProvider.manager, requestSHA256: digest(JSON.stringify(nativeRequest)), receipt: nativePath, receiptSHA256: digest(nativeText),
          manifestSHA256: digest(manifestText), lockSHA256: digest(committedLock), normalization: "posix-package-files-0644-0755" }, provider: artifactProvider.provider });
        for (const entry of artifacts) {
          const comparison = await receiveInstalledArtifactMembers({ registry: entry.registry, name: entry.name, version: entry.version,
            archive: entry.archive, limits: entry.limits, packageRoot: join(staging, "node_modules", entry.name), installationRoot: staging,
            binDirectory: join(staging, "node_modules", ".bin") }, { nativeInstallation });
          artifactReceipts.push(comparison);
          if (!comparison.ok) throw new Error("native installed artifact member receiving refused");
        }
      }
      const modules=join(dir,'node_modules');
      try{
        if(!(await lstat(modules)).isDirectory())throw new Error('previous installation is not a local directory');
        previousInstallation=staging+'.previous-node-modules';
        await rename(modules,previousInstallation);
      }catch(error){if(error.code!=='ENOENT')throw error;}
      try{await rename(join(staging,'node_modules'),modules);}
      catch(error){if(previousInstallation)await rename(previousInstallation,modules);throw error;}
      receipt.packages.push({ name: manifest.name, version: manifest.version, path, frozenInstall: true,
        manifestDigest: digest(manifestText), lockDigest: digest(committedLock),
        workspacePolicyDigest: workspacePolicy===null?null:digest(workspacePolicy),
        minimumReleaseAge: minimumReleaseAge ?? "pnpm-default", log,
        ...(artifactReceipts.length ? { artifactReceiving: artifactReceipts } : {}),
        ...(previousInstallation?{previousInstallation}:{} ) });
    } catch (error) {
      output += `${error.stdout ?? ""}${error.stderr ?? ""}\n${error.message}\n`;
      receipt.refusals.push({ name: manifest.name, path, log, reason: error.code ?? error.signal ?? "command-failed", ...(artifactReceipts.length ? { artifactReceiving: artifactReceipts } : {}) });
    }finally{if(staging)await rm(staging,{recursive:true,force:true});}
    await writeFile(log, output);
    await onProgress(receipt, manifest.name);
  }
  return receipt;
}

export { preparePublicationCarrierManifest } from "./publication-carrier-manifest.mjs";

export { receiveSourceArchiveMembers, readRegistryArchiveMembers, receiveInstalledArtifactMembers } from "./artifact-member-receiving.mjs";
