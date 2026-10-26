import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { observeTrackedLegacyOwnerCandidates as observe } from "../src/legacy-capability-reallocation.mjs";

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), "legacy-owner-candidates-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const git = (...args) => execFileSync("git", ["-C", root, ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
  git("init"); git("config", "user.name", "Test"); git("config", "user.email", "test@example.invalid");
  mkdirSync(join(root, "lib/legacy"), { recursive: true }); mkdirSync(join(root, "living"));
  writeFileSync(join(root, "lib/legacy/é\nsource.mts"), "export function projectPackage() { return 1; }\n");
  writeFileSync(join(root, "lib/legacy/unknown.mjs"), "export const unrelated = 1;\n");
  writeFileSync(join(root, "lib/legacy/unselected.mjs"), "x".repeat(4096));
  writeFileSync(join(root, "living/module.mjs"), "export function projectPackage() { return 2; }\n");
  symlinkSync("../living/module.mjs", join(root, "lib/legacy/link"));
  git("add", "."); git("commit", "-m", "original");
  return { root, git, request: { repositoryRoot: root, legacyRoot: "lib/legacy", revision: git("rev-parse", "HEAD"), sourcePaths: ["é\nsource.mts", "unknown.mjs"], owners: [{ repositoryRoot: root, path: "living/module.mjs" }], maximumFileBytes: 256 } };
}

test("selected immutable bytes and one owner table give hints without semantic or retirement authority", t => {
  const { root, git, request } = fixture(t);
  writeFileSync(join(root, "lib/legacy/é\nsource.mts"), "export const edited = true;\n");
  const before = git("status", "--porcelain", "--untracked-files=no");
  const result = observe(request);
  assert.equal(result.retirementAuthorized, false);
  assert.equal(result.owners.length, 1);
  assert.deepEqual(result.records[0].candidates, [{ owner: 0, sharedSymbols: ["projectPackage"] }]);
  assert.deepEqual(result.records[1].candidates, []);
  assert.equal(result.records[0].source.path, "é\nsource.mts");
  assert.equal(result.records[0].reviewRequired, true);
  assert.match(result.records[0].source.sha256, /^[a-f0-9]{64}$/u);
  assert.deepEqual(result.records[0].exports, ["projectPackage"]);
  assert.equal(git("status", "--porcelain", "--untracked-files=no"), before);
  assert.equal(readFileSync(join(root, "living/module.mjs"), "utf8"), "export function projectPackage() { return 2; }\n");
});

test("already retired sources remain readable from their exact Git blobs", t => {
  const { root, request } = fixture(t);
  rmSync(join(root, "lib/legacy/é\nsource.mts"));
  assert.equal(observe(request).records[0].candidates[0].owner, 0);
});

test("shared private helpers do not manufacture a living capability candidate", t => {
  const { root, git, request } = fixture(t);
  writeFileSync(join(root, "lib/legacy/unknown.mjs"), "function requireSpecification() {}\nexport const original = 1;\n");
  writeFileSync(join(root, "living/module.mjs"), "function requireSpecification() {}\nexport const other = 2;\n");
  git("add", "."); git("commit", "-m", "different public capabilities");
  const result = observe({ ...request, revision: git("rev-parse", "HEAD"), sourcePaths: ["unknown.mjs"] });
  assert.deepEqual(result.records[0].candidates, []);
  assert.deepEqual(result.records[0].directExports, ["original"]);
});

test("unknown, repeated, symbolic-link sources and mutable revisions refuse", t => {
  const { request } = fixture(t);
  for (const sourcePaths of [["missing"], ["unknown.mjs", "unknown.mjs"], ["link"]]) assert.throws(() => observe({ ...request, sourcePaths }));
  assert.throws(() => observe({ ...request, revision: "HEAD" }), /immutable/u);
  assert.throws(() => observe({ ...request, sourcePaths: [] }), /selected/u);
});

test("linked, nonregular, duplicate, legacy and foreign owner paths refuse", t => {
  const { root, request } = fixture(t);
  symlinkSync("module.mjs", join(root, "living/link.mjs"));
  for (const path of ["living/link.mjs", "living", "lib/legacy/unknown.mjs", "../elsewhere"]) assert.throws(() => observe({ ...request, owners: [{ repositoryRoot: root, path }] }));
  assert.throws(() => observe({ ...request, owners: [...request.owners, ...request.owners] }), /duplicated/u);
  assert.throws(() => observe({ ...request, owners: [{ repositoryRoot: join(root, "living"), path: "module.mjs" }] }), /actual Git root/u);
});

test("individual and combined byte limits refuse while unselected large blobs remain unread", t => {
  const { request } = fixture(t);
  assert.equal(observe(request).records.length, 2);
  assert.throws(() => observe({ ...request, maximumFileBytes: 8 }), /byte limits/u);
  assert.throws(() => observe({ ...request, maximumTotalBytes: 60 }), /byte limits/u);
  assert.throws(() => observe({ ...request, sourcePaths: ["unselected.mjs"] }), /byte limits/u);
  assert.throws(() => observe({ ...request, maximumTotalBytes: Infinity }), /bounded/u);
});

test("the ordinary CLI writes a new discovery record and refuses to replace it", t => {
  const { root, request } = fixture(t), input = join(root, "request.json"), output = join(root, "observed.json");
  writeFileSync(input, JSON.stringify(request));
  const cli = fileURLToPath(new URL("../scripts/observe-tracked-legacy-owners.mjs", import.meta.url));
  const run = () => spawnSync(process.execPath, [cli, input, output], { encoding: "utf8" });
  const first = run(); assert.equal(first.status, 0, first.stderr);
  const retained = readFileSync(output);
  assert.equal(JSON.parse(retained).retirementAuthorized, false);
  assert.notEqual(run().status, 0);
  assert.deepEqual(readFileSync(output), retained);
});

test('one received owner record supplies several members without native source copies or repeated byte charges', t => {
  const { root, git, request } = fixture(t);
  const commit = 'a'.repeat(40), repository = 'https://example.invalid/source.git';
  const files = ['projectPackage', 'unrelated'].map(name => {
    const path = 'src/' + name + '.mjs', text = 'export function ' + name + '() { return 2; }\n', bytes = Buffer.from(text);
    return { path, text, bytes: bytes.length, mode: '100644', sha256: createHash('sha256').update(bytes).digest('hex'),
      source: { repository, commit, path, object: createHash('sha1').update('blob ' + bytes.length + '\0').update(bytes).digest('hex') } };
  });
  const receipt = Buffer.from(JSON.stringify({ kind: 'legacy-pinned-owner-evidence/v1', reviewRequired: true,
    retirementAuthorized: false, owners: [{ id: 'received', repository, commit, files }] }));
  writeFileSync(join(root, 'living/source.json'), receipt);
  rmSync(join(root, 'living/module.mjs'));
  const before = git('status', '--porcelain', '--untracked-files=no');
  const owners = files.map(file => ({ repositoryRoot: root, path: 'living/source.json', receivedSource: { owner: 'received', path: file.path } }));
  const result = observe({ ...request, owners });
  assert.deepEqual(result.records.map(row => row.candidates.map(c => c.owner)), [[0], [1]]);
  assert.equal(result.bytesRead, receipt.length + Buffer.byteLength('export function projectPackage() { return 1; }\n') + Buffer.byteLength('export const unrelated = 1;\n'));
  assert.equal(result.owners[0].receipt.sha256, createHash('sha256').update(receipt).digest('hex'));
  assert.equal(result.owners[1].receipt.source.commit, commit);
  assert.equal(result.owners[1].source.path, files[1].path);
  assert.equal(result.retirementAuthorized, false);
  assert.equal(git('status', '--porcelain', '--untracked-files=no'), before);
  assert.throws(() => observe({ ...request, owners, maximumTotalBytes: receipt.length - 1 }), /byte limits/u);
  assert.throws(() => observe({ ...request, owners: [owners[0], { ...owners[0], receivedSource: { path: files[0].path, owner: 'received' } }] }), /duplicated/u);
  symlinkSync('source.json', join(root, 'living/linked.json'));
  assert.throws(() => observe({ ...request, owners: [{ ...owners[0], path: 'living/linked.json' }] }));
});
