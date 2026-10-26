import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { lstat, mkdir, readFile, readdir, realpath, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, isAbsolute, join, relative, sep } from "node:path";
import * as nativePath from "node:path";
import { classifyLockfileResolvedUrls } from "./lockfile-registry-classification.mjs";
import { developmentRootSelfRecipe } from "./source-bindings.mjs";

// The dedicated worker owns this process group, including npm and its build/test
// descendants. A terminal result cannot leave those writers in deleted staging.
const run = (program, args, options) => new Promise((accept, reject) => {
  // execFile does not forward detached to spawn. Use Node's actual process-group
  // entrance, so the finite timeout owns descendants as well as the wrapper.
  const child = spawn(program, args, { cwd: options.cwd, env: options.env, detached: true, shell: false, stdio: ["ignore", "pipe", "pipe"] });
  const chunks = { stdout: [], stderr: [] };
  let size = 0, failure;
  const stop = () => { try { process.kill(-child.pid, "SIGKILL"); } catch (error) { if (error.code !== "ESRCH") throw error; } };
  const timer = setTimeout(() => {
    failure = Object.assign(new Error("source build worker timed out"), { code: "ETIMEDOUT", killed: true });
    try { stop(); } catch (error) { failure = error; }
  }, options.timeout);
  for (const stream of ["stdout", "stderr"]) child[stream].on("data", bytes => {
    size += bytes.length;
    if (size <= options.maxBuffer) chunks[stream].push(bytes);
    else if (!failure) {
      failure = Object.assign(new Error("source build worker output exceeds its bound"), { code: "ERR_CHILD_PROCESS_STDIO_MAXBUFFER", killed: true });
      try { stop(); } catch (error) { failure = error; }
    }
  });
  child.on("error", error => { failure = error; });
  child.on("close", async (code, signal) => {
    clearTimeout(timer);
    try {
      if (child.pid !== undefined) {
        stop();
        const deadline = Date.now() + 2000;
        for (;;) {
          try { process.kill(-child.pid, 0); }
          catch (error) { if (error.code === "ESRCH") break; throw error; }
          if (Date.now() >= deadline) throw new Error("source worker process group did not quiesce");
          await new Promise(accept => setTimeout(accept, 10));
        }
      }
    } catch (error) {
      error.code = "BUILD_WORKER_CUSTODY_UNCERTAIN"; error.workerProcessGroup = child.pid; reject(error); return;
    }
    const stdout = Buffer.concat(chunks.stdout).toString("utf8"), stderr = Buffer.concat(chunks.stderr).toString("utf8");
    if (failure || code !== 0 || signal !== null) {
      const error = failure ?? new Error("source build worker did not complete successfully");
      Object.assign(error, { code: failure?.code ?? code, signal, stdout, stderr }); reject(error);
    } else accept({ stdout, stderr });
  });
});

const qualifiedProducts = new WeakMap();
const digest = bytes => createHash("sha256").update(bytes).digest("hex");
const literal = path => typeof path === "string" && /^[A-Za-z0-9_-][A-Za-z0-9_./-]*$/u.test(path)
  && path.split("/").every(part => part && part !== "." && part !== "..");
const glob = path => typeof path === "string" && /^[A-Za-z0-9_][A-Za-z0-9_./*?-]*\.test\.[cm]?js$/u.test(path)
  && path.split("/").every(part => part && part !== "." && part !== "..");
const exact = /^\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?$/u;

/** A caller-owned native cache is reusable input, never a source or install receipt. */
export async function validateSourceBuildCacheRoot(cacheRoot, directory) {
  if (typeof cacheRoot !== "string" || !isAbsolute(cacheRoot))
    throw new TypeError("source cacheRoot must be an absolute private owned directory");
  const stat = await lstat(cacheRoot);
  if (!stat.isDirectory() || stat.uid !== process.getuid() || (stat.mode & 0o077) !== 0
    || await realpath(cacheRoot) !== cacheRoot)
    throw new TypeError("source cacheRoot must be an unredirected private owned directory");
  for (const name of ["npm", "npm/_cacache", "npm/_logs", "pnpm-metadata", "pnpm-store", "yarn"]) {
    const path = join(cacheRoot, name);
    let child;
    try { child = await lstat(path); }
    catch (error) { if (error.code === "ENOENT") continue; throw error; }
    if (!child.isDirectory() || child.uid !== process.getuid() || await realpath(path) !== path)
      throw new TypeError("source cacheRoot native cache directories must be owned and unredirected");
  }
  const source = await realpath(directory);
  const inside = (parent, child) => {
    const path = relative(parent, child);
    return path === "" || (path !== ".." && !path.startsWith(".." + sep) && !isAbsolute(path));
  };
  if (inside(source, cacheRoot) || inside(cacheRoot, source))
    throw new TypeError("source cacheRoot must be separate from the source directory");
  return cacheRoot;
}

/** Only the already admitted literal native test command; never parse arbitrary shell. */
function nativeTestTargets(manifest, script = "test") {
  const test = /^(?:npm run build && )?node --test(?: --test-concurrency=[1-9][0-9]*)? (.+)$/u.exec(manifest.scripts?.[script] ?? "");
  if (!test || !test[1].split(" ").every(glob)) throw new TypeError("publication build requires confined native Node test globs");
  return test[1].split(" ");
}

/** Existing Code gate classes, never a general lifecycle executor.
 * Direct TypeScript/npm builds and explicit native root-self development QA are supported.
 */
export function sourcePublicationBuildRecipe(manifest) {
  const development = developmentRootSelfRecipe(manifest);
  if (development) {
    if (manifest.scripts?.build !== undefined) throw new TypeError("development root-self QA admits native JavaScript source only");
    nativeTestTargets(manifest);
    if (manifest.scripts?.["test:coordination"] !== undefined) nativeTestTargets(manifest, "test:coordination");
    if (manifest.packageManager !== undefined && !/^pnpm@\d+\.\d+\.\d+$/u.test(manifest.packageManager))
      throw new TypeError("development root-self QA preserves the owner's native PNPM lock");
    return { developmentRootSelf: development };
  }
  if (manifest.scripts?.build === undefined) return null;
  const recipe = /^tsc -p (tsconfig(?:\.build)?\.json)$/u.exec(manifest.scripts.build);
  if (!recipe) return null;
  if (typeof nativePath.matchesGlob !== "function") throw new TypeError("source build qualification requires the native path glob matcher"); // Other recipes retain the original pack-only/refusal path; never execute them.
  nativeTestTargets(manifest);
  if (manifest.packageManager !== undefined && !/^npm@\d+\.\d+\.\d+$/u.test(manifest.packageManager))
    throw new TypeError("publication build requires the owner's npm lock");
  for (const field of ["dependencies", "devDependencies", "optionalDependencies", "peerDependencies"])
    for (const [name, version] of Object.entries(manifest[field] ?? {}))
      if (!exact.test(version)) throw new TypeError("publication build requires exact registry dependencies: " + name);
  if (!exact.test(manifest.devDependencies?.typescript ?? "")) throw new TypeError("publication build requires an exact build-only TypeScript supplier");
  return { configuration: recipe[1] };
}

/** The original gate's source-only worker is deliberately selected. It cannot publish,
 * bump a version, repin a consumer or write its applying EAVT receipt on this path.
 * No service credential or inherited npm configuration reaches its child.
 */
export async function runSourceBuildWorker({ directory, registry, scratch, cacheRoot, timeoutMilliseconds = 300_000 }) {
  if (process.platform !== "linux") throw new TypeError("source build qualification requires the Linux worker custody contract");
  if (!Number.isSafeInteger(timeoutMilliseconds) || timeoutMilliseconds < 1 || timeoutMilliseconds > 300_000)
    throw new TypeError("source worker timeout must be 1 through 300000 milliseconds");
  if (cacheRoot !== undefined) await validateSourceBuildCacheRoot(cacheRoot, directory);
  const home = join(scratch, "build-home"), userconfig = join(home, "npmrc"), globalconfig = join(home, "global-npmrc");
  await mkdir(home, { recursive: true, mode: 0o700 });
  await writeFile(userconfig, "", { flag: "wx", mode: 0o600 });
  await writeFile(globalconfig, "", { flag: "wx", mode: 0o600 });
  const gate = fileURLToPath(new URL("../scripts/publish-package.mjs", import.meta.url));
  const environment = Object.fromEntries(["PATH", "LANG", "LC_ALL", "TZ", "SystemRoot", "WINDIR"].filter(key => process.env[key] !== undefined).map(key => [key, process.env[key]]));
  let result;
  try { result = await run(process.execPath, [gate, "--qualify-build", "--package", directory, "--registry", registry,
    ...(cacheRoot === undefined ? [] : ["--qualification-cache-root", cacheRoot])], {
    cwd: scratch, timeout: timeoutMilliseconds, maxBuffer: 16 * 1024 * 1024,
    env: { ...environment, HOME: home, TMPDIR: scratch, TEMP: scratch, TMP: scratch,
      npm_config_userconfig: userconfig, npm_config_globalconfig: globalconfig,
      npm_config_ignore_scripts: "true", npm_config_update_notifier: "false", npm_config_audit: "false", npm_config_fund: "false" },
  }); } catch (error) {
    // A completed gate refusal has a typed report on stdout. Preserve its
    // actual reason; timeout, signal and malformed output remain process failures.
    if (error.code === 2 && !error.signal && error.killed !== true) {
      try { const report = JSON.parse(error.stdout); if (report.outcome === "refused") return report; } catch {}
    }
    throw error;
  }
  return JSON.parse(result.stdout);
}

/** Receive Code's generated products while preserving every authored input.
 * The caller supplies the exact Git reader's regular-file entries, never a live checkout scan.
 */
export async function qualifySourcePublicationBuild({ directory, manifest, entries, registry, scratch, codeGate = runSourceBuildWorker }) {
  const recipe = sourcePublicationBuildRecipe(manifest);
  if (!recipe) return null;
  if (typeof nativePath.matchesGlob !== "function") throw new TypeError("source build qualification requires the native path glob matcher");
  if (!isAbsolute(directory) || await realpath(directory) !== directory || !(await lstat(directory)).isDirectory())
    throw new TypeError("source build requires an unredirected absolute source directory");
  let sourceBytes = 0;
  if (!Array.isArray(entries) || !entries.length || entries.length > 100_000) throw new TypeError("bounded committed source entries required");
  for (const entry of entries) {
    if (typeof entry?.path !== "string" || entry.path.startsWith("/") || /[\\\0\r\n]/u.test(entry.path)
      || entry.path.split("/").some(part => !part || part === "." || part === "..")
      || !["100644", "100755"].includes(entry.mode) || !(entry.bytes instanceof Uint8Array))
      throw new TypeError("source build entries must be confined regular committed files");
    sourceBytes += entry.bytes.length;
    if (sourceBytes > 64 * 1024 * 1024) throw new RangeError("source build input byte bound exceeded");
  }
  const authored = new Map(entries.map(entry => [entry.path, entry]));
  if (authored.size !== entries.length || !authored.has("package.json")
    || JSON.stringify(JSON.parse(Buffer.from(authored.get("package.json").bytes).toString("utf8"))) !== JSON.stringify(manifest))
    throw new TypeError("source build requires unique entries and the exact committed manifest");
  if (recipe.developmentRootSelf) {
    for (const path of [".pnpmfile.cjs", ".pnpmfile.mjs", "package-lock.json", "yarn.lock"])
      if (authored.has(path)) throw new TypeError("unsupported development source QA configuration: " + path);
    if (!authored.has("pnpm-lock.yaml") || !authored.has("pnpm-workspace.yaml"))
      throw new TypeError("development source QA requires the authored native PNPM lock and policy");
    const receiveSource = async () => {
      for (const [path, entry] of authored) {
        const file = join(directory, path), stat = await lstat(file);
        if (!stat.isFile() || await realpath(file) !== file || digest(await readFile(file)) !== digest(entry.bytes)
          || Boolean(stat.mode & 0o111) !== (entry.mode === "100755"))
          throw new TypeError("development source QA changed authored input: " + path);
      }
    };
    await receiveSource();
    const result = await codeGate({ directory, registry, scratch });
    if (result?.outcome === "refused") throw new TypeError("Code publication gate refused: " + JSON.stringify(result.refusal));
    const sourceQa = result?.state?.developmentSourceQa;
    if (result?.kind !== "npm.source-build-qualification" || result.outcome !== "source-build-qualified"
      || result.package !== manifest.name || result.state?.sourceVersion !== manifest.version
      || result.steps?.some(step => step.step >= 3)
      || ![1, 2].every(step => result.steps?.some(row => row.step === step && row.ok === true))
      || sourceQa?.kind !== "npm.development-root-self.source-qa" || sourceQa.source?.name !== manifest.name
      || sourceQa.source?.version !== manifest.version || sourceQa.source?.manifestDigest !== digest(authored.get("package.json").bytes)
      || sourceQa.canonicalInputsUnchanged !== true || sourceQa.bindingsRestored !== true
      || sourceQa.authoredPeerSatisfied !== false || sourceQa.registryPeerClosureReceived !== false
      || result.steps.find(row => row.step === 1).evidence?.lockfile?.kind !== "npm.development-root-self.installation"
      || result.steps.find(row => row.step === 1).evidence?.lockfile?.peerFrontier?.kind !== "npm.development-root-self.peer-frontier"
      || result.steps.find(row => row.step === 1).evidence?.lockfile?.peerFrontier?.authoredPeerSatisfied !== false
      || result.steps.find(row => row.step === 1).evidence?.lockfile?.registryPeerClosureReceived !== false)
      throw new TypeError("Code gate did not qualify this exact development source context");
    const count = result.steps.find(row => row.step === 2).evidence?.testCount;
    if (![count?.tests, count?.pass, count?.fail].every(Number.isSafeInteger)
      || count.tests < 1 || count.pass < 1 || count.fail !== 0 || count.pass > count.tests)
      throw new TypeError("Code development source QA did not execute passing required tests");
    await receiveSource();
    let paths = 0, bytes = 0;
    const receiveProducts = async at => {
      for (const entry of await readdir(at, { withFileTypes: true })) {
        const file = join(at, entry.name), path = relative(directory, file).split("\\").join("/");
        if (path === "node_modules") continue;
        if (++paths > 100_000) throw new RangeError("development source QA path bound exceeded");
        if (entry.isDirectory()) await receiveProducts(file);
        else {
          if (!entry.isFile() || !authored.has(path)) throw new TypeError("development source QA added undeclared product: " + path);
          bytes += (await lstat(file)).size;
          if (bytes > 64 * 1024 * 1024) throw new RangeError("development source QA byte bound exceeded");
        }
      }
    };
    await receiveProducts(directory);
    const qualification = { producer: "@red-cup-engineering/npm-workspace-publication-service", operation: "qualify-source-publication-build", apply: false,
      sourceVersion: manifest.version, authoredFiles: authored.size, paths, bytes, steps: result.steps, developmentSourceQa: sourceQa,
      scope: "Development source QA; canonical registry, final artifact and installed/runtime receiving remain separate" };
    qualifiedProducts.set(qualification, { directory, products: [], qualificationSHA256: digest(JSON.stringify(qualification)) });
    return qualification;
  }
  if (!authored.has("package-lock.json")) throw new TypeError("publication build requires a committed npm lock");
  for (const path of [".pnpmfile.cjs", ".pnpmfile.mjs", "pnpm-workspace.yaml", "pnpm-lock.yaml", "yarn.lock"])
    if (authored.has(path)) throw new TypeError("unsupported publication build configuration: " + path);
  if (authored.has(".npmrc")) {
    const text = Buffer.from(authored.get(".npmrc").bytes).toString("utf8").trim();
    if (text !== `registry=${registry.replace(/\/$/u, "")}` && text !== `registry=${registry.replace(/\/$/u, "")}/`)
      throw new TypeError("publication build project configuration must retain the canonical registry only");
  }
  const lock = JSON.parse(Buffer.from(authored.get("package-lock.json").bytes).toString("utf8"));
  const compiler = lock.packages?.["node_modules/typescript"];
  if (classifyLockfileResolvedUrls(lock, registry).houseScopedNotCanonical > 0
    || Object.values(lock.packages ?? {}).some(entry => entry?.link === true || /^(?:file|link|workspace|git|git\+[^:]*|ssh):/u.test(entry?.resolved ?? "")))
    throw new TypeError("publication build lock must retain exact registry supplier routing");
  if (![2, 3].includes(lock.lockfileVersion) || lock.name !== manifest.name || lock.version !== manifest.version
    || lock.packages?.[""]?.name !== manifest.name || lock.packages?.[""]?.version !== manifest.version
    || lock.packages?.[""]?.devDependencies?.typescript !== manifest.devDependencies.typescript
    || compiler?.version !== manifest.devDependencies.typescript || !/^sha512-[A-Za-z0-9+/]+=*$/u.test(compiler.integrity ?? ""))
    throw new TypeError("publication build compiler and source identity must match the committed npm lock");
  const configuration = authored.get(recipe.configuration);
  if (!configuration) throw new TypeError("publication build configuration is not committed");
  const config = JSON.parse(Buffer.from(configuration.bytes).toString("utf8")), options = config.compilerOptions ?? {};
  if (config.extends !== undefined || config.references !== undefined
    || (config.files !== undefined && (!Array.isArray(config.files) || !config.files.length || !config.files.every(literal)))
    || !literal(options.rootDir) || !literal(options.outDir)
    || options.rootDir === options.outDir || options.outDir === "node_modules" || options.outDir.startsWith("node_modules/") || options.outDir.startsWith(options.rootDir + "/")
    || ["outFile", "declarationDir", "tsBuildInfoFile", "plugins", "rootDirs", "typeRoots", "baseUrl", "paths"].some(key => options[key] !== undefined)
    || !Array.isArray(config.include) || !config.include.length
    || [...config.include, ...(config.exclude ?? [])].some(path => typeof path !== "string" || path.startsWith("/") || /[\\\0]/u.test(path) || path.split("/").some(part => part === "..")))
    throw new TypeError("publication compiler inputs and output must remain in the direct source owner");
  const output = options.outDir;
  if ([...authored.keys()].some(path => path === output || path.startsWith(output + "/")))
    throw new TypeError("publication build cannot overwrite committed products");
  async function receiveAuthored() {
    for (const [path, entry] of authored) {
      const file = join(directory, path), stat = await lstat(file);
      if (!stat.isFile() || digest(await readFile(file)) !== digest(entry.bytes) || Boolean(stat.mode & 0o111) !== (entry.mode === "100755"))
        throw new TypeError("publication build changed authored source: " + path);
    }
  }
  await receiveAuthored();
  const result = await codeGate({ directory, registry, scratch });
  if (result?.outcome === "refused") throw new TypeError("Code publication gate refused: " + JSON.stringify(result.refusal));
  if (result?.kind !== "npm.source-build-qualification" || result.outcome !== "source-build-qualified" || result.package !== manifest.name || result.state?.sourceVersion !== manifest.version
    || result.steps?.some(step => step.step >= 3) || ![1, 2].every(step => result.steps?.some(row => row.step === step && row.ok === true)))
    throw new TypeError("Code publication gate did not qualify this source without applying effects");
  const count = result.steps.find(row => row.step === 2).evidence?.testCount;
  if (![count?.tests, count?.pass, count?.fail].every(Number.isSafeInteger)
    || count.tests < 1 || count.pass < 1 || count.fail !== 0 || count.pass > count.tests)
    throw new TypeError("Code publication gate did not execute passing required tests");
  await receiveAuthored();
  const receivedFiles = [];
  let paths = 0, bytes = 0;
  async function receive(at) {
    for (const entry of await readdir(at, { withFileTypes: true })) {
      const file = join(at, entry.name), path = relative(directory, file).split("\\").join("/");
      if (path === "node_modules") continue;
      if (++paths > 100_000) throw new RangeError("publication build output path bound exceeded");
      if (entry.isDirectory()) await receive(file);
      else if (!entry.isFile()) throw new TypeError("publication build produced a nonregular carrier");
      else {
        receivedFiles.push(path);
        bytes += (await lstat(file)).size;
        if (bytes > 64 * 1024 * 1024) throw new RangeError("publication build output byte bound exceeded");
        if (!authored.has(path) && !path.startsWith(output + "/")) throw new TypeError("publication build added undeclared source: " + path);
      }
    }
  }
  await receive(directory);
  const testTargets = nativeTestTargets(manifest).map(pattern => ({ pattern,
    files: receivedFiles.filter(path => nativePath.matchesGlob(path, pattern)) }));
  for (const target of testTargets) if (target.files.length === 0)
    throw new TypeError("publication build declared test target has no received file: " + target.pattern);
  const qualification = { producer: "@red-cup-engineering/npm-workspace-publication-service", operation: "qualify-source-publication-build", apply: false,
    configuration: recipe.configuration, sourceVersion: manifest.version, steps: result.steps, testTargets, authoredFiles: authored.size, paths, bytes };
  const products = [];
  for (const path of receivedFiles.filter(path => !authored.has(path))) {
    const file = join(directory, path), stat = await lstat(file), body = await readFile(file);
    if (!stat.isFile() || await realpath(file) !== file) throw new TypeError("qualified product became redirected");
    products.push({ path, mode: stat.mode & 0o777, sha256: digest(body), bytes: body.length });
  }
  qualifiedProducts.set(qualification, { directory, products, qualificationSHA256: digest(JSON.stringify(qualification)) });
  return qualification;
}

/** Only a retained result of this actual in-process producer can open this port.
 * JSON reports preserve evidence but cannot manufacture qualified products.
 */
export async function receiveQualifiedPublicationBuildProducts(qualification, { directory }) {
  const held = qualifiedProducts.get(qualification);
  if (!held || held.directory !== directory || held.qualificationSHA256 !== digest(JSON.stringify(qualification))) throw new TypeError("original in-process Code build qualification required");
  const provenance = { producer: qualification.producer, operation: qualification.operation,
    sourceVersion: qualification.sourceVersion, qualificationSHA256: held.qualificationSHA256 };
  const products = [];
  for (const expected of held.products) {
    const file = join(directory, expected.path), stat = await lstat(file);
    if (!stat.isFile() || stat.size !== expected.bytes) throw new TypeError("qualified Code product size changed");
    const bytes = await readFile(file);
    if (!stat.isFile() || await realpath(file) !== file || (stat.mode & 0o777) !== expected.mode
      || bytes.length !== expected.bytes || digest(bytes) !== expected.sha256)
      throw new TypeError("qualified Code product changed: " + expected.path);
    products.push({ path: expected.path, bytes, mode: expected.mode, source: { ...provenance } });
  }
  return products;
}
