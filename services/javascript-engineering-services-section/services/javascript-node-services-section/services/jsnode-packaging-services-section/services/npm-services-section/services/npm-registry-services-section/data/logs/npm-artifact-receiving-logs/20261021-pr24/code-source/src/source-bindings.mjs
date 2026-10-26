import { lstat, mkdir, readFile, realpath, rename, rm, rmdir, symlink } from "node:fs/promises";
import { createHash } from "node:crypto";
import { isDeepStrictEqual } from "node:util";
import { executeJavascriptNodeCommand } from "@red-cup-engineering/execute-javascript-node-command-service";
import { dependencySpecificationViolations, isExactSemver } from "./dependency-policy.mjs";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";

const INSTALL_COMMAND = /\bnpm\s+(?:ci|install|i)\b/u;

function packageTarget(directory, name) {
  if (name.startsWith("@")) {
    const [scope, leaf] = name.split("/");
    return join(directory, "node_modules", scope, leaf);
  }
  return join(directory, "node_modules", name);
}

function within(root, path) {
  const relation = relative(root, path);
  return relation === "" || (!relation.startsWith(`..${sep}`) && relation !== "..");
}

async function manifestAt(directory) {
  const manifest = JSON.parse(await readFile(join(directory, "package.json"), "utf8"));
  if (typeof manifest.name !== "string" || typeof manifest.version !== "string") throw new TypeError(`source binding package at ${directory} has no name/version`);
  return manifest;
}

async function assertNoInstallLifecycle(packages) {
  for (const pkg of packages) {
    const manifest = await manifestAt(pkg.dir);
    if (manifest.name !== pkg.name || manifest.version !== pkg.version) throw new TypeError(`planned source ${pkg.name}@${pkg.version} does not match ${pkg.dir}`);
    for (const script of pkg.lifecycle) {
      if (INSTALL_COMMAND.test(manifest.scripts?.[script] ?? "")) throw new TypeError(`source-bound verification refuses ${pkg.name} lifecycle ${script}: npm installation is not permitted while bindings are active`);
    }
  }
}

/**
 * Temporarily resolves planned internal edges to their exact source directories.
 * It never changes manifests or locks; every replaced install target is restored,
 * including when the callback fails.
 */
export async function withSourceBindings(plan, run) {
  if (typeof run !== "function") throw new TypeError("source-bound verification requires a callable operation");
  await assertNoInstallLifecycle(plan.packages);
  const providers = new Map(plan.packages.map((pkg) => [pkg.name, pkg]));
  const bindings = [];
  try {
    for (const consumer of plan.packages) {
      for (const dependency of plan.dependencies[consumer.name] ?? []) {
        const provider = providers.get(dependency);
        if (provider === undefined) continue;
        const target = packageTarget(consumer.dir, dependency);
        const nodeModules = join(consumer.dir, "node_modules");
        if (!within(nodeModules, target)) throw new TypeError(`source binding target escapes node_modules: ${target}`);
        const backup = `${target}.source-binding-backup-${process.pid}-${bindings.length}`;
        let replaced = false;
        try { await lstat(target); replaced = true; } catch (error) { if (error?.code !== "ENOENT") throw error; }
        await mkdir(dirname(target), { recursive: true });
        bindings.push({ target, backup, replaced });
        if (replaced) await rename(target, backup);
        await symlink(provider.dir, target, "dir");
      }
    }
    return await run();
  } finally {
    for (const binding of bindings.reverse()) {
      await rm(binding.target, { recursive: true, force: true });
      if (binding.replaced) await rename(binding.backup, binding.target);
    }
  }
}


const sourceDigest = bytes => createHash("sha256").update(bytes).digest("hex");
const activeDevelopmentRoots = new Set();

/** An authored test-host composition, never an amendment to a registry contract. */
export function developmentRootSelfRecipe(manifest) {
  const qa = manifest?.registryConsumption?.sourceQualification;
  if (qa === undefined) return null;
  if (qa?.kind !== "development-root-self" || !qa.testLibrary || !qa.selector
    || Object.keys(qa).some(key => !["kind", "testLibrary", "selector"].includes(key))
    || Object.keys(qa.testLibrary).some(key => !["name", "version", "peerVersion"].includes(key))
    || Object.keys(qa.selector).some(key => !["variable", "value"].includes(key)))
    throw new TypeError("source qualification must declare the development root-self context");
  if (typeof manifest.name !== "string" || !/^(?:@[a-z0-9._-]+\/[a-z0-9._-]+|[a-z0-9._-]+)$/u.test(manifest.name)
    || dependencySpecificationViolations(manifest).length || !isExactSemver(manifest.version))
    throw new TypeError("development source QA preserves the exact canonical dependency contract");
  for (const field of ["dependencies", "devDependencies", "optionalDependencies", "peerDependencies"])
    if (Object.hasOwn(manifest[field] ?? {}, manifest.name))
      throw new TypeError("development self context is not a canonical dependency edge");
  const host = qa.testLibrary;
  if (typeof host.name !== "string" || host.name === manifest.name
    || manifest.devDependencies?.[host.name] !== host.version
    || !isExactSemver(host.version) || !isExactSemver(host.peerVersion)
    || ["dependencies", "optionalDependencies", "peerDependencies"].some(field => Object.hasOwn(manifest[field] ?? {}, host.name)))
    throw new TypeError("root-self test library must be one exact development-only supplier");
  if (!/^[A-Z][A-Z0-9_]{1,63}$/u.test(qa.selector.variable ?? "")
    || /^(?:NODE|NPM|PNPM|GIT|HTTP|HTTPS|ALL|NO|LD|DYLD)_/u.test(qa.selector.variable)
    || ["PATH", "HOME", "TMP", "TEMP", "TMPDIR", "SHELL", "BASH_ENV", "ENV"].includes(qa.selector.variable)
    || qa.selector.value !== host.name)
    throw new TypeError("development selector must name only the declared test library");
  if (manifest.exports?.["./package.json"] !== "./package.json")
    throw new TypeError("root-self QA requires the actual source identity export");
  return Object.freeze({ kind: qa.kind, testLibrary: Object.freeze({ ...host }), selector: Object.freeze({ ...qa.selector }) });
}

/** Receive the native peer diagnostic without converting a missing peer into
 * registry compatibility. Only the explicitly authored development edge may be
 * unresolved; every other peer issue remains a refusal. */
export function receiveDevelopmentRootSelfPeerReport(manifest, report) {
  const recipe = developmentRootSelfRecipe(manifest);
  if (!recipe || !report || typeof report !== "object" || Array.isArray(report)
    || Object.keys(report).length !== 1 || !Object.hasOwn(report, "."))
    throw new TypeError("development QA requires the complete native root peer report");
  const project = report["."], missing = project?.missing;
  const issue = missing?.[manifest.name];
  if (!project || Object.keys(project).some(key => !["bad", "missing", "conflicts", "intersections"].includes(key))
    || !project.bad || Object.keys(project.bad).length !== 0
    || !missing || Object.keys(missing).length !== 1
    || !Array.isArray(issue) || issue.length !== 1
    || issue[0]?.optional !== false || issue[0]?.wantedRange !== recipe.testLibrary.peerVersion
    || issue[0]?.parents?.length !== 1
    || issue[0].parents[0]?.name !== recipe.testLibrary.name
    || issue[0].parents[0]?.version !== recipe.testLibrary.version
    || !Array.isArray(project.conflicts) || project.conflicts.length !== 0
    || !project.intersections || Object.keys(project.intersections).length !== 1
    || project.intersections[manifest.name] !== recipe.testLibrary.peerVersion)
    throw new TypeError("development QA refuses undeclared or additional native peer issues");
  return Object.freeze({ kind: "npm.development-root-self.peer-frontier", nativeReport: report,
    authoredPeerSatisfied: false, registryPeerClosureReceived: false,
    selection: Object.freeze({ law: "explicit-development-root-self-source-qualification",
      consumer: recipe.testLibrary, provider: Object.freeze({ name: manifest.name, version: manifest.version }),
      scope: "Functional source interoperability assay; unchanged authored peer requirement remains unsatisfied" }) });
}

async function absent(path) {
  try { await lstat(path); return false; } catch (error) { if (error.code === "ENOENT") return true; throw error; }
}

async function unredirectedDirectory(path) {
  if (!(await lstat(path)).isDirectory() || await realpath(path) !== path)
    throw new TypeError("development source context directory is redirected: " + path);
}

// Each phase gets a fresh native resolver. A require.resolve cache populated by
// the old fallback must not be mistaken for the provider used by fresh tests.
function nativeEsmResolution(directory, specifiers) {
  if (!specifiers.length || specifiers.length > 2049) throw new TypeError("development source requires bounded public runtime subpaths");
  const source = `import {realpathSync} from 'node:fs';import {fileURLToPath} from 'node:url';
const resolve=specifier=>{try{return {specifier,path:realpathSync(fileURLToPath(import.meta.resolve(specifier)))};}catch(error){return {specifier,error:error.code};}};
console.log(JSON.stringify(JSON.parse(process.argv[1]).map(resolve)));`;
  const { result } = executeJavascriptNodeCommand({ type: "JavascriptNodeCommandExecutionRequest", version: 1,
    command: process.execPath, arguments: ["--input-type=module", "-e", source, JSON.stringify(specifiers)],
    directory, environment: {}, input: null }, { timeoutMilliseconds: 5000 });
  if (result.status !== 0 || result.signal !== null || result.error || Buffer.byteLength(result.stdout) > 512 * 1024)
    throw new TypeError("fresh native development provider resolution failed");
  return JSON.parse(result.stdout);
}

function nativeDevelopmentResolution(library, manifest) {
  const subpaths = Object.keys(manifest.exports).filter(key => (key === "." || key.startsWith("./")) && key !== "./package.json" && !key.includes("*"));
  if (!subpaths.length) throw new TypeError("development source requires a public runtime subpath");
  return nativeEsmResolution(library, [manifest.name + "/package.json", ...subpaths.map(key => key === "." ? manifest.name : manifest.name + key.slice(1))]);
}

async function legacyDevelopmentFallback(modules, manifest, recipe, resolution) {
  const identity = resolution[0];
  if (identity.error === "ERR_MODULE_NOT_FOUND") return null;
  if (identity.error || typeof identity.path !== "string") throw new TypeError("development source peer identity is unreadable");
  const shared = join(modules, ".pnpm", "node_modules", manifest.name);
  const virtualStore = join(modules, ".pnpm");
  for (let at = dirname(shared); at !== modules; at = dirname(at)) await unredirectedDirectory(at);
  if (!within(virtualStore, identity.path) || !(await lstat(shared)).isSymbolicLink()
    || await realpath(shared) !== dirname(identity.path))
    throw new TypeError("development source refuses a direct, redirected or foreign peer fallback");
  const bytes = await readFile(identity.path), prior = JSON.parse(bytes);
  if (!(await lstat(identity.path)).isFile() || prior.name !== manifest.name || !isExactSemver(prior.version)
    || prior.version === recipe.testLibrary.peerVersion || prior.version === manifest.version)
    throw new TypeError("development source cannot replace a compatible or conflicting peer");
  for (const item of resolution) if (item.path && !within(dirname(identity.path), item.path))
    throw new TypeError("development fallback runtime subpath escapes its package");
  return { path: identity.path, shared, name: prior.name, version: prior.version,
    manifestDigest: sourceDigest(bytes), sourceCommit: prior.gitHead ?? null };
}

/** Reuse the original binding conductor for one missing own-root peer only.
 * Canonical source, registry suppliers and their authored peer declarations stay
 * intact. This returns SOURCE QA evidence, not registry or runtime receiving.
 * The caller owns finite execution/resource admission and the source inventory.
 */
export async function withDevelopmentRootSelfContext({ directory, manifest, manifestDigest }, run) {
  const recipe = developmentRootSelfRecipe(manifest);
  if (!recipe || typeof run !== "function" || !isAbsolute(directory) || resolve(directory) !== directory
    || !/^[a-f0-9]{64}$/u.test(manifestDigest ?? ""))
    throw new TypeError("explicit exact development source context required");
  await unredirectedDirectory(directory);
  const modules = join(directory, "node_modules");
  await unredirectedDirectory(modules);
  if (!(await lstat(join(modules, ".modules.yaml"))).isFile()) throw new TypeError("native development installation is absent");
  if (activeDevelopmentRoots.has(directory)) throw new TypeError("development source context is already active");
  const original = new Map();
  for (const name of ["package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", ".npmrc"]) {
    try {
      const file = join(directory, name), stat = await lstat(file);
      if (!stat.isFile() || await realpath(file) !== file) throw new TypeError("development source input is redirected");
      original.set(name, await readFile(file));
    } catch (error) { if (error.code !== "ENOENT" || name === "package.json") throw error; original.set(name, null); }
  }
  if (sourceDigest(original.get("package.json")) !== manifestDigest
    || !isDeepStrictEqual(JSON.parse(original.get("package.json")), manifest))
    throw new TypeError("development source identity changed");
  const selectedEntry = nativeEsmResolution(directory, [recipe.testLibrary.name])[0];
  if (!selectedEntry.path) throw new TypeError("actual development test-library ESM entry is unavailable");
  const entry = selectedEntry.path;
  if (!within(modules, entry)) throw new TypeError("development test supplier escapes the native installation");
  let library = dirname(entry), libraryManifest, libraryBytes;
  for (let depth = 0; depth < 32 && within(modules, library); depth++) {
    try {
      libraryBytes = await readFile(join(library, "package.json"));
      const candidate = JSON.parse(libraryBytes);
      if (candidate.name === recipe.testLibrary.name) { libraryManifest = candidate; break; }
    } catch (error) { if (error.code !== "ENOENT") throw error; }
    library = dirname(library);
  }
  if (!libraryManifest || libraryManifest.version !== recipe.testLibrary.version
    || libraryManifest.peerDependencies?.[manifest.name] !== recipe.testLibrary.peerVersion)
    throw new TypeError("actual test-library identity or authored peer differs");
  const targets = [join(modules, manifest.name), join(library, "node_modules", manifest.name)];
  const libraryModules = libraryManifest.name.startsWith("@") ? dirname(dirname(library)) : dirname(library);
  const nativePeerTarget = join(libraryModules, manifest.name);
  if (!await absent(nativePeerTarget)) throw new TypeError("root-self QA only fills an absent native peer; direct provider is already installed");
  const createdParents = [];
  for (const [index, target] of targets.entries()) {
    const boundary = index === 0 ? directory : library;
    if (!within(boundary, target) || !await absent(target)) throw new TypeError("development self target is not absent and confined; root-self QA only fills an absent source peer");
    for (let at = dirname(target); at !== boundary; at = dirname(at)) {
      if (await absent(at)) createdParents.push(at);
      else await unredirectedDirectory(at);
    }
  }
  const previousResolution = nativeDevelopmentResolution(library, manifest);
  const legacyFallback = await legacyDevelopmentFallback(modules, manifest, recipe, previousResolution);
  const source = { name: manifest.name, version: manifest.version, dir: directory, lifecycle: ["test", "test:coordination", "prepack"] };
  const consumer = { name: libraryManifest.name, version: libraryManifest.version, dir: library, lifecycle: [] };
  const plan = { packages: [source, consumer], dependencies: { [source.name]: [source.name], [consumer.name]: [source.name] } };
  let result, failure, provider;
  activeDevelopmentRoots.add(directory);
  try {
    result = await withSourceBindings(plan, async () => {
      const boundResolution = nativeDevelopmentResolution(library, manifest);
      const identity = boundResolution[0].path;
      if (identity !== join(directory, "package.json")) throw new TypeError("native test-library peer does not resolve to this source root");
      for (const item of boundResolution.slice(1)) if (!item.path || !within(directory, item.path) || within(modules, item.path))
        throw new TypeError("native test-library runtime subpath does not resolve to this source root");
      provider = { name: manifest.name, version: manifest.version, sourceRoot: directory, manifestPath: identity, manifestDigest,
        publicResolution: boundResolution, previousResolution, legacyFallback };
      return run(Object.freeze({ kind: "npm.development-root-self.context", provider: Object.freeze(provider), environment: Object.freeze({ [recipe.selector.variable]: recipe.selector.value }) }));
    });
  } catch (error) { failure = error; }
  try {
    for (const [name, bytes] of original) {
      if (bytes === null ? !await absent(join(directory, name)) : !(await readFile(join(directory, name))).equals(bytes))
        throw new TypeError("development source QA changed canonical input: " + name);
    }
    if (!(await readFile(join(library, "package.json"))).equals(libraryBytes)) throw new TypeError("development source QA changed its registry supplier");
    for (const target of targets) if (!await absent(target)) throw new TypeError("development self binding was not restored");
    if (!await absent(nativePeerTarget)) throw new TypeError("development source QA changed its absent native peer target");
    if (!isDeepStrictEqual(nativeDevelopmentResolution(library, manifest), previousResolution))
      throw new TypeError("development source QA changed prior native provider resolution");
    if (legacyFallback && (!isDeepStrictEqual(await legacyDevelopmentFallback(modules, manifest, recipe, previousResolution), legacyFallback)))
      throw new TypeError("development source QA changed its legacy fallback identity");
    for (const path of [...new Set(createdParents)].sort((a, b) => b.length - a.length)) {
      try { await rmdir(path); } catch (error) { if (error.code !== "ENOENT") throw error; }
    }
  } catch (error) { failure = failure ? new AggregateError([failure, error], "development source QA and custody both failed") : error; }
  finally { activeDevelopmentRoots.delete(directory); }
  if (failure) throw failure;
  return Object.freeze({ kind: "npm.development-root-self.source-qa", source: Object.freeze(provider),
    testLibrary: recipe.testLibrary, authoredPeer: recipe.testLibrary.peerVersion, selector: recipe.selector,
    authoredPeerSatisfied: false, registryPeerClosureReceived: false,
    canonicalInputsUnchanged: true, bindingsRestored: true, result,
    scope: "Functional development source QA only; not registry closure, artifact publication, portable runtime or operating acceptance" });
}
