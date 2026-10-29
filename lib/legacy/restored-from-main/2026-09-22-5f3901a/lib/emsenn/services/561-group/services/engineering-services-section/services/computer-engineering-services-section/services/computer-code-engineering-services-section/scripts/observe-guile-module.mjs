import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const READER = fileURLToPath(new URL("./read-guile-module.scm", import.meta.url));

/** Project a Guile module observation into its declared module relations. */
export function guixModuleClaims(modules) {
  if (!Array.isArray(modules)) throw new TypeError("Guix module records must be an array");
  const claims = [];
  for (const module of modules) {
    if (module?.id === undefined) throw new TypeError("Guix module records require id");
    for (const used of module.uses ?? []) claims.push(Object.freeze({
      subject: module.id,
      predicate: "uses-module",
      object: used,
      evidence: Object.freeze({ substrate: "guix-module", resource: module.id }),
    }));
    for (const exported of module.exports ?? []) claims.push(Object.freeze({
      subject: module.id,
      predicate: "exports-binding",
      object: exported,
      evidence: Object.freeze({ substrate: "guix-module", resource: module.id }),
    }));
  }
  return Object.freeze(claims);
}

function text(value, label) {
  if (typeof value !== "string" || value.length === 0) throw new TypeError(`${label} must be a non-empty string`);
  return value;
}

function runNativeReader(source, { guix = "guix", spawnImpl = spawn } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawnImpl(guix, ["repl", "-q", "--", READER], { stdio: ["pipe", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) return reject(new Error(`Guile module reader exited ${code}: ${stderr.trim()}`));
      try { resolve(JSON.parse(stdout)); }
      catch (error) { reject(new Error(`Guile module reader returned invalid JSON: ${error.message}`)); }
    });
    child.stdin.end(source);
  });
}

/** Read explicit source bytes with Guile's own reader; never evaluate them. */
export async function observeGuileModuleSource({ source, path, guix, spawnImpl } = {}) {
  text(source, "source");
  text(path, "path");
  const reading = await runNativeReader(source, { guix, spawnImpl });
  if (reading === null || typeof reading !== "object" || !Array.isArray(reading.uses) || !Array.isArray(reading.exports)) {
    throw new TypeError("Guile module reader returned an invalid observation");
  }
  const digest = `sha256:${createHash("sha256").update(source).digest("hex")}`;
  const moduleName = typeof reading.module === "string" ? reading.module : null;
  return Object.freeze({
    kind: "guile.module-observation",
    id: moduleName ?? path,
    module: moduleName,
    uses: Object.freeze(reading.uses.map((value) => text(value, "used module"))),
    exports: Object.freeze(reading.exports.map((value) => text(value, "exported binding"))),
    evidence: Object.freeze({
      substrate: "guile-source",
      resource: path,
      sha256: digest,
      bytes: Buffer.byteLength(source),
      reader: "guix-repl-native-read",
      evaluated: false,
    }),
  });
}

/** Filesystem face over the same native source reader. */
export async function observeGuileModuleFile(path, options = {}) {
  const source = await readFile(path, "utf8");
  return observeGuileModuleSource({ source, path, ...options });
}
