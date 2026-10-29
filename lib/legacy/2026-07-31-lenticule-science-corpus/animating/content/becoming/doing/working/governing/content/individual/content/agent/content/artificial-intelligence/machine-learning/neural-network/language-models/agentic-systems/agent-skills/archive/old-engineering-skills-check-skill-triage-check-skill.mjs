#!/usr/bin/env node
/** Check that a skill meets ASR quality standards. */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptPath = fileURLToPath(import.meta.url);
const repoRoot = ascend(path.dirname(scriptPath), 7);

const manifestRequired = new Set(["name", "description", "kind"]);
const manifestOptional = new Set([
  "version",
  "runtime",
  "triggers",
  "inputs",
  "outputs",
  "region",
  "dependencies",
  "scopes",
]);
const validKinds = new Set(["operational", "learn", "meta"]);
const semanticFields = new Set([
  "defines",
  "requires",
  "part-of",
  "extends",
  "questions",
  "addresses",
  "cites",
  "teaches",
]);
const codeExtensions = new Set([".mjs", ".js", ".ts", ".sh"]);

function ascend(startPath, levels) {
  let current = startPath;
  for (let index = 0; index < levels; index += 1) {
    current = path.dirname(current);
  }
  return current;
}

function sortedDifference(left, right) {
  return [...left].filter((value) => !right.has(value)).sort();
}

function sortedIntersection(left, right) {
  return [...left].filter((value) => right.has(value)).sort();
}

function parseFrontmatter(text) {
  const lines = text.split("\n");
  if (lines.length === 0 || lines[0].trim() !== "---") {
    return [{}, text];
  }

  let end = null;
  for (let index = 1; index < lines.length; index += 1) {
    if (lines[index].trim() === "---") {
      end = index;
      break;
    }
  }
  if (end === null) {
    return [{}, text];
  }

  const frontmatter = {};
  for (const line of lines.slice(1, end)) {
    const match = line.match(/^([a-zA-Z_-]+)\s*:/);
    if (match && !line.startsWith(" ") && !line.startsWith("\t")) {
      frontmatter[match[1]] = line.slice(match[0].length).trim();
    }
  }
  return [frontmatter, lines.slice(end + 1).join("\n")];
}

function isFile(candidatePath) {
  try {
    return fs.statSync(candidatePath).isFile();
  } catch {
    return false;
  }
}

function isDirectory(candidatePath) {
  try {
    return fs.statSync(candidatePath).isDirectory();
  } catch {
    return false;
  }
}

function walkFiles(rootPath, predicate) {
  if (!isDirectory(rootPath)) {
    return [];
  }

  const matches = [];
  const stack = [rootPath];
  while (stack.length > 0) {
    const current = stack.pop();
    const entries = fs.readdirSync(current, { withFileTypes: true })
      .sort((left, right) => left.name.localeCompare(right.name));
    for (const entry of entries) {
      const entryPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(entryPath);
      } else if (entry.isFile() && predicate(entryPath)) {
        matches.push(entryPath);
      }
    }
  }
  return matches.sort();
}

function findSkill(skillRef) {
  const directPath = path.resolve(skillRef);
  if (isFile(directPath) && path.basename(directPath) === "SKILL.md") {
    return directPath;
  }

  const contentRoot = path.join(repoRoot, "content");
  const matches = walkFiles(contentRoot, (entryPath) => {
    if (path.basename(entryPath) !== "SKILL.md") {
      return false;
    }
    const parts = entryPath.split(path.sep);
    return parts.some((part, index) => part === "skills" && parts[index + 1] === skillRef);
  });
  return matches[0] ?? null;
}

function checkSkill(skillPath) {
  const result = {
    path: path.relative(repoRoot, skillPath),
    checks: [],
    passed: 0,
    failed: 0,
    warnings: 0,
  };

  const text = fs.readFileSync(skillPath, "utf8");
  const [frontmatter, body] = parseFrontmatter(text);
  const skillDir = path.dirname(skillPath);
  const skillId = path.basename(skillDir);
  const frontmatterKeys = new Set(Object.keys(frontmatter));

  const missingRequired = sortedDifference(manifestRequired, frontmatterKeys);
  if (missingRequired.length > 0) {
    result.checks.push({
      name: "manifest-required",
      status: "FAIL",
      message: `Missing required fields: ${missingRequired.join(", ")}`,
    });
    result.failed += 1;
  } else {
    result.checks.push({ name: "manifest-required", status: "PASS", message: "All required manifest fields present" });
    result.passed += 1;
  }

  const kindValue = frontmatter.kind ?? "";
  if (kindValue && !validKinds.has(kindValue)) {
    result.checks.push({ name: "kind-enum", status: "FAIL", message: `kind '${kindValue}' not in {operational, learn, meta}` });
    result.failed += 1;
  } else if (kindValue) {
    result.checks.push({ name: "kind-enum", status: "PASS", message: `kind: ${kindValue}` });
    result.passed += 1;
  }

  const missingOptional = sortedDifference(manifestOptional, frontmatterKeys);
  if (missingOptional.length > 0) {
    result.checks.push({ name: "manifest-optional", status: "WARN", message: `Missing optional fields: ${missingOptional.join(", ")}` });
    result.warnings += 1;
  } else {
    result.checks.push({ name: "manifest-optional", status: "PASS", message: "All optional manifest fields present" });
    result.passed += 1;
  }

  const presentSemantic = sortedIntersection(semanticFields, frontmatterKeys);
  if (presentSemantic.length === 0) {
    result.checks.push({
      name: "semantic-frontmatter",
      status: "FAIL",
      message: "No semantic relation fields (defines, requires, part-of, extends, questions, addresses)",
    });
    result.failed += 1;
  } else {
    const missingSemantic = sortedDifference(semanticFields, frontmatterKeys);
    result.checks.push({
      name: "semantic-frontmatter",
      status: "PASS",
      message: `Has: ${presentSemantic.join(", ")}. Missing: ${missingSemantic.length > 0 ? missingSemantic.join(", ") : "none"}`,
    });
    result.passed += 1;
  }

  const codeFiles = [];
  for (const entry of fs.readdirSync(skillDir, { withFileTypes: true })) {
    if (entry.isFile() && codeExtensions.has(path.extname(entry.name)) && entry.name !== "SKILL.md") {
      codeFiles.push(entry.name);
    }
  }

  const scriptsDir = path.join(skillDir, "scripts");
  if (isDirectory(scriptsDir)) {
    for (const entry of fs.readdirSync(scriptsDir, { withFileTypes: true })) {
      if (entry.isFile() && codeExtensions.has(path.extname(entry.name))) {
        codeFiles.push(`scripts/${entry.name}`);
      }
    }
  }
  codeFiles.sort();

  const runtime = frontmatter.runtime ?? "inference";
  if (runtime === "script" && codeFiles.length === 0) {
    result.checks.push({ name: "colocated-code", status: "FAIL", message: "runtime: script but no code files found alongside SKILL.md" });
    result.failed += 1;
  } else if (codeFiles.length > 0) {
    result.checks.push({ name: "colocated-code", status: "PASS", message: `Code files: ${codeFiles.join(", ")}` });
    result.passed += 1;
  } else {
    result.checks.push({ name: "colocated-code", status: "WARN", message: "No colocated code. Consider whether this skill should have scripts." });
    result.warnings += 1;
  }

  const registryPath = path.join(repoRoot, ".claude", "skills", "registry.md");
  if (isFile(registryPath)) {
    const registryText = fs.readFileSync(registryPath, "utf8");
    if (registryText.includes(skillId)) {
      result.checks.push({ name: "registry-entry", status: "PASS", message: `'${skillId}' found in registry.md` });
      result.passed += 1;
    } else {
      result.checks.push({ name: "registry-entry", status: "WARN", message: `'${skillId}' not found in registry.md` });
      result.warnings += 1;
    }
  } else {
    result.checks.push({ name: "registry-entry", status: "WARN", message: "registry.md not found" });
    result.warnings += 1;
  }

  const hasCommand = /`[a-z].*\.(py|sh|ts|js|mjs)`|`python |`node |`bash /.test(body);
  const hasFileRef = /`[a-zA-Z._/]+\.(md|py|ts|js|mjs|ttl|lean|json)`/.test(body);
  const hasSkillRef = /`\/[a-z]/.test(body);
  if (hasCommand || hasFileRef || hasSkillRef) {
    const refs = [];
    if (hasCommand) refs.push("commands");
    if (hasFileRef) refs.push("file paths");
    if (hasSkillRef) refs.push("skill invocations");
    result.checks.push({ name: "body-concreteness", status: "PASS", message: `Body references: ${refs.join(", ")}` });
    result.passed += 1;
  } else {
    result.checks.push({ name: "body-concreteness", status: "WARN", message: "Body has no references to concrete files, commands, or skills" });
    result.warnings += 1;
  }

  return result;
}

function parseArgs(argv) {
  const args = { all: false, json: false, skill: null, help: false };
  for (const arg of argv) {
    if (arg === "--all") args.all = true;
    else if (arg === "--json") args.json = true;
    else if (arg === "-h" || arg === "--help") args.help = true;
    else if (arg.startsWith("-")) throw new Error(`Unknown option: ${arg}`);
    else if (args.skill === null) args.skill = arg;
    else throw new Error(`Unexpected argument: ${arg}`);
  }
  return args;
}

function printHelp() {
  console.log(`Usage:
  node check-skill.mjs <skill-id-or-path>
  node check-skill.mjs --all
  node check-skill.mjs --json <skill-id-or-path>
  node check-skill.mjs --json --all`);
}

function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(error.message);
    printHelp();
    process.exitCode = 2;
    return;
  }

  if (args.help) {
    printHelp();
    return;
  }

  if (!args.skill && !args.all) {
    printHelp();
    process.exitCode = 1;
    return;
  }

  const results = [];
  if (args.all) {
    const contentDir = path.join(repoRoot, "content");
    for (const skillFile of walkFiles(contentDir, (entryPath) => {
      if (path.basename(entryPath) !== "SKILL.md") return false;
      const parts = entryPath.split(path.sep);
      return parts.some((part, index) => part === "skills" && index < parts.length - 2);
    })) {
      results.push(checkSkill(skillFile));
    }
  } else {
    const skillPath = findSkill(args.skill);
    if (skillPath === null) {
      console.error(`Skill not found: ${args.skill}`);
      process.exitCode = 1;
      return;
    }
    results.push(checkSkill(skillPath));
  }

  if (args.json) {
    console.log(JSON.stringify({ results }, null, 2));
    return;
  }

  for (const result of results) {
    const total = result.passed + result.failed + result.warnings;
    console.log(`\n  ${result.path}  [${result.passed}/${total} pass, ${result.failed} fail, ${result.warnings} warn]`);
    for (const check of result.checks) {
      const marker = { PASS: "+", FAIL: "x", WARN: "!" }[check.status];
      console.log(`    ${marker} ${check.name}: ${check.message}`);
    }
  }

  const totalPass = results.reduce((sum, result) => sum + result.passed, 0);
  const totalFail = results.reduce((sum, result) => sum + result.failed, 0);
  const totalWarn = results.reduce((sum, result) => sum + result.warnings, 0);
  console.log(`\n  Summary: ${totalPass} pass, ${totalFail} fail, ${totalWarn} warn across ${results.length} skills`);
}

main();
