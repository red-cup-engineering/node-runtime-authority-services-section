import path from "node:path";
import { applyExactSourceEdits } from "./exact-source-edits.mjs";
import { sha256Digest, sha256Hex } from "@red-cup-engineering/cryptographic-computer-data-engineering-services-section/integrity";

const posix = path.posix;


function repositoryPath(value, name) {
  if (typeof value !== "string" || value === "" || value.startsWith("/") || value.split("/").includes("..") || posix.normalize(value) !== value) {
    throw new TypeError(`${name} must be a normalized repository-relative path`);
  }
  return value;
}

function relocations(value) {
  if (!Array.isArray(value) || value.length === 0) throw new TypeError("relocations must be a non-empty array");
  const result = value.map((entry) => Object.freeze({ from: repositoryPath(entry?.from, "relocation.from"), to: repositoryPath(entry?.to, "relocation.to") }));
  const seen = new Set();
  for (const entry of result) {
    if (entry.from === entry.to || seen.has(entry.from) || seen.has(entry.to)) throw new TypeError("relocations must have distinct source and destination paths");
    seen.add(entry.from); seen.add(entry.to);
  }
  for (const left of result) for (const right of result) if (left !== right && (left.from.startsWith(`${right.from}/`) || left.to.startsWith(`${right.to}/`))) {
    throw new TypeError("relocation prefixes must not overlap");
  }
  return result.sort((left, right) => right.from.length - left.from.length);
}

function relocated(value, moves) {
  for (const move of moves) if (value === move.from || value.startsWith(`${move.from}/`)) return `${move.to}${value.slice(move.from.length)}`;
  return value;
}

function relativeSpecifier(fromFile, target) {
  const value = posix.relative(posix.dirname(fromFile), target);
  return value === "" ? "./" : value.startsWith(".") ? value : `./${value}`;
}

function referenceReplacement(value, sourcePath, relocatedSourcePath, repositoryRoot, moves, bareRelative = false) {
  const filePrefix = value.startsWith("file:") ? "file:" : "";
  const reference = filePrefix ? value.slice(filePrefix.length) : value;
  if (reference === "" || /[\\\r\n]/u.test(reference) || /^[a-z][a-z0-9+.-]*:/iu.test(reference)) return value;
  const [, pathname, suffix] = /^([^?#]*)(.*)$/u.exec(reference);
  let target;
  let render;
  if (pathname.startsWith(repositoryRoot + "/")) {
    target = pathname.slice(repositoryRoot.length + 1);
    render = (next) => `${repositoryRoot}/${next}`;
  } else if (pathname.startsWith("/")) {
    return value;
  } else if (pathname.startsWith(".") || bareRelative || filePrefix) {
    target = posix.normalize(posix.join(posix.dirname(sourcePath), pathname));
    if (target === ".." || target.startsWith("../")) return value;
    render = (next) => relativeSpecifier(relocatedSourcePath, next);
  } else {
    target = pathname;
    render = (next) => next;
  }
  const nextTarget = relocated(target, moves);
  if (nextTarget === target && sourcePath === relocatedSourcePath) return value;
  return `${filePrefix}${render(nextTarget)}${suffix}`;
}

function jsonStrings(text) {
  JSON.parse(text);
  const spans = [];
  for (let index = 0; index < text.length; index += 1) {
    if (text[index] !== '"') continue;
    const start = index;
    index += 1;
    while (index < text.length) {
      if (text[index] === "\\") { index += 2; continue; }
      if (text[index] === '"') break;
      index += 1;
    }
    if (index >= text.length) throw new SyntaxError("unterminated JSON string");
    const end = index + 1;
    let following = end;
    while (/\s/u.test(text[following] ?? "")) following += 1;
    if (text[following] !== ":") spans.push({ start, end, value: JSON.parse(text.slice(start, end)), encode: JSON.stringify });
  }
  return spans;
}

function markdownLinks(text) {
  const spans = [];
  const expression = /!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)/gu;
  for (const match of text.matchAll(expression)) {
    const value = match[1];
    const start = match.index + match[0].indexOf(value);
    spans.push({ start, end: start + value.length, value, encode: (next) => next });
  }
  return spans;
}

function admittedModuleLiterals(text, references) {
  if (!Array.isArray(references)) throw new TypeError("module sources require parser-admitted literal references");
  return references.map((reference) => {
    if (!Number.isSafeInteger(reference?.start) || !Number.isSafeInteger(reference?.end) || reference.start < 0 || reference.end > text.length || reference.end <= reference.start || typeof reference.value !== "string") {
      throw new TypeError("module reference must carry an admitted literal span and value");
    }
    const raw = text.slice(reference.start, reference.end);
    const quote = raw[0];
    if ((quote !== "'" && quote !== '"') || raw.at(-1) !== quote || raw.slice(1, -1) !== reference.value) throw new TypeError("module reference no longer matches its admitted literal");
    return { start: reference.start, end: reference.end, value: reference.value, encode: (next) => `${quote}${next.replaceAll("\\", "\\\\").replaceAll(quote, `\\${quote}`)}${quote}` };
  });
}

/**
 * Plans exact path-reference edits for an explicitly admitted active JSON
 * configuration or Markdown document. Journals, snapshots, user data and
 * content-addressed records are rejected at this boundary rather than scanned.
 */
export function planActivePathRelocation(source, options) {
  if (source?.type !== "active-path-reference-source" || source.version !== 1 || !["json", "markdown", "module"].includes(source.kind)) throw new TypeError("source must be an active JSON, Markdown, or module path-reference source");
  const sourcePath = repositoryPath(source.path, "source.path");
  if (typeof source.text !== "string") throw new TypeError("source.text must be a string");
  if (typeof options?.repositoryRoot !== "string" || !options.repositoryRoot.startsWith("/")) throw new TypeError("repositoryRoot must be an absolute path");
  const moves = relocations(options.relocations);
  const relocatedSourcePath = relocated(sourcePath, moves);
  const references = source.kind === "json" ? jsonStrings(source.text) : source.kind === "markdown" ? markdownLinks(source.text) : admittedModuleLiterals(source.text, source.references);
  const edits = references.map((reference) => {
    const replacement = referenceReplacement(reference.value, sourcePath, relocatedSourcePath, options.repositoryRoot.replace(/\/$/u, ""), moves, source.kind === "markdown");
    return replacement === reference.value ? null : { start: reference.start, end: reference.end, text: reference.encode(replacement) };
  }).filter(Boolean);
  return Object.freeze({ kind: "active-path-relocation.plan", version: 1, source: Object.freeze({ path: sourcePath, digest: sha256Digest(source.text), kind: source.kind }), relocatedPath: relocatedSourcePath, relocations: Object.freeze(moves), edits: Object.freeze(edits.map((edit) => Object.freeze(edit))) });
}

/** Applies an admitted pure plan to the exact input bytes; filesystem moves are deliberately outside this module. */
export function applyActivePathRelocation(source, plan) {
  if (plan?.kind !== "active-path-relocation.plan" || plan.version !== 1) throw new TypeError("not an active path relocation plan");
  if (source?.path !== plan.source.path || typeof source.text !== "string" || sha256Digest(source.text) !== plan.source.digest) throw new Error("source changed after the path relocation plan was admitted");
  return Object.freeze({ kind: "active-path-relocation.receipt", version: 1, source: plan.source, relocatedPath: plan.relocatedPath, editCount: plan.edits.length, text: applyExactSourceEdits(source.text, plan.edits) });
}

/** Rewrites the pathname carrier only; callers use it to project a file move before applying text edits. */
export function relocateRepositoryPath(fileName, replacements) {
  return relocated(repositoryPath(fileName, "fileName"), relocations(replacements));
}
