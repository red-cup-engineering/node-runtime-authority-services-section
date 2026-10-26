import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { createReceivedOwnerSourceReader } from '../src/received-owner-source.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const text = '\ufeffexport function projectPackage() { return 2; }\n';
const bytes = Buffer.from(text), path = 'src/source.mjs';
const file = { path, text, bytes: bytes.length, sha256: sha(bytes) };
const source = { repository: 'https://example.invalid/owner.git', commit: 'a'.repeat(40), path,
  object: createHash('sha1').update('blob ' + bytes.length + '\0').update(bytes).digest('hex') };
function pinned() {
  return { kind: 'legacy-pinned-owner-evidence/v1', reviewRequired: true, retirementAuthorized: false,
    owners: [{ id: 'owner', repository: source.repository, commit: source.commit, files: [{ ...file, mode: '100644', source: { ...source } }] }] };
}
function published() {
  const integrity = 'sha512-' + Buffer.alloc(64, 1).toString('base64');
  return { kind: 'legacy-current-published-owner-source/v1', reviewRequired: true, retirementAuthorized: false,
    owner: { name: 'owner', version: '1.0.0', registry: 'https://registry.example.invalid',
      tarball: 'https://registry.example.invalid/owner/-/owner-1.0.0.tgz', integrity },
    archive: { integrity, archiveSHA256: 'b'.repeat(64), extracted: false, installationClaimed: false },
    sourceFiles: [{ ...file, mode: 0o644 }], members: [{ path, kind: 'file', bytes: bytes.length, sha256: sha(bytes), mode: 0o644 }] };
}
const read = (record, selection = { owner: 'owner', path }, limit = 1024) =>
  createReceivedOwnerSourceReader(Buffer.from(JSON.stringify(record)))(selection, limit);

test('pinned Git source preserves BOM bytes and exact Git provenance', () => {
  const result = read(pinned());
  assert.deepEqual(result.bytes, bytes);
  assert.equal(result.identity.object, source.object);
  assert.equal(result.identity.commit, source.commit);
  assert.equal(result.identity.path, path);
});

test('published source retains archive identity and admitted member mode', () => {
  const result = read(published());
  assert.deepEqual(result.bytes, bytes);
  assert.equal(result.identity.integrity, published().owner.integrity);
  assert.equal(result.identity.archiveSHA256, 'b'.repeat(64));
  assert.equal(result.identity.mode, 0o644);
});

test('SHA-256 Git repositories use their original blob identity', () => {
  const record = pinned(), owner = record.owners[0];
  owner.commit = 'c'.repeat(64);
  owner.files[0].source = { ...source, commit: owner.commit,
    object: createHash('sha256').update('blob ' + bytes.length + '\0').update(bytes).digest('hex') };
  assert.equal(read(record).identity.object, owner.files[0].source.object);
});

test('missing, ambiguous, unsafe and oversized member selections refuse', () => {
  for (const selection of [{ owner: 'other', path }, { owner: 'owner', path: 'missing' },
    { owner: 'owner', path: '../source.mjs' }, { owner: 'owner', path, evaluate: true }]) assert.throws(() => read(pinned(), selection));
  const record = pinned(); record.owners[0].files.push({ ...record.owners[0].files[0] });
  assert.throws(() => read(record));
  assert.throws(() => read(pinned(), undefined, bytes.length - 1));
});

test('altered text, byte counts, hashes, provenance and Git objects refuse', () => {
  for (const mutate of [f => f.text += 'changed', f => f.bytes++, f => f.sha256 = '0'.repeat(64),
    f => f.mode = '120000', f => f.source.path = 'other', f => f.source.commit = 'c'.repeat(40),
    f => f.source.object = '0'.repeat(40)]) {
    const record = pinned(); mutate(record.owners[0].files[0]); assert.throws(() => read(record));
  }
  const record = pinned(); record.owners[0].commit = 'HEAD'; assert.throws(() => read(record));
});

test('archive identity substitution, duplicate members and executable claims refuse', () => {
  for (const mutate of [r => r.archive.integrity = 'different', r => r.archive.archiveSHA256 = 'unknown',
    r => r.archive.extracted = true, r => r.archive.installationClaimed = true,
    r => r.retirementAuthorized = true, r => r.reviewRequired = false,
    r => r.members[0].sha256 = '0'.repeat(64), r => r.members[0].mode = 0o755,
    r => r.members[0].kind = 'symlink', r => r.members.push({ ...r.members[0] }),
    r => r.owner.tarball = 'https://other.example.invalid/owner.tgz']) {
    const record = published(); mutate(record); assert.throws(() => read(record));
  }
});

test('credential-bearing locators and lossy UTF-8 are never accepted', () => {
  const record = pinned(); record.owners[0].repository = 'https://token@example.invalid/owner.git'; assert.throws(() => read(record));
  const other = published(); other.owner.tarball += '?token=secret'; assert.throws(() => read(other));
  assert.throws(() => createReceivedOwnerSourceReader(Buffer.from([0xff])));
  const lossy = pinned(), selected = lossy.owners[0].files[0];
  selected.text = '\ud800'; selected.bytes = 3; selected.sha256 = sha(Buffer.from(selected.text));
  assert.throws(() => read(lossy));
});
