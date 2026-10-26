import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtemp, mkdir, writeFile, readFile, rm, chmod, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { gzipSync, gunzipSync } from 'node:zlib';
import { create, Header } from 'tar';
import { readRegistryArchiveMembers, receiveSourceArchiveMembers } from '../src/artifact-member-receiving.mjs';
import { planLandedPackageRelease } from '../src/release-wave.mjs';
import { preparePublicationCarrierManifest } from '../src/publication-carrier-manifest.mjs';
const limits = { members: 1000, bytes: 8 * 1024 * 1024, archiveBytes: 1024 * 1024, tarBytes: 16 * 1024 * 1024, metadataBytes: 65536, sourcePaths: 10000, sourceRepositories: 16 };
const sri = bytes => 'sha512-' + createHash('sha512').update(bytes).digest('base64');
async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'artifact-native-test-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const source = join(root, 'source'); await mkdir(source);
  const scratch = join(root, 'caller-owned-scratch'); await mkdir(scratch, { mode: 0o700 });
  const manifest = { name: 'native-artifact-test', version: '0.1.0', files: ['src', 'package'], bin: { native: 'src/cli.mjs' } };
  const text = JSON.stringify(manifest) + '\n';
  await writeFile(join(source, 'package.json'), text); await mkdir(join(source, 'src')); await mkdir(join(source, 'package'));
  await writeFile(join(source, 'src/cli.mjs'), '#!/usr/bin/env node\n'); await chmod(join(source, 'src/cli.mjs'), 0o755);
  await writeFile(join(source, 'src/ignored.mjs'), 'ignored\n'); await writeFile(join(source, 'src/.npmignore'), 'ignored.mjs\n');
  await writeFile(join(source, 'package/real.txt'), 'nested package directory\n');
  async function pack(paths, options = {}) {
    const path = join(root, `archive-${Math.random()}.tgz`);
    await create({ cwd: source, file: path, prefix: 'package', gzip: true, portable: true, ...options }, paths);
    return { path, integrity: sri(await readFile(path)), limits };
  }
  return { root, source, scratch, manifest, text, pack };
}
test('original landed allocation retains unoccupied, history and occupied dev sequence laws', () => {
  assert.deepEqual(planLandedPackageRelease({ declared: '0.4.0', published: [], history: 2 }), { version: '0.4.0', tag: 'latest', kind: 'release' });
  assert.deepEqual(planLandedPackageRelease({ declared: '0.4.0', published: ['0.4.0', '0.4.1-dev.7'], history: 4 }), { version: '0.4.1-dev.8', tag: 'dev', kind: 'dev' });
  assert.equal(planLandedPackageRelease({ declared: '0.4.1-dev.2', published: ['0.4.1-dev.2'], history: 99 }).version, '0.4.1-dev.99');
  assert.throws(() => planLandedPackageRelease({ declared: '0.4.1-rc.1', published: [], history: 1 }));
  assert.throws(() => planLandedPackageRelease({ declared: '0.4.0', published: ['latest'], history: 1 }));
});
test('prepared carrier separates native source coordinates from finite repository fallback', () => {
  const input = { repository: 'file:///original/mirror', commit: 'a'.repeat(40), manifestText: '{"name":"native","version":"0.1.0","scripts":{"test":"kept"}}\n', published: ['0.1.0'], history: 5, repositoryFallback: { type: 'git', url: 'https://example.invalid/owner/native.git' } };
  const plan = preparePublicationCarrierManifest(input), value = JSON.parse(plan.preparedManifestText);
  assert.equal(plan.source.repository, input.repository); assert.equal(value.version, '0.1.1-dev.5'); assert.equal(value.scripts.test, 'kept');
  assert.deepEqual(value.repository, input.repositoryFallback); assert.equal(Object.hasOwn(value, 'gitHead'), false);
  const original = { name: 'native', version: '0.1.0', repository: 'https://elsewhere.invalid/native' };
  assert.equal(JSON.parse(preparePublicationCarrierManifest({ ...input, manifestText: JSON.stringify(original) }).preparedManifestText).repository, original.repository);
  assert.throws(() => preparePublicationCarrierManifest({ ...input, repositoryFallback: { url: 'x', unexpected: true } }));
});
test('maintained native archive reader preserves a literal nested package directory and executable intent', async t => {
  const f = await fixture(t), archive = await f.pack(['package.json', 'src/cli.mjs', 'package/real.txt']);
  const result = await readRegistryArchiveMembers(archive);
  assert.deepEqual(result.archive.members.map(e => e.path).sort(), ['package.json', 'package/real.txt', 'src/cli.mjs']);
  assert.equal(result.archive.members.find(e => e.path === 'src/cli.mjs').mode & 0o111, 0o111);
  assert.equal(result.observation.extracted, false); assert.equal(result.observation.installationClaimed, false);
});
test('native archive reader refuses duplicate paths, links and bounded expansion before extraction', async t => {
  const f = await fixture(t);
  await assert.rejects(readRegistryArchiveMembers(await f.pack(['package.json', 'package.json'])), /duplicate/);
  await symlink('cli.mjs', join(f.source, 'src/link'));
  await assert.rejects(readRegistryArchiveMembers(await f.pack(['package.json', 'src/link'])), /regular|unsupported/);
  const archive = await f.pack(['package.json', 'src/cli.mjs']);
  await assert.rejects(readRegistryArchiveMembers({ ...archive, limits: { ...limits, tarBytes: 512 } }));
  await assert.rejects(readRegistryArchiveMembers({ ...archive, integrity: sri(Buffer.from('another')) }), /SHA512/);
});
test('native archive reader refuses parser metadata, truncated bodies, nonzero tails and ambiguous decoded names', async t => {
  const f = await fixture(t);
  const long = 'a'.repeat(150); await writeFile(join(f.source, long), 'long\n');
  await assert.rejects(readRegistryArchiveMembers(await f.pack(['package.json', long])), /extension|uninterpreted/);
  const replacement = 'x\ufffd'; await writeFile(join(f.source, replacement), 'ambiguous\n');
  await assert.rejects(readRegistryArchiveMembers(await f.pack(['package.json', replacement])), /encoding|extension/);
  const archive = await f.pack(['package.json', 'src/cli.mjs']), raw = gunzipSync(await readFile(archive.path));
  const bad = gzipSync(Buffer.concat([raw, Buffer.from('tail') , Buffer.alloc(508)]));
  const path = join(f.root, 'tail.tgz'); await writeFile(path, bad);
  await assert.rejects(readRegistryArchiveMembers({ ...archive, path, integrity: sri(bad) }), /after.*end|uninterpreted/);
  const truncated = gzipSync(raw.subarray(0, 1024)); await writeFile(path, truncated);
  await assert.rejects(readRegistryArchiveMembers({ ...archive, path, integrity: sri(truncated) }));
});
test('unobserved zero-length metadata cannot hide in public parser event coverage', async t => {
  const f = await fixture(t), archive = await f.pack(['package.json', 'src/cli.mjs']);
  const header = new Header({ path: 'package/zero-meta', type: 'ExtendedHeader', size: 0, mode: 0o644 });
  header.encode();
  const bytes = gzipSync(Buffer.concat([header.block, gunzipSync(await readFile(archive.path))]));
  const path = join(f.root, 'zero-meta.tgz'); await writeFile(path, bytes);
  await assert.rejects(readRegistryArchiveMembers({ ...archive, path, integrity: sri(bytes) }), /account|extension|uninterpreted/);
});
// These tests exercise the original reader port with explicit supplied Git facts;
// released CLI receiving additionally qualifies the actual selected Git provider.
async function suppliedReader(f) {
  const paths = ['package.json', 'src/cli.mjs', 'src/ignored.mjs', 'src/.npmignore', 'package/real.txt'];
  const entries = await Promise.all(paths.map(async path => ({ path, mode: path === 'src/cli.mjs' ? '100755' : '100644', bytes: await readFile(join(f.source, path)), source: { repository: 'fixture', commit: 'a'.repeat(40), object: 'b'.repeat(40), path: 'scope/' + path } })));
  return async ({ selectFile }) => entries.filter(entry => selectFile(entry.path));
}
test('native npm narrows the original source allowance using real ignore precedence, before archive names', async t => {
  const f = await fixture(t), readSource = await suppliedReader(f), archive = await f.pack(['package.json', 'src/cli.mjs', 'package/real.txt']);
  const result = await receiveSourceArchiveMembers({ registry: 'https://registry.example.invalid/', source: { repository: 'fixture', commit: 'a'.repeat(40), scope: 'scope' }, archive: { path: archive.path, integrity: archive.integrity }, limits }, { readSource, sourceDirectory: f.source, scratchDirectory: f.scratch });
  assert.equal(result.ok, true); assert.ok(!result.source.requiredPaths.includes('src/ignored.mjs'));
  assert.equal(result.source.members[0].path, 'package.json'); assert.equal(result.source.members[0].gitSource.path, 'scope/package.json');
  assert.equal(result.installationClaimed, false);
  const missing = await f.pack(['package.json', 'src/cli.mjs']);
  const refusal = await receiveSourceArchiveMembers({ registry: 'https://registry.example.invalid/', source: { repository: 'fixture', commit: 'a'.repeat(40) }, archive: { path: missing.path, integrity: missing.integrity }, limits }, { readSource, sourceDirectory: f.source, scratchDirectory: f.scratch });
  assert.equal(refusal.ok, false); assert.ok(refusal.comparison.refusal.findings.some(f => f.code === 'absent-from-archive' && f.path === 'package/real.txt'));
});
test('native source receiving refuses unknown source-directory inputs and JSON claimed build evidence', async t => {
  const f = await fixture(t), readSource = await suppliedReader(f), archive = await f.pack(['package.json']);
  const input = { registry: 'https://registry.example.invalid/', source: { repository: 'fixture', commit: 'a'.repeat(40) }, archive: { path: archive.path, integrity: archive.integrity }, limits };
  await assert.rejects(receiveSourceArchiveMembers(input, { readSource, sourceDirectory: f.source, scratchDirectory: f.scratch, buildQualification: { outcome: 'source-build-qualified' } }), /in-process/);
  await writeFile(join(f.source, 'unexpected.txt'), 'unreceived\n');
  await assert.rejects(receiveSourceArchiveMembers(input, { readSource, sourceDirectory: f.source, scratchDirectory: f.scratch }), /differs.*producer/);
});

test('native dynamic preparation is recomputed from original Git manifest and occupied/history inputs', async t => {
  const f = await fixture(t), readSource = await suppliedReader(f);
  const commit = 'a'.repeat(40), preparation = { published: ['0.1.0'], history: 7, repositoryFallback: { type: 'git', url: 'https://example.invalid/native.git' } };
  const producer = preparePublicationCarrierManifest({ repository: 'fixture', commit, manifestText: f.text, ...preparation });
  const stamped = JSON.stringify({ ...JSON.parse(producer.preparedManifestText), gitHead: commit }, null, 2) + '\n';
  await writeFile(join(f.source, 'package.json'), stamped);
  const archive = await f.pack(['package.json', 'src/cli.mjs', 'package/real.txt']);
  const input = { registry: 'https://registry.example.invalid/', source: { repository: 'fixture', commit }, archive: { path: archive.path, integrity: archive.integrity }, publisher: { gitHead: commit, format: 'json-2-newline' }, limits };
  const received = await receiveSourceArchiveMembers(input, { readSource, sourceDirectory: f.source, scratchDirectory: f.scratch, preparation });
  assert.equal(received.ok, true); assert.equal(received.source.preparation.selection.version, '0.1.1-dev.7');
  await assert.rejects(receiveSourceArchiveMembers(input, { readSource, sourceDirectory: f.source, scratchDirectory: f.scratch, preparation: { ...preparation, history: 8 } }), /differs.*producer/);
});

test('ordinary native receive CLI uses the selected strict Git provider and exclusive output', async t => {
  const { execFile } = await import('node:child_process'), { promisify } = await import('node:util');
  const execute = promisify(execFile), f = await fixture(t);
  const git = args => execute('git', ['-c', 'core.hooksPath=/dev/null', ...args], { cwd: f.source });
  await git(['init', '--quiet']); await git(['add', '.']);
  await git(['-c', 'user.name=Native Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet', '-m', 'native receiving fixture']);
  const commit = (await git(['rev-parse', 'HEAD'])).stdout.trim(), archive = await f.pack(['package.json', 'src/cli.mjs', 'package/real.txt']);
  const input = join(f.root, 'selection.json'), output = join(f.root, 'received.json');
  await writeFile(input, JSON.stringify({ registry: 'https://registry.example.invalid/', source: { repository: f.source, commit },
    sourceDirectory: f.source, scratchDirectory: f.scratch, archive: { path: archive.path, integrity: archive.integrity }, limits }));
  const cli = new URL('../scripts/receive-packed-registry-artifact.mjs', import.meta.url);
  const { stdout } = await execute(process.execPath, [cli.pathname, 'receive', input, output], { timeout: 60000 });
  assert.equal(JSON.parse(stdout).ok, true); const held = await readFile(output);
  await assert.rejects(execute(process.execPath, [cli.pathname, 'receive', input, output], { timeout: 60000 }), error => error.stderr.includes('EEXIST'));
  assert.deepEqual(await readFile(output), held);
  await symlink('cli.mjs', join(f.source, 'src/unexported-link')); await git(['add', '.']);
  await git(['-c', 'user.name=Native Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet', '-m', 'unsupported selected kind']);
  const later = (await git(['rev-parse', 'HEAD'])).stdout.trim();
  const request = JSON.parse(await readFile(input)); request.source.commit = later; await writeFile(input, JSON.stringify(request));
  await assert.rejects(execute(process.execPath, [cli.pathname, 'receive', input], { timeout: 60000 }), error => error.stderr.includes('not a supported regular file'));
});


test('one invalid artifact preflight stays attached to its selected consumer and launches no installer', async t => {
  const { receiveSourceRegistryConsumers } = await import('../src/source-registry-closure.mjs');
  const f = await fixture(t), archive = await f.pack(['package.json']);
  const manifest = { name: 'native-consumer-fixture', version: '0.0.0', private: true, dependencies: { 'native-artifact-test': '0.1.0' } };
  await writeFile(join(f.source, 'package.json'), JSON.stringify(manifest));
  await writeFile(join(f.source, 'pnpm-lock.yaml'), "lockfileVersion: '9.0'\n");
  const released = { name: 'native-artifact-test', version: '0.1.0', integrity: archive.integrity, artifactDownloaded: true };
  const result = await receiveSourceRegistryConsumers({ consumerPaths: [f.source], releases: [released],
    artifactReceiving: [{ consumer: manifest.name, name: released.name, version: released.version,
      archive: { path: archive.path, integrity: archive.integrity }, limits: { ...limits, archiveBytes: 1 }, registry: 'https://registry.example.invalid/' }],
    artifactReceiptDirectory: f.root, logDirectory: join(f.root, 'logs'), pnpm: '/must-not-launch-a-native-installer' });
  assert.equal(result.packages.length, 0); assert.equal(result.refusals.length, 1);
  assert.equal(result.refusals[0].name, manifest.name);
});
