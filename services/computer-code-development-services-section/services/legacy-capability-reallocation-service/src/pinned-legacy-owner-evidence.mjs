import { createHash } from 'node:crypto';
import { mkdtemp, realpath, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { isAbsolute, join, resolve } from 'node:path';
import { createPinnedSourceReader } from '@red-cup-engineering/git-source-reading-service/pinned-source-files';

const keys = (value, allowed) => {
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).some(key => !allowed.includes(key)))
    throw new TypeError('owner evidence contains unsupported fields');
};
const bound = (value, maximum, name) => {
  if (!Number.isSafeInteger(value) || value < 1 || value > maximum) throw new TypeError('finite ' + name + ' bound required');
  return value;
};
const contained = value => typeof value === 'string' && value.length > 0 && value.length <= 4096
  && !value.includes('\\') && !/[\0\r\n]/u.test(value) && !value.startsWith('/')
  && value.split('/').every(part => part && !['.', '..', '.git'].includes(part));
function sourceRequest(value) {
  keys(value, ['id', 'repository', 'commit', 'paths']);
  if (typeof value.id !== 'string' || !/^[a-z0-9][a-z0-9._-]{0,79}$/u.test(value.id)) throw new TypeError('a bounded owner id is required');
  let url;
  try { url = new URL(value.repository); } catch { throw new TypeError('owner repository must be an HTTPS identity'); }
  if (typeof value.repository !== 'string' || url.protocol !== 'https:' || url.username || url.password || url.search || url.hash
    || url.href !== value.repository || /[\s\\]/u.test(value.repository)) throw new TypeError('owner repository must be a credential-free HTTPS identity');
  if (typeof value.commit !== 'string' || !/^[0-9a-f]{40}(?:[0-9a-f]{24})?$/u.test(value.commit)) throw new TypeError('an exact owner commit is required');
  if (!Array.isArray(value.paths) || value.paths.length < 1 || value.paths.length > 64 || value.paths.some(path => !contained(path))
    || new Set(value.paths).size !== value.paths.length) throw new TypeError('one to 64 distinct contained owner paths are required');
  return { id: value.id, repository: value.repository, commit: value.commit, paths: [...value.paths] };
}

/** Receive exact owner source, without checkout, import evaluation, gitlink traversal or retirement authority. */
export async function receivePinnedLegacyOwnerEvidence(request, { createReader = createPinnedSourceReader, environment = {} } = {}) {
  keys(request, ['kind', 'sources', 'scratchParent', 'maximumFileBytes', 'maximumTotalBytes', 'maximumTreePaths']);
  if (request.kind !== 'legacy-pinned-owner-evidence-request/v1') throw new TypeError('an owner evidence request is required');
  if (!Array.isArray(request.sources) || request.sources.length < 1 || request.sources.length > 32) throw new TypeError('one to 32 explicit owner sources are required');
  const sources = request.sources.map(sourceRequest);
  if (new Set(sources.map(source => source.id)).size !== sources.length || sources.reduce((n, source) => n + source.paths.length, 0) > 512)
    throw new TypeError('owner ids must be distinct and total selected paths bounded by 512');
  const maximumFileBytes = bound(request.maximumFileBytes ?? 262144, 1048576, 'file byte');
  const maximumTotalBytes = bound(request.maximumTotalBytes ?? 8388608, 16777216, 'total byte');
  const maximumTreePaths = bound(request.maximumTreePaths ?? 5000, 100000, 'tree path');
  const parent = request.scratchParent ?? tmpdir();
  if (typeof parent !== 'string' || !isAbsolute(parent) || resolve(parent) !== parent || await realpath(parent) !== parent || !(await stat(parent)).isDirectory())
    throw new TypeError('owner source scratch parent must be an existing unredirected directory');
  const scratch = await mkdtemp(join(parent, 'legacy-owner-source-'));
  try {
    const read = createReader({ scratch, environment, rejectSelectedNonRegular: true, maxRepositories: sources.length, maxPaths: maximumTreePaths, maxBytes: maximumTotalBytes });
    let totalBytes = 0;
    const owners = [];
    for (const source of sources) {
      const selected = new Set(source.paths);
      const received = await read({ repository: source.repository, commit: source.commit, scope: '', selectFile: path => selected.has(path), enterDirectory: () => false });
      if (!Array.isArray(received) || received.length !== selected.size) throw new TypeError('selected owner files were not all received: ' + source.id);
      const seen = new Set();
      const files = received.map(file => {
        if (!selected.has(file.path) || seen.has(file.path) || !['100644', '100755'].includes(file.mode)
          || !Buffer.isBuffer(file.bytes) || file.source?.repository !== source.repository || file.source?.commit !== source.commit || file.source?.path !== file.path)
          throw new TypeError('owner source provenance differs: ' + source.id);
        seen.add(file.path);
        totalBytes += file.bytes.length;
        if (file.bytes.length > maximumFileBytes || totalBytes > maximumTotalBytes) throw new RangeError('owner source byte bound exceeded');
        const object = createHash(source.commit.length === 40 ? 'sha1' : 'sha256').update('blob ' + file.bytes.length + '\0').update(file.bytes).digest('hex');
        if (file.source.object !== object) throw new TypeError('owner source blob identity differs: ' + source.id);
        const text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(file.bytes);
        return { path: file.path, mode: file.mode, bytes: file.bytes.length, sha256: createHash('sha256').update(file.bytes).digest('hex'),
          source: { repository: source.repository, commit: source.commit, path: file.path, object }, text };
      }).sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
      owners.push({ id: source.id, repository: source.repository, commit: source.commit, files });
    }
    return { kind: 'legacy-pinned-owner-evidence/v1', retirementAuthorized: false, reviewRequired: true, totalBytes, owners };
  } finally { await rm(scratch, { recursive: true, force: true }); }
}
