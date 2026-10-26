import assert from "node:assert/strict";
import { test } from "node:test";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, readFile, rm, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { produceRegistryRuntime } from "../src/produce-registry-runtime.mjs";

const digest = bytes => createHash("sha256").update(bytes).digest("hex");

async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), "portable-registry-runtime-test-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const source = join(root, "received");
  const destination = join(root, "portable");
  await mkdir(join(source, "node_modules"), { recursive: true });
  const manifest = Buffer.from(JSON.stringify({
    name: "@fixture/consumer", version: "0.1.0",
    publishConfig: { registry: "https://registry.561.group/" },
  }) + "\n");
  const lock = Buffer.from("lockfileVersion: '9.0'\n");
  await writeFile(join(source, "package.json"), manifest);
  await writeFile(join(source, "pnpm-lock.yaml"), lock);
  const receiving = {
    kind: "npm.source-registry-closure.consumers", refusals: [],
    packages: [{
      path: join(source, "package.json"), name: "@fixture/consumer", version: "0.1.0",
      frozenInstall: true, manifestDigest: digest(manifest), lockDigest: digest(lock),
    }],
  };
  return { source, destination, receiving };
}

test("a released consumer cannot be represented by a mismatched frozen receipt", async t => {
  const { source, destination, receiving } = await fixture(t);
  const wrong = { ...receiving, packages: [{ ...receiving.packages[0], lockDigest: "incorrect" }] };
  await assert.rejects(
    produceRegistryRuntime({ consumerPath: source, receiving: wrong, destination }),
    /received consumer declarations changed/,
  );
  await assert.rejects(stat(destination), { code: "ENOENT" });
  assert.equal((await stat(join(source, "node_modules"))).isDirectory(), true);
});

test("a caller's occupied runtime destination survives a refused attempt", async t => {
  const { source, destination, receiving } = await fixture(t);
  await mkdir(destination);
  const marker = join(destination, "do-not-overwrite.txt");
  await writeFile(marker, "previous independently received runtime\n");
  await assert.rejects(
    produceRegistryRuntime({ consumerPath: source, receiving, destination }),
    { code: "EEXIST" },
  );
  assert.equal(await readFile(marker, "utf8"), "previous independently received runtime\n");
  assert.equal((await stat(join(source, "node_modules"))).isDirectory(), true);
});

test("a refusal after reserving the runtime destination removes only its own output", async t => {
  const { source, destination, receiving } = await fixture(t);
  const manifestPath = join(source, "package.json");
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  manifest.registryConsumption = { frozenLockfile: "./unadmitted-lock.yaml" };
  const bytes = Buffer.from(JSON.stringify(manifest) + "\n");
  await writeFile(manifestPath, bytes);
  receiving.packages[0].manifestDigest = digest(bytes);
  await assert.rejects(
    produceRegistryRuntime({ consumerPath: source, receiving, destination }),
    /frozen lock product must be the declared release export/,
  );
  await assert.rejects(stat(destination), { code: "ENOENT" });
  assert.equal((await stat(join(source, "node_modules"))).isDirectory(), true);
  assert.deepEqual(await readFile(manifestPath), bytes);
});

test("source and destination cannot share custody or infer success from an absent receipt", async t => {
  const { source, destination, receiving } = await fixture(t);
  await assert.rejects(
    produceRegistryRuntime({ consumerPath: source, receiving, destination: join(source, "runtime") }),
    /independent directories/,
  );
  await assert.rejects(
    produceRegistryRuntime({ consumerPath: source, receiving: { ...receiving, refusals: ["not-admitted"] }, destination }),
    /successful native frozen consumer receiving required/,
  );
  await assert.rejects(stat(destination), { code: "ENOENT" });
});

test("runtime production refuses missing static imports in an untyped JS entrance", async t => {
  const { source, destination, receiving } = await fixture(t);
  const manifestPath = join(source, "package.json");
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  manifest.files = ["main.js"];
  manifest.registryConsumption = { nodeEntrances: ["./main.js"] };
  const bytes = Buffer.from(JSON.stringify(manifest) + "\n");
  await writeFile(manifestPath, bytes);
  receiving.packages[0].manifestDigest = digest(bytes);
  await writeFile(join(source, "main.js"), "import './missing.mjs';\nthrow new Error('must not evaluate');\n");
  await assert.rejects(
    produceRegistryRuntime({ consumerPath: source, receiving, destination }),
    /declared Node composition has unresolved static imports/,
  );
  await assert.rejects(stat(destination), { code: "ENOENT" });
  assert.equal((await stat(join(source, "node_modules"))).isDirectory(), true);
  assert.deepEqual(await readFile(manifestPath), bytes);
});
