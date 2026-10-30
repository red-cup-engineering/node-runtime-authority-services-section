#!/usr/bin/env node
// ways — the ways, enforced and midwifed.
//
//   ways list                      print the invariant catalog
//   ways check <pkg-dir> [...]     judge package(s); findings are charges
//   ways check --all               judge every workspace package
//   ways scaffold <layer> <name>   generate a conformant package skeleton
//
// Exit code: number of packages with unheld active findings (0 = lawful).

import { readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import process from "node:process";

import { INVARIANTS, type Finding } from "./invariants.ts";
import { checkPackage, type CheckReport } from "./check.ts";
import { scaffold } from "./scaffold.ts";

const MARKS: Readonly<Record<string, string>> = {
  potential: "+", active: "!", stable: "#", absurd: "·",
};

function findRepoRoot(start: string): string {
  let dir = path.resolve(start);
  while (true) {
    if (existsSync(path.join(dir, "pnpm-workspace.yaml"))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) throw new TypeError("no pnpm-workspace.yaml above " + start);
    dir = parent;
  }
}

function renderReport(report: CheckReport): string {
  const lines: string[] = [];
  const counts = report.settled;
  lines.push(`${report.packageDir} [${report.layer}]  ` +
    `+${counts["potential"] ?? 0} !${counts["active"] ?? 0} #${counts["stable"] ?? 0} ·${counts["absurd"] ?? 0}`);
  const interesting = report.findings.filter((f) => f.charge !== "potential");
  for (const f of interesting) {
    lines.push(`  ${MARKS[f.charge] ?? "?"} ${f.invariant} ${f.charge}: ${f.message}`);
    for (const e of f.evidence) lines.push(`      ${e}`);
  }
  if (interesting.length === 0) lines.push("  + fully lawful");
  return lines.join("\n");
}

function hasUnheldViolation(report: CheckReport): boolean {
  return report.findings.some((f: Finding) => f.charge === "active" && f.severity === "error");
}

async function workspacePackages(root: string): Promise<string[]> {
  const out: string[] = [];
  for (const layer of ["lib", "apps", "services", "sites"]) {
    const layerDir = path.join(root, layer);
    if (!existsSync(layerDir)) continue;
    for (const entry of await readdir(layerDir, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      if (existsSync(path.join(layerDir, entry.name, "package.json"))) {
        out.push(path.join(layerDir, entry.name));
      }
    }
  }
  return out;
}

async function main(): Promise<void> {
  const [, , command, ...args] = process.argv;

  if (command === "list" || command === undefined) {
    for (const i of INVARIANTS) {
      console.log(`${i.id}  [${i.severity}]  (${i.layers.join(",")})  ${i.claim}  — way: ${i.way}`);
    }
    console.log("\ncharges: + potential (conforms)  ! active (violation)  # stable (held under law-allow)  · absurd (no evidence)");
    return;
  }

  if (command === "check") {
    const root = findRepoRoot(process.cwd());
    const targets = args.includes("--all")
      ? await workspacePackages(root)
      : args.filter((a) => !a.startsWith("--"));
    if (targets.length === 0) {
      console.error("ways check <pkg-dir> [...] | ways check --all");
      process.exitCode = 2;
      return;
    }
    let unlawful = 0;
    for (const target of targets) {
      try {
        const report = await checkPackage(target, root);
        console.log(renderReport(report) + "\n");
        if (hasUnheldViolation(report)) unlawful += 1;
      } catch (error) {
        console.error(`${target}: ${error instanceof Error ? error.message : String(error)}\n`);
        unlawful += 1;
      }
    }
    console.log(`${targets.length} package(s) judged; ${unlawful} with unheld violations`);
    process.exitCode = Math.min(unlawful, 125);
    return;
  }

  if (command === "scaffold") {
    const [layer, name] = args;
    if (layer !== "lib" && layer !== "apps" && layer !== "services" && layer !== "sites") {
      console.error("ways scaffold <lib|apps|services|sites> <name>");
      process.exitCode = 2;
      return;
    }
    if (name === undefined) {
      console.error("ways scaffold <layer> <name>");
      process.exitCode = 2;
      return;
    }
    const suffixAdvice: Readonly<Record<string, RegExp>> = {
      lib: /-(topology|codecs(-[a-z0-9-]+)?)$/,
      apps: /-computer$/,
      services: /-(tics|wire|room)$/,
    };
    const advice = suffixAdvice[layer];
    if (advice !== undefined && !advice.test(name)) {
      console.error(`note (M6): domain ${layer} packages usually parse as ` +
        (layer === "lib" ? "<thing>-topology or <thing>-codecs[-<standard>]"
          : layer === "apps" ? "<thing>-computer"
            : "<thing>-tics (or -wire/-room)") +
        `; "${name}" diverges — fine for utilities, deliberate for organisms.`);
    }
    const root = findRepoRoot(process.cwd());
    const result = await scaffold(root, layer, name);
    console.log(`scaffolded ${result.packageDir}`);
    for (const f of result.written) console.log(`  ${path.relative(root, f)}`);
    console.log(`\nnext: pnpm install   then: ways check ${path.relative(process.cwd(), result.packageDir)}`);
    return;
  }

  console.error(`unknown command: ${command}\nways list | ways check <dir>|--all | ways scaffold <layer> <name>`);
  process.exitCode = 2;
}

await main();
