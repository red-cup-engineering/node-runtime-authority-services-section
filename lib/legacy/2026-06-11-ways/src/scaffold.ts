// `ways scaffold` — packages born conformant. Generates the per-layer
// skeleton from package-invariants.md. Refuses to overwrite anything that
// exists (time only accumulates; scaffolding is append-only).

import { mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

import type { Layer } from "./invariants.ts";

export type ScaffoldResult = Readonly<{
  packageDir: string;
  written: readonly string[];
}>;

function manifestFor(layer: Layer, name: string): string {
  const base: Record<string, unknown> = {
    name: `@561-group/${name}`,
    version: "0.0.1",
    private: true,
    type: "module",
    description: "TODO: one sentence — what site (domain-as-topology) this package presents.",
    engines: { node: ">=22.18" },
    scripts: layer === "lib"
      ? { check: "tsc --noEmit", test: 'node --test "src/**/*.test.mts"', verify: "npm run check && npm run test" }
      : { check: "tsc --noEmit", test: 'node --test "src/**/*.test.ts"' },
    exports: { ".": layer === "lib" ? "./src/index.mts" : "./src/index.ts", "./package.json": "./package.json" },
    devDependencies: { "@types/node": "^22.0.0", typescript: "^5.8.0" },
    sideEffects: false,
  };
  if (layer === "apps") base["bin"] = { [name]: "./src/cli.ts" };
  if (layer === "services" || layer === "sites") {
    base["561:serve"] = { serviceName: name, kind: "proxy", port: 0, sse: false, ws: false };
  }
  return JSON.stringify(base, null, 2) + "\n";
}

const TSCONFIG = `{
  "compilerOptions": {
    "module": "nodenext",
    "moduleResolution": "nodenext",
    "target": "es2023",
    "lib": ["es2023"],
    "types": ["node"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "noEmit": true
  },
  "include": ["src"]
}
`;

function indexFor(layer: Layer, name: string): string {
  const kind = name.replace(/[^a-z0-9-]/g, "");
  return `// @561-group/${name}
//
// A domain presented as witnessed predication: vocabulary enters as marks,
// facts enter as witnesses, computation is induce() plus readings.
// Judgments return witness-or-obstruction carriers, never booleans, never
// domain-outcome throws. Evidence is monotone. Kind strings are morphism
// paths (Three Dots and a Dash: "." generated-from, ":" witnesses,
// "-" obstructs). See dev/docs/explanations/package-invariants.md.

export type ${pascal(name)}Carrier = Readonly<{
  kind: "${kind}";
}>;

export function ${camel(name)}(): ${pascal(name)}Carrier {
  return Object.freeze({ kind: "${kind}" });
}
${layer === "lib" ? "" : "\n// Apps render; services settle; sites operate. Domain logic lives in lib/.\n"}`;
}

function testFor(name: string): string {
  return `// Theorem-shaped tests: each test name is a claim about the carrier.
import test from "node:test";
import assert from "node:assert/strict";

import { ${camel(name)} } from "./index.mts";

test("${name} carrier is frozen and kind-conformant", () => {
  const carrier = ${camel(name)}();
  assert.equal(Object.isFrozen(carrier), true);
  assert.match(carrier.kind, /^[a-z0-9]+([.:-][a-z0-9]+)*$/);
});
`;
}

function readmeFor(layer: Layer, name: string): string {
  return `# @561-group/${name}

TODO (D1): what this package IS, in one paragraph — the domain it presents
as a topology, and the consumer contract in five sentences or fewer.

## Quick start

\`\`\`ts
import { ${camel(name)} } from "@561-group/${name}";
\`\`\`

## Objects and morphisms

- \`${pascal(name)}Carrier\` — TODO.
- \`${camel(name)}()\` — TODO.

## Layer

${layer}/ — ${layer === "lib" ? "vocabulary and computation" : layer === "apps" ? "a runnable tool over lib topologies" : layer === "services" ? "a persistent settling process" : "an operated instance with public identity"}.
`;
}

function camel(name: string): string {
  return name.replace(/-(\w)/g, (_, c: string) => c.toUpperCase());
}

function pascal(name: string): string {
  const c = camel(name);
  return c.charAt(0).toUpperCase() + c.slice(1);
}

export async function scaffold(repoRoot: string, layer: Layer, name: string): Promise<ScaffoldResult> {
  if (!/^[a-z][a-z0-9-]*$/.test(name)) {
    throw new TypeError(`package name must be lower-kebab-case, got ${name}`);
  }
  const dir = path.join(repoRoot, layer, name);
  if (existsSync(dir)) {
    throw new TypeError(`${dir} already exists; scaffolding is append-only`);
  }
  const ext = layer === "lib" ? "mts" : "ts";
  const files: ReadonlyArray<readonly [string, string]> = [
    ["package.json", manifestFor(layer, name)],
    ["tsconfig.json", TSCONFIG],
    [`src/index.${ext}`, indexFor(layer, name)],
    [`src/index.test.${ext === "mts" ? "mts" : "ts"}`, testFor(name)],
    ["README.md", readmeFor(layer, name)],
  ];
  const written: string[] = [];
  await mkdir(path.join(dir, "src"), { recursive: true });
  for (const [rel, content] of files) {
    const target = path.join(dir, rel);
    await writeFile(target, content, { flag: "wx" });
    written.push(target);
  }
  return Object.freeze({ packageDir: dir, written: Object.freeze(written) });
}
