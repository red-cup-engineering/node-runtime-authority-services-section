import { createHash } from 'node:crypto';

const fail = () => { throw new TypeError('received owner source identity or bytes differ'); };
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const literal = path => typeof path === 'string' && path.length > 0 && path.length <= 4096
  && !path.startsWith('/') && !/[\\\0\r\n]/u.test(path)
  && path.split('/').every(part => part && !['.', '..', '.git'].includes(part));
function https(value) {
  let url;
  try { url = new URL(value); } catch { fail(); }
  const exact = url.href === value || url.pathname === '/' && url.href === value + '/';
  if (typeof value !== 'string' || !exact || url.protocol !== 'https:'
    || url.username || url.password || url.search || url.hash || /[\s\\]/u.test(value)) fail();
  return url;
}

/** Select already received source bytes. A receipt is evidence for review, never acquisition or coverage authority. */
export function createReceivedOwnerSourceReader(recordBytes) {
  const record = JSON.parse(new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(recordBytes));
  if (record?.reviewRequired !== true || record.retirementAuthorized !== false) fail();
  return (selection, maximumFileBytes) => {
  if (!selection || Object.keys(selection).some(key => !['owner', 'path'].includes(key))
    || typeof selection.owner !== 'string' || !selection.owner || selection.owner.length > 256
    || !literal(selection.path) || !Number.isSafeInteger(maximumFileBytes) || maximumFileBytes < 1 || maximumFileBytes > 1048576) fail();
  let files, identity, git;
  if (record.kind === 'legacy-pinned-owner-evidence/v1') {
    if (!Array.isArray(record.owners) || record.owners.length > 32) fail();
    const matches = record.owners.filter(owner => owner?.id === selection.owner);
    if (matches.length !== 1) fail();
    const owner = matches[0];
    https(owner.repository);
    if (!/^[0-9a-f]{40}(?:[0-9a-f]{24})?$/u.test(owner.commit)) fail();
    files = owner.files;
    if (!Array.isArray(files) || files.length > 64) fail();
    identity = { kind: record.kind, owner: owner.id, repository: owner.repository, commit: owner.commit };
    git = owner;
  } else if (record.kind === 'legacy-current-published-owner-source/v1') {
    const owner = record.owner;
    if (!owner || owner.name !== selection.owner || typeof owner.version !== 'string' || !owner.version) fail();
    const registry = https(owner.registry), tarball = https(owner.tarball);
    if (registry.origin !== tarball.origin || !/^sha512-[A-Za-z0-9+/]{86}==$/u.test(owner.integrity)
      || Buffer.from(owner.integrity.slice(7), 'base64').toString('base64') !== owner.integrity.slice(7)
      || record.archive?.integrity !== owner.integrity || !/^[a-f0-9]{64}$/u.test(record.archive?.archiveSHA256)
      || record.archive.extracted !== false || record.archive.installationClaimed !== false) fail();
    files = record.sourceFiles;
    if (!Array.isArray(files) || files.length > 200 || !Array.isArray(record.members) || record.members.length > 100000) fail();
    identity = { kind: record.kind, owner: owner.name, version: owner.version, registry: owner.registry,
      tarball: owner.tarball, integrity: owner.integrity, archiveSHA256: record.archive.archiveSHA256 };
  } else fail();
  const matches = files.filter(file => file?.path === selection.path);
  if (matches.length !== 1) fail();
  const file = matches[0];
  if (typeof file.text !== 'string' || !Number.isSafeInteger(file.bytes) || file.bytes < 0
    || file.bytes > maximumFileBytes || !/^[a-f0-9]{64}$/u.test(file.sha256)) fail();
  const bytes = Buffer.from(file.text, 'utf8');
  if (bytes.length !== file.bytes || digest(bytes) !== file.sha256) fail();
  // UTF-8 replacement of an unpaired surrogate must not silently change the selected text.
  if (new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes) !== file.text) fail();
  if (git) {
    if (!['100644', '100755'].includes(file.mode) || file.source?.repository !== git.repository
      || file.source?.commit !== git.commit || file.source?.path !== selection.path) fail();
    const object = createHash(git.commit.length === 40 ? 'sha1' : 'sha256')
      .update('blob ' + bytes.length + '\0').update(bytes).digest('hex');
    if (file.source.object !== object) fail();
    identity.object = object;
  } else {
    const members = record.members.filter(member => member?.path === selection.path);
    if (members.length !== 1 || members[0].kind !== 'file' || members[0].bytes !== bytes.length
      || members[0].sha256 !== file.sha256 || members[0].mode !== file.mode
      || !Number.isInteger(file.mode) || file.mode < 0 || file.mode > 0o7777) fail();
  }
  return { bytes, identity: { ...identity, path: selection.path, mode: file.mode, sha256: file.sha256 } };
  };
}
