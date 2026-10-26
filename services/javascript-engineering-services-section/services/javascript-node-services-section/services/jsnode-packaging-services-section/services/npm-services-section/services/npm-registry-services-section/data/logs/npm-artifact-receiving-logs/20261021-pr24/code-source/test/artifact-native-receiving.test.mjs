import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtemp, mkdir, writeFile, readFile, rm, chmod, symlink, cp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { gzipSync, gunzipSync } from 'node:zlib';
import { create, Header } from 'tar';
import { readRegistryArchiveMembers, receiveSourceArchiveMembers, receiveInstalledArtifactMembers } from '../src/artifact-member-receiving.mjs';
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
test('carrier preparation accepts literal SHA256 source coordinates and refuses truncated or coercible identities', () => {
  const commit = 'c'.repeat(64), input = { repository: 'file:///original/mirror', commit,
    manifestText: '{"name":"native","version":"0.1.0"}\n', published: [], history: 1 };
  const result = preparePublicationCarrierManifest(input);
  assert.equal(result.source.commit, commit); assert.equal(result.publisher.gitHead, commit);
  assert.equal(result.selection.version, '0.1.0');
  for (const wrong of [commit.slice(0, 63), commit + 'c', [commit]]) {
    assert.throws(() => preparePublicationCarrierManifest({ ...input, commit: wrong }), /exact bounded original/u);
    if (Array.isArray(wrong)) assert.equal(Object.isFrozen(wrong), false);
  }
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

test('ordinary native receive CLI receives an actual SHA256 Git commit through the selected primitive', async t => {
  const { execFile } = await import('node:child_process'), { promisify } = await import('node:util');
  const execute = promisify(execFile), f = await fixture(t);
  const git = args => execute('git', ['-c', 'core.hooksPath=/dev/null', ...args], { cwd: f.source });
  await git(['init', '--quiet', '--object-format=sha256']); await git(['add', '.']);
  await git(['-c', 'user.name=Native Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet', '-m', 'native SHA256 receiving fixture']);
  assert.equal((await git(['rev-parse', '--show-object-format=storage'])).stdout.trim(), 'sha256');
  const commit = (await git(['rev-parse', 'HEAD'])).stdout.trim(); assert.match(commit, /^[a-f0-9]{64}$/u);
  const archive = await f.pack(['package.json', 'src/cli.mjs', 'package/real.txt']);
  const input = join(f.root, 'sha256-selection.json'), output = join(f.root, 'sha256-received.json');
  await writeFile(input, JSON.stringify({ registry: 'https://registry.example.invalid/', source: { repository: f.source, commit },
    sourceDirectory: f.source, scratchDirectory: f.scratch, archive: { path: archive.path, integrity: archive.integrity }, limits }));
  const cli = new URL('../scripts/receive-packed-registry-artifact.mjs', import.meta.url);
  const { stdout } = await execute(process.execPath, [cli.pathname, 'receive', input, output], {
    timeout: 60000, maxBuffer: 1024 * 1024, env: { ...process.env, GIT_DEFAULT_HASH: 'sha1' },
  });
  const result = JSON.parse(stdout); assert.equal(result.ok, true);
  assert.equal(result.source.commit, commit); assert.equal(result.installationClaimed, false);
  assert.equal(result.source.requiredPaths.length, 3);
  for (const entry of result.source.members) {
    assert.equal(entry.gitSource.commit, commit); assert.match(entry.gitSource.object, /^[a-f0-9]{64}$/u);
  }
  assert.deepEqual(JSON.parse(await readFile(output, 'utf8')), result);
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

test('ordinary receive CLI follows only selected declared exact child repositories', async t => {
  const { execFile } = await import('node:child_process'), { promisify } = await import('node:util');
  const execute = promisify(execFile), f = await fixture(t), child = join(f.root, 'child-owner');
  await mkdir(child); await writeFile(join(child, 'child.mjs'), 'export const child = true;\n');
  const git = (cwd, args) => execute('git', ['-c', 'core.hooksPath=/dev/null', ...args], { cwd });
  const commit = async cwd => {
    await git(cwd, ['-c', 'user.name=Native Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet', '-m', 'exact native child']);
    return (await git(cwd, ['rev-parse', 'HEAD'])).stdout.trim();
  };
  await git(child, ['init', '--quiet']); await git(child, ['add', '.']); const childCommit = await commit(child);
  f.manifest.files.push('services/selected/child.mjs');
  await writeFile(join(f.source, 'package.json'), JSON.stringify(f.manifest) + '\n');
  const declarations = selected => `[submodule "selected"]\n path = services/selected\n url = ${selected}\n[submodule "unselected"]\n path = unrelated\n url = ${join(f.root, 'must-not-acquire')}\n`;
  await writeFile(join(f.source, '.gitmodules'), declarations(child));
  await git(f.source, ['init', '--quiet']); await git(f.source, ['add', '.']);
  await git(f.source, ['update-index', '--add', '--cacheinfo', `160000,${childCommit},services/selected`]);
  await git(f.source, ['update-index', '--add', '--cacheinfo', `160000,${'f'.repeat(40)},unrelated`]);
  const sourceCommit = await commit(f.source);
  // The actual staged carrier contains selected inputs, while Git retains its
  // declaration metadata and the unrelated link in the exact original source.
  const stage = join(f.root, 'staged-source'); await mkdir(stage);
  for (const path of ['package.json', 'src', 'package']) await cp(join(f.source, path), join(stage, path), { recursive: true });
  for (const root of [f.source, stage]) {
    await mkdir(join(root, 'services/selected'), { recursive: true });
    await cp(join(child, 'child.mjs'), join(root, 'services/selected/child.mjs'));
  }
  const archive = await f.pack(['package.json', 'src/cli.mjs', 'package/real.txt', 'services/selected/child.mjs']);
  const input = join(f.root, 'child-selection.json'), cli = new URL('../scripts/receive-packed-registry-artifact.mjs', import.meta.url);
  const request = { registry: 'https://registry.example.invalid/', source: { repository: f.source, commit: sourceCommit },
    sourceDirectory: stage, scratchDirectory: f.scratch, archive: { path: archive.path, integrity: archive.integrity }, limits };
  await writeFile(input, JSON.stringify(request));
  const { stdout } = await execute(process.execPath, [cli.pathname, 'receive', input], { timeout: 60000 });
  const received = JSON.parse(stdout); assert.equal(received.ok, true);
  const witness = received.source.members.find(entry => entry.path === 'services/selected/child.mjs');
  assert.equal(witness.gitSource.repository, child); assert.equal(witness.gitSource.commit, childCommit);
  assert.equal(witness.gitSource.path, 'child.mjs');
  await writeFile(join(f.source, '.gitmodules'), declarations('../unqualified-relative-child'));
  await git(f.source, ['add', '.gitmodules']); request.source.commit = await commit(f.source);
  await writeFile(input, JSON.stringify(request));
  await assert.rejects(execute(process.execPath, [cli.pathname, 'receive', input], { timeout: 60000 }), error => error.stderr.includes('child repository locator is outside'));
});

test('installed receiving refuses an outside bin directory before reading archive or registrations', async t => {
  const f = await fixture(t), installationRoot = join(f.root, 'installation'), outside = join(f.root, 'outside-bins');
  await mkdir(installationRoot); await mkdir(outside); await mkdir(join(installationRoot, 'package'));
  await symlink(outside, join(installationRoot, '.bin'));
  // Supplied in-process fixture facts exercise this negative boundary only;
  // they make no claim that a historical native installation occurred.
  const nativeInstallation = async () => ({ installation: { kind: 'native-package-installation', status: 0,
    manager: { name: 'pnpm', version: '11.28.5' } }, provider: { shimTargetFormat: 'pnpm11-cmd-shim-target' } });
  await assert.rejects(receiveInstalledArtifactMembers({ registry: 'https://registry.example.invalid/',
    archive: { path: join(f.root, 'must-not-open.tgz'), integrity: sri(Buffer.alloc(0)) }, limits,
    installationRoot, packageRoot: join(installationRoot, 'package'), binDirectory: join(installationRoot, '.bin'),
    name: 'native-artifact-test', version: '0.1.0' }, { nativeInstallation }), /bin directory leaves/);
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
