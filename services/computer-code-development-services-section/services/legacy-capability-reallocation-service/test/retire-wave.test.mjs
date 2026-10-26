import assert from "node:assert/strict";
import { posix } from "node:path";
import test from "node:test";
import { exclusions } from "../scripts/retire-wave.mjs";

test("the exclusions leave exactly the admitted owner packages of the mounted forest in the workspace", () => {
  const packages = new Set(["m", "m/a", "m/a/x", "m/a/y", "m/b", "m/b/z", "m/c"]);
  assert.deepEqual(exclusions("m", packages, []), ["!m", "!m/**"]);
  assert.deepEqual(exclusions("m", packages, ["m/a/x"]), ["!m", "!m/a", "!m/a/y", "!m/a/y/**", "!m/b", "!m/b/**", "!m/c", "!m/c/**"]);
  assert.deepEqual(exclusions("m", packages, ["m/a", "m/b/z"]), ["!m", "!m/a/x", "!m/a/x/**", "!m/a/y", "!m/a/y/**", "!m/b", "!m/c", "!m/c/**"]);
  // Read as the lockfile freshness check reads them (node's path.matchesGlob), they leave exactly the admitted packages.
  for (const admitted of [[], ["m/a/x"], ["m/a", "m/b/z"]]) {
    const patterns = exclusions("m", packages, admitted).map((line) => line.slice(1));
    const left = [...packages].filter((dir) => !patterns.some((pattern) => posix.matchesGlob(dir, pattern)));
    assert.deepEqual(left.sort(), [...admitted].sort());
  }
});

test("a wave integrates clean source into its living owner while retaining conflicts and original custody", async () => {
  const { execFileSync } = await import("node:child_process");
  const { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync, existsSync } = await import("node:fs");
  const { tmpdir } = await import("node:os");
  const { join, dirname } = await import("node:path");
  const { retireWave } = await import("../scripts/retire-wave.mjs");
  const root = mkdtempSync(join(tmpdir(), "retire-wave-"));
  const git = (cwd, ...args) => execFileSync("git", ["-C", cwd, "-c", "user.name=t", "-c", "user.email=t@t", ...args], { encoding: "utf8" });
  const put = (path, text) => { mkdirSync(dirname(join(root, path)), { recursive: true }); writeFileSync(join(root, path), text); };
  try {
    git(root, "init", "-q");
    const manifest = JSON.stringify({name: "@t/pkg", exports: {".": "./src/index.mjs"}});
    put("copy/pkg/package.json", manifest);
    put("copy/pkg/src/index.mjs", "export const useful = true;\n");
    put("copy/pkg/src/clash.mjs", "copy disagreement\n");
    put("copy/pkg/lib/legacy/old.mjs", "older source\n");
    const workspace = 'packages:\n  - "copy/**"\n';
    put("pnpm-workspace.yaml", workspace);
    git(root, "add", "."); git(root, "commit", "-q", "-m", "copy source");
    put("mount/svc/pkg/package.json", manifest);
    put("mount/svc/pkg/src/clash.mjs", "owner disagreement\n");
    const owner = join(root, "mount");
    git(owner, "init", "-q"); git(owner, "add", "."); git(owner, "commit", "-q", "-m", "living owner");
    const census = {packages: {"@t/pkg": {owner: {path: "svc/pkg"}, copies: [{path: "copy/pkg"}]}}, waves: [{wave: 1, names: ["@t/pkg"]}]};
    const options = {census, wave: 1, repository: root, mount: "mount"};
    const preview = retireWave(options);
    assert.equal(preview.kind, "owner-retirement-wave/v2");
    assert.equal(preview.applied, false);
    assert.equal(preview.packages[0].counts["copy-added"], 1);
    assert.equal(preview.packages[0].counts.conflict, 1);
    assert(!existsSync(join(owner, "svc/pkg/src/index.mjs")));
    const result = retireWave({...options, write: true});
    assert.equal(result.applied, true);
    assert.equal(result.moves, 0);
    assert.equal(readFileSync(join(owner, "svc/pkg/src/index.mjs"), "utf8"), "export const useful = true;\n");
    assert.equal(readFileSync(join(owner, "svc/pkg/src/clash.mjs"), "utf8"), "owner disagreement\n");
    assert(existsSync(join(root, "copy/pkg/src/index.mjs")), "original custody awaits separate retirement");
    assert(existsSync(join(root, "copy/pkg/lib/legacy/old.mjs")));
    assert.equal(readFileSync(join(root, "pnpm-workspace.yaml"), "utf8"), workspace);
    assert(!existsSync(join(root, "lib/emsenn/services/561-group/lib/legacy/retired-for-owner")));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
