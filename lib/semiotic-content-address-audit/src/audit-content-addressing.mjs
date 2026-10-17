import { promises as fs } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

export const AUDIT_VERSION = 1;

const SKIP_DIRS = new Set([
  ".git", "node_modules", "vendor", "dist", "build", "coverage", ".cache",
  ".next", ".venv", "venv", "target", "__pycache__",
]);

const TEXT_EXTENSIONS = new Set([
  ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html",
  ".java", ".js", ".json", ".jsx", ".lean", ".md", ".mjs", ".mts",
  ".php", ".py", ".rb", ".rs", ".sh", ".sol", ".sql", ".swift",
  ".toml", ".ts", ".tsx", ".txt", ".yaml", ".yml",
]);

const DETECTORS = Object.freeze([
  {
    kind: "canonical-ni",
    class: "canonical",
    pattern: /ni:\/\/\/sha-256;[A-Za-z0-9_-]{43}/gu,
  },
  {
    kind: "sha256-hex-output",
    class: "candidate",
    pattern: /(?:createHash\s*\(\s*["']sha256["']\s*\)|sha256)[^\n]{0,160}?digest\s*\(\s*["']hex["']\s*\)/giu,
  },
  {
    kind: "sha256-hex-literal",
    class: "candidate",
    pattern: /\b[0-9a-f]{64}\b/giu,
  },
  {
    kind: "legacy-sha256-address-alias",
    class: "candidate",
    pattern: /(?:\b(?:urn|blob):sha-?256:|\bsha256:|\bmetroplat:artifact:[^\s"'`]+sha-256:)/giu,
  },
  {
    kind: "cid-ipfs",
    class: "candidate",
    pattern: /(?:\bCID\.(?:parse|create)|\bmultihash\b|\bmultiformats\b|\bipfs:\/\/|\/ipfs\/)/giu,
  },
  {
    kind: "content-identity-field",
    class: "candidate",
    pattern: /\b(?:contentId|contentID|contentAddress|content_address|artifactId|artifactID|witnessRoot|digest|checksum)\b/gu,
  },
  {
    kind: "git-oid-identity",
    class: "candidate",
    pattern: /\b(?:gitOid|gitOID|commitSha|commitSHA|commit_hash|commitHash)\b/gu,
  },
  {
    kind: "uuid-content-identity",
    class: "candidate",
    pattern: /\b(?:content|artifact|receipt)[_-]?(?:id|identity)[^\n]{0,80}?\b(?:uuid|randomUUID)\b/giu,
  },
]);

function isLikelyTextFile(file) {
  const base = path.basename(file);
  if (["Dockerfile", "Makefile", "Procfile", "Justfile"].includes(base)) return true;
  return TEXT_EXTENSIONS.has(path.extname(file).toLowerCase());
}

export function auditText(text, file = "<memory>") {
  const evidence = [];
  const lines = String(text).split(/\r?\n/u);
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    for (const detector of DETECTORS) {
      detector.pattern.lastIndex = 0;
      if (!detector.pattern.test(line)) continue;
      evidence.push(Object.freeze({
        file,
        line: index + 1,
        kind: detector.kind,
        class: detector.class,
        snippet: line.trim().slice(0, 240),
      }));
    }
  }
  return Object.freeze(evidence);
}

async function walk(root, current = root, out = []) {
  const entries = await fs.readdir(current, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory() && SKIP_DIRS.has(entry.name)) continue;
    const absolute = path.join(current, entry.name);
    if (entry.isDirectory()) {
      await walk(root, absolute, out);
    } else if (entry.isFile() && isLikelyTextFile(absolute)) {
      out.push(absolute);
    }
  }
  return out;
}

async function readMode(root) {
  const configPath = path.join(root, ".content-addressing.json");
  try {
    const parsed = JSON.parse(await fs.readFile(configPath, "utf8"));
    const allowed = new Set(["canonical", "adapter-only", "exempt-external-protocol"]);
    return allowed.has(parsed.mode) ? parsed.mode : null;
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
}

export function classifyEvidence(evidence, declaredMode = null) {
  const canonical = evidence.filter((item) => item.class === "canonical").length;
  const candidates = evidence.filter((item) => item.class === "candidate").length;
  if (declaredMode === "adapter-only" || declaredMode === "exempt-external-protocol") return declaredMode;
  if (candidates > 0 && canonical > 0) return "mixed";
  if (candidates > 0) return "legacy-only";
  if (canonical > 0) return "canonical";
  return "unknown";
}

export async function auditRepository(rootInput = ".") {
  const root = path.resolve(rootInput);
  const files = await walk(root);
  const evidence = [];
  for (const absolute of files) {
    let text;
    try {
      text = await fs.readFile(absolute, "utf8");
    } catch {
      continue;
    }
    evidence.push(...auditText(text, path.relative(root, absolute) || path.basename(absolute)));
  }
  const declaredMode = await readMode(root);
  const state = classifyEvidence(evidence, declaredMode);
  const counts = evidence.reduce((acc, item) => {
    acc[item.kind] = (acc[item.kind] ?? 0) + 1;
    return acc;
  }, {});
  return Object.freeze({
    kind: "semiotic-content-address.audit",
    version: AUDIT_VERSION,
    root,
    declaredMode,
    state,
    counts: Object.freeze(counts),
    evidence: Object.freeze(evidence),
  });
}

async function main(argv) {
  const roots = argv.length > 0 ? argv : ["."];
  const reports = [];
  for (const root of roots) reports.push(await auditRepository(root));
  process.stdout.write(`${JSON.stringify(reports.length === 1 ? reports[0] : reports, null, 2)}\n`);
  if (reports.some((report) => report.state === "mixed" || report.state === "legacy-only")) {
    process.exitCode = 1;
  }
}

const invoked = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (invoked) await main(process.argv.slice(2));
