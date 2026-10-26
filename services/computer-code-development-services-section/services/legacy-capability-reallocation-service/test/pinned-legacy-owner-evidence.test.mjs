import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, readdir, rm, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { receivePinnedLegacyOwnerEvidence } from '../src/pinned-legacy-owner-evidence.mjs';

const repository = 'https://github.com/example/owner.git', commit = 'a'.repeat(40);
const source = { id: 'owner', repository, commit, paths: ['package.json', 'src/owner.mjs'] };
const request = parent => ({ kind: 'legacy-pinned-owner-evidence-request/v1', scratchParent: parent, sources: [source] });
const file = (path, bytes = Buffer.from('export const owner = 1;\n'), pin = commit) => ({ path, mode: '100644', bytes,
  source: { repository, commit: pin, path, object: createHash(pin.length === 40 ? 'sha1' : 'sha256').update('blob ' + bytes.length + '\0').update(bytes).digest('hex') } });
async function fixture(t) {
  const parent = await mkdtemp(join(tmpdir(), 'legacy-owner-evidence-test-'));
  t.after(() => rm(parent, { recursive: true, force: true }));
  return parent;
}

test('receives exact original source and refuses to confer retirement or runtime authority', async t => {
  const parent = await fixture(t), events = [];
  const result = await receivePinnedLegacyOwnerEvidence(request(parent), { environment: { PRIVATE_TOKEN: 'not-for-evidence' }, createReader: options => {
    events.push(options);
    return async selection => {
      assert.equal(selection.repository, repository); assert.equal(selection.commit, commit);
      assert.equal(selection.scope, ''); assert.equal(selection.enterDirectory('services/other'), false);
      assert.equal(selection.selectFile('src/owner.mjs'), true); assert.equal(selection.selectFile('src/other.mjs'), false);
      return [file('src/owner.mjs'), file('package.json', Buffer.from('\ufeff{}\n'))];
    };
  } });
  assert.equal(events[0].rejectSelectedNonRegular, true);
  assert.equal(events[0].maxRepositories, 1);
  assert.equal(result.retirementAuthorized, false); assert.equal(result.reviewRequired, true);
  assert.deepEqual(result.owners[0].files.map(f => f.path), ['package.json', 'src/owner.mjs']);
  assert.equal(result.owners[0].files[0].text, '\ufeff{}\n');
  assert.equal(JSON.stringify(result).includes('not-for-evidence'), false);
  assert.deepEqual(await readdir(parent), []);
});

test('validates all finite selections before creating a reader or scratch', async t => {
  const parent = await fixture(t);
  const bad = [
    { sources: [{ ...source, commit: 'main' }] },
    { sources: [{ ...source, repository: 'https://secret:token@github.com/example/owner.git' }] },
    { sources: [{ ...source, repository: repository + '?token=secret' }] },
    { sources: [{ ...source, paths: ['../escape'] }] },
    { sources: [{ ...source, paths: ['a', 'a'] }] },
    { sources: [{ ...source, paths: ['services/link/file.mjs'], grant: 'ambient' }] },
    { sources: [source, source] }, { maximumFileBytes: 1048577 }, { maximumTotalBytes: 16777217 },
    { maximumTreePaths: Infinity }, { sources: [] }, { token: 'must-not-be-a-record' }
  ];
  for (const value of bad) await assert.rejects(receivePinnedLegacyOwnerEvidence({ ...request(parent), ...value }, {
    createReader: () => assert.fail('invalid request reached source reader')
  }));
  assert.deepEqual(await readdir(parent), []);
});

test('requires every named regular source at the exact owner pin and Git blob identity', async t => {
  const parent = await fixture(t);
  const a = file('package.json'), b = file('src/owner.mjs');
  for (const files of [[a], [a, a], [a, file('other.mjs')], [a, { ...b, mode: '120000' }],
    [a, { ...b, source: { ...b.source, commit: 'b'.repeat(40) } }],
    [a, { ...b, source: { ...b.source, object: '0'.repeat(40) } }],
    [a, { ...b, source: { ...b.source, repository: 'https://github.com/example/other.git' } }]]) {
    await assert.rejects(receivePinnedLegacyOwnerEvidence(request(parent), { createReader: () => async () => files }));
    assert.deepEqual(await readdir(parent), []);
  }
});

test('enforces byte limits across independent owners and rejects lossy text', async t => {
  const parent = await fixture(t);
  await assert.rejects(receivePinnedLegacyOwnerEvidence({ ...request(parent), maximumFileBytes: 2 }, {
    createReader: () => async () => [file('package.json'), file('src/owner.mjs')]
  }), /byte bound/);
  await assert.rejects(receivePinnedLegacyOwnerEvidence({ ...request(parent), maximumTotalBytes: 6,
    sources: [{ ...source, paths: ['a'] }, { ...source, id: 'second', paths: ['b'] }] }, {
    createReader: () => async selection => [file(selection.selectFile('a') ? 'a' : 'b', Buffer.from('four'))]
  }), /byte bound/);
  await assert.rejects(receivePinnedLegacyOwnerEvidence(request(parent), {
    createReader: () => async () => [file('package.json'), file('src/owner.mjs', Buffer.from([0xff]))]
  }), /encoded data/);
  assert.deepEqual(await readdir(parent), []);
});

test('cleans only its own scratch after failed original source receiving', async t => {
  const parent = await fixture(t);
  const sibling = await mkdtemp(join(parent, 'another-owner-'));
  await assert.rejects(receivePinnedLegacyOwnerEvidence(request(parent), { createReader: () => async () => { throw Error('source unavailable'); } }), /source unavailable/);
  assert.deepEqual(await readdir(parent), [sibling.slice(parent.length + 1)]);
  const linked = join(parent, 'linked'); await symlink(sibling, linked);
  await assert.rejects(receivePinnedLegacyOwnerEvidence(request(linked), { createReader: () => assert.fail('redirected scratch reached reader') }), /unredirected/);
});

test('retains exact SHA-256 Git provenance without reducing it to SHA-1', async t => {
  const parent = await fixture(t), pin = 'b'.repeat(64);
  const result = await receivePinnedLegacyOwnerEvidence({ ...request(parent), sources: [{ ...source, commit: pin, paths: ['owner.mjs'] }] }, {
    createReader: () => async () => [file('owner.mjs', Buffer.from('export default 1;'), pin)]
  });
  assert.equal(result.owners[0].files[0].source.object.length, 64);
});

test('ordinary CLI refuses an occupied evidence destination before source acquisition', async t => {
  const parent = await fixture(t), input = join(parent, 'request.json'), output = join(parent, 'evidence.json');
  await writeFile(input, JSON.stringify({ kind: 'invalid-and-never-acquired' }));
  await writeFile(output, 'retained original evidence\n');
  assert.throws(() => execFileSync(process.execPath, [fileURLToPath(new URL('../scripts/receive-pinned-legacy-owners.mjs', import.meta.url)), input, output], {
    encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 5000
  }), error => /owner evidence output already exists/u.test(error.stderr));
  assert.equal(await readFile(output, 'utf8'), 'retained original evidence\n');
});
