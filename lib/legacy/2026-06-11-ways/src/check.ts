// `ways check` — judge one package directory against the invariant catalog.
// Pure functions over read files; the only I/O is reading. Findings are
// charges with evidence; an inline `// law-allow: <key>` downgrades a
// source-law violation to stable (held contradiction: the law and the
// annotation both witnessed).

import { readFile, readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

import {
  INVARIANTS,
  finding,
  type Finding,
  type Invariant,
  type Layer,
} from "./invariants.ts";

export type CheckReport = Readonly<{
  packageDir: string;
  layer: Layer;
  findings: readonly Finding[];
  settled: Readonly<Record<string, number>>;
}>;

type Manifest = Readonly<Record<string, unknown>>;

const LAYERS: readonly Layer[] = ["lib", "apps", "services", "sites"];

function inv(id: string): Invariant {
  const found = INVARIANTS.find((i) => i.id === id);
  if (found === undefined) throw new TypeError(`unknown invariant ${id}`);
  return found;
}

export function layerOf(packageDir: string): Layer {
  const parent = path.basename(path.dirname(path.resolve(packageDir)));
  const layer = LAYERS.find((l) => l === parent);
  if (layer === undefined) {
    throw new TypeError(
      `package directory ${packageDir} is not under lib/, apps/, services/, or sites/`,
    );
  }
  return layer;
}

async function sourceFiles(dir: string): Promise<readonly string[]> {
  const src = path.join(dir, "src");
  if (!existsSync(src)) return [];
  const entries = await readdir(src, { recursive: true, withFileTypes: true });
  return entries
    .filter((e) => e.isFile() && /\.(mts|ts|mjs|js)$/.test(e.name) && !/\.test\./.test(e.name))
    .map((e) => path.join(e.parentPath ?? src, e.name));
}

function checkManifest(dir: string, manifest: Manifest, layer: Layer): Finding[] {
  const out: Finding[] = [];
  const dirName = path.basename(path.resolve(dir));
  const name = manifest["name"];

  if (typeof name !== "string" || !/^@(561-group|emsenn)\/.+$/.test(name)) {
    out.push(finding(inv("M1"), "active", `name ${String(name)} is not @561-group/<dir> or @emsenn/<dir>`));
  } else if (name.split("/")[1] !== dirName) {
    out.push(finding(inv("M1"), "active", `name ${name} does not match directory ${dirName}`));
  } else {
    out.push(finding(inv("M1"), "potential", `name ${name} matches ${dirName}`));
  }

  const m2Faults: string[] = [];
  if (manifest["type"] !== "module") m2Faults.push('type is not "module"');
  if (manifest["private"] !== true) m2Faults.push("private is not true");
  if (manifest["sideEffects"] !== false) m2Faults.push("sideEffects is not false");
  out.push(m2Faults.length > 0
    ? finding(inv("M2"), "active", m2Faults.join("; "))
    : finding(inv("M2"), "potential", "module, private, side-effect-free"));

  const exportsMap = manifest["exports"];
  if (typeof exportsMap !== "object" || exportsMap === null) {
    out.push(finding(inv("M3"), "active", "no exports map"));
  } else {
    const keys = Object.keys(exportsMap);
    const missing = [".", "./package.json"].filter((k) => !keys.includes(k));
    out.push(missing.length > 0
      ? finding(inv("M3"), "active", `exports map missing ${missing.join(", ")}`)
      : finding(inv("M3"), "potential", `exports map declares ${keys.length} boundary points`));
  }

  const scripts = (manifest["scripts"] ?? {}) as Readonly<Record<string, unknown>>;
  const wanted = layer === "lib" ? ["check", "test", "verify"] : ["check", "test"];
  const absent = wanted.filter((s) => typeof scripts[s] !== "string");
  out.push(absent.length > 0
    ? finding(inv("M4"), "active", `missing scripts: ${absent.join(", ")}`)
    : finding(inv("M4"), "potential", `scripts present: ${wanted.join(", ")}`));

  return out;
}

function checkLayering(dir: string, manifest: Manifest, layer: Layer, repoRoot: string): Finding[] {
  const out: Finding[] = [];
  const deps = Object.entries((manifest["dependencies"] ?? {}) as Record<string, string>);
  const workspaceDeps = deps.filter(([n]) => n.startsWith("@561-group/") || n.startsWith("@emsenn/"));

  const badProtocol = workspaceDeps.filter(([, v]) => v !== "workspace:*");
  out.push(badProtocol.length > 0
    ? finding(inv("M5"), "active", `workspace deps without workspace:*: ${badProtocol.map(([n]) => n).join(", ")}`)
    : finding(inv("M5"), "potential", `${workspaceDeps.length} workspace deps, all workspace:*`));

  const allowed: Readonly<Record<Layer, readonly Layer[]>> = {
    lib: ["lib"],
    apps: ["lib"],
    services: ["lib", "apps"],
    sites: ["lib", "services"],
  };
  const inversions: string[] = [];
  for (const [depName] of workspaceDeps) {
    const short = depName.split("/")[1] ?? "";
    const home = LAYERS.find((l) => existsSync(path.join(repoRoot, l, short)));
    if (home !== undefined && !allowed[layer].includes(home)) {
      inversions.push(`${depName} lives in ${home}/`);
    }
  }
  const lId = layer === "lib" ? "L1" : layer === "apps" ? "L2" : "L3";
  out.push(inversions.length > 0
    ? finding(inv(lId), "active", `layering inversions: ${inversions.join("; ")}`)
    : finding(inv(lId), "potential", `dependency directions lawful for ${layer}/`));

  if (layer === "lib" && /-codecs(-|$)/.test(path.basename(path.resolve(dir)))) {
    out.push(deps.length > 0
      ? finding(inv("L4"), "active", `codec package declares ${deps.length} runtime deps; codecs are geometric morphisms and carry nothing`)
      : finding(inv("L4"), "potential", "codec is zero-dep"));
  }

  if (deps.length > 8) {
    out.push(finding(inv("L5"), "active", `${deps.length} direct dependencies — the god-package smell (swarm had 42)`));
  } else {
    out.push(finding(inv("L5"), "potential", `${deps.length} direct dependencies`));
  }
  return out;
}

// Source-law guards. We reuse @561-group/memetic-law when it resolves;
// hermetic fallback patterns otherwise so `ways` judges even before
// pnpm install has linked the workspace.
type LawFinding = Readonly<{ law: string; line: number; text: string; allowed: boolean }>;

const FALLBACK_LAWS: readonly Readonly<{ key: string; id: string; re: RegExp }>[] = [
  { key: "wall-clock-as-data", id: "S1", re: /\bDate\.now\(\)|new Date\(\)/ },
  { key: "delete-not-trace", id: "S2", re: /\b(unlinkSync|rmSync|rmdirSync)\b|\.\s*(unlink|rm)\(|\bdelete\s+[a-zA-Z_$][\w$.[\]]*/ },
  { key: "stringify-not-identity", id: "S3", re: /JSON\.stringify[\s\S]{0,80}?(sha256|assertionId|contentKey|append|writeFile)/ },
  { key: "ungated-admit", id: "S4", re: /\b(admitLog|federate|mergeWorlds|mergeLog)\s*\(/ },
  { key: "domain-throw", id: "S5", re: /throw new Error\(\s*["'`][^"'`]*(not.?found|denied|conflict|missing|unauthorized)/i },
];

async function scanLaws(files: readonly string[]): Promise<Map<string, LawFinding[]>> {
  const byId = new Map<string, LawFinding[]>();
  for (const file of files) {
    const text = await readFile(file, "utf8");
    const lines = text.split("\n");
    for (const law of FALLBACK_LAWS) {
      lines.forEach((lineText, i) => {
        if (!law.re.test(lineText)) return;
        const allowed = /law-allow:\s*[\w-]+/.test(lineText);
        const list = byId.get(law.id) ?? [];
        list.push({ law: law.key, line: i + 1, text: `${path.relative(process.cwd(), file)}:${i + 1}`, allowed });
        byId.set(law.id, list);
      });
    }
  }
  return byId;
}

function checkKindStrings(texts: readonly Readonly<{ file: string; text: string }>[]): Finding[] {
  const bad: string[] = [];
  let total = 0;
  for (const { file, text } of texts) {
    for (const match of text.matchAll(/kind:\s*["'`]([^"'`]+)["'`]/g)) {
      total += 1;
      const kindValue = match[1] ?? "";
      // Conformant: lowercase atoms joined by . : - ; underscore is the
      // declared escape (non-conformant but lawful); anything else is a bug.
      if (kindValue.includes("_")) continue;
      if (!/^[a-z0-9]+([.:-][a-z0-9]+)*$/.test(kindValue)) {
        bad.push(`${path.basename(file)}: "${kindValue}"`);
      }
    }
  }
  if (total === 0) return [finding(inv("A3"), "absurd", "no kind strings found")];
  return bad.length > 0
    ? [finding(inv("A3"), "active", `non-conformant kind strings: ${bad.slice(0, 6).join("; ")}${bad.length > 6 ? ` (+${bad.length - 6})` : ""}`)]
    : [finding(inv("A3"), "potential", `${total} kind strings conformant`)];
}

function checkBooleanJudgments(layer: Layer, texts: readonly Readonly<{ file: string; text: string }>[]): Finding[] {
  if (layer !== "lib") return [];
  const hits: string[] = [];
  for (const { file, text } of texts) {
    for (const match of text.matchAll(/export (?:function|const) ((?:is|has|can)[A-Z]\w*)[^\n]*?:\s*boolean/g)) {
      hits.push(`${path.basename(file)}: ${match[1]}`);
    }
  }
  return hits.length > 0
    ? [finding(inv("A1"), "active", `boolean judgments in lib exports (judgments carry witness or obstruction): ${hits.slice(0, 6).join("; ")}`)]
    : [finding(inv("A1"), "potential", "no bare boolean judgments in exports")];
}

function checkServiceTick(layer: Layer, texts: readonly Readonly<{ file: string; text: string }>[]): Finding[] {
  if (layer !== "services") return [];
  const hits: string[] = [];
  for (const { file, text } of texts) {
    const lines = text.split("\n");
    lines.forEach((lineText, i) => {
      if (/setInterval\s*\(/.test(lineText) && !/law-allow:\s*polling-fallback/.test(lineText)) {
        hits.push(`${path.basename(file)}:${i + 1}`);
      }
    });
  }
  return hits.length > 0
    ? [finding(inv("S6"), "active", `wall-clock tick without polling-fallback annotation: ${hits.join("; ")} — a tick is a witness-driven ordinal advance`)]
    : [finding(inv("S6"), "potential", "no unannotated wall-clock ticks")];
}

async function checkReadme(dir: string): Promise<Finding[]> {
  const p = path.join(dir, "README.md");
  if (!existsSync(p)) return [finding(inv("D1"), "active", "no README.md")];
  const text = await readFile(p, "utf8");
  const lines = text.split("\n").filter((l) => l.trim().length > 0).length;
  return lines >= 10
    ? [finding(inv("D1"), "potential", `README.md present (${lines} lines)`)]
    : [finding(inv("D1"), "active", `README.md is ${lines} non-empty lines; not substantive`)];
}

export async function checkPackage(packageDir: string, repoRoot?: string): Promise<CheckReport> {
  const dir = path.resolve(packageDir);
  const root = repoRoot ?? path.resolve(dir, "..", "..");
  const layer = layerOf(dir);
  const manifestPath = path.join(dir, "package.json");
  if (!existsSync(manifestPath)) {
    throw new TypeError(`no package.json at ${manifestPath}`);
  }
  const manifest = JSON.parse(await readFile(manifestPath, "utf8")) as Manifest;

  const files = await sourceFiles(dir);
  const texts = await Promise.all(
    files.map(async (file) => ({ file, text: await readFile(file, "utf8") })),
  );

  const findings: Finding[] = [
    ...checkManifest(dir, manifest, layer),
    ...checkLayering(dir, manifest, layer, root),
    ...checkKindStrings(texts),
    ...checkBooleanJudgments(layer, texts),
    ...checkServiceTick(layer, texts),
    ...(await checkReadme(dir)),
  ];

  const laws = await scanLaws(files);
  for (const lawId of ["S1", "S2", "S3", "S4", "S5"]) {
    const hits = laws.get(lawId) ?? [];
    if (hits.length === 0) {
      findings.push(finding(inv(lawId), "potential", "no occurrences"));
      continue;
    }
    const held = hits.filter((h) => h.allowed);
    const live = hits.filter((h) => !h.allowed);
    if (live.length > 0) {
      findings.push(finding(inv(lawId), "active",
        `${live.length} unannotated occurrence(s)`, live.slice(0, 8).map((h) => h.text)));
    }
    if (held.length > 0) {
      findings.push(finding(inv(lawId), "stable",
        `${held.length} occurrence(s) held under law-allow — visible, not fatal`, held.slice(0, 8).map((h) => h.text)));
    }
  }

  const settled: Record<string, number> = { potential: 0, active: 0, stable: 0, absurd: 0 };
  for (const f of findings) settled[f.charge] = (settled[f.charge] ?? 0) + 1;

  return Object.freeze({ packageDir: dir, layer, findings: Object.freeze(findings), settled: Object.freeze(settled) });
}
