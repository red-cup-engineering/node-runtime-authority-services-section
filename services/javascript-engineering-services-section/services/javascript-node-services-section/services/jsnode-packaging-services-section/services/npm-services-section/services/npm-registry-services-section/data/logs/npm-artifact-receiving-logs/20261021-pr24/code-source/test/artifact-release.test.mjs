import assert from "node:assert/strict";
import { test } from "node:test";
import { admitArtifactRelease, compareArtifactInventories } from "../src/artifact-release.mjs";

const manifest = Object.freeze({ name: "@red-cup-engineering/example", version: "0.1.0", exports: { ".": "./dist/index.mjs" } });
const input = Object.freeze({
  registry: "https://registry.561.group",
  manifest,
  tarballManifest: manifest,
  tarballInventory: ["package.json", "dist/index.mjs"],
  installedManifest: manifest,
  installedInventory: ["dist/index.mjs", "package.json"],
  imports: [{ specifier: "@red-cup-engineering/example", status: "imported", exports: ["answer"] }],
});

test("explicit inventory comparison preserves its original replayable manifest/path/import observations", () => {
  const first = compareArtifactInventories(input);
  const second = compareArtifactInventories(input);
  assert.equal(first.ok, true);
  assert.deepEqual(first, second);
  assert.match(first.value.identity, /^ni:\/\//u);
  assert.deepEqual(first.value.tarball.inventory, ["dist/index.mjs", "package.json"]);
});

test("explicit inventory comparison preserves its original mismatched inventory refusal", () => {
  const result = compareArtifactInventories({ ...input, installedInventory: ["package.json"] });
  assert.deepEqual(result, {
    ok: false,
    refusal: {
      code: "artifact-release-mismatch",
      releaseIdentity: result.refusal.releaseIdentity,
      manifestMismatch: false,
      inventory: { absentFromTarball: [], absentFromInstalledPackage: ["dist/index.mjs"] },
    },
  });
});

test("legacy inventory evidence cannot become a successful full release admission", () => {
  const result = admitArtifactRelease(input);
  assert.equal(result.ok, false);
  assert.equal(result.refusal.code, "artifact-release-evidence-incomplete");
  assert.equal(result.refusal.stage, "release");
  assert.equal(compareArtifactInventories(input).value.version, 1);
});
