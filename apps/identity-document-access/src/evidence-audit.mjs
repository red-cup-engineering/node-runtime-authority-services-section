import { constants, readFileSync } from 'node:fs';
import { lstat, open, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { validateJsonSchema } from '@red-cup-engineering/json-schema-services-section/validation';
import { validateAssessmentDate } from './identity-access.mjs';

const schema = JSON.parse(readFileSync(new URL('../data/schemas/evidence-manifest.schema.json', import.meta.url)));
const safeName = value => typeof value === 'string' && value !== '.' && value !== '..' && !/[\\/\0]/.test(value);

export async function auditEvidence({ manifestPath, caseId, asOf }) {
  validateAssessmentDate(asOf);
  if (typeof caseId !== 'string' || !caseId) throw new TypeError('An explicit case ID is required for evidence audit');
  const result = { kind: 'identity-evidence-audit', caseId, asOf, manifestProblems: [], items: [], state: 'unavailable', limits: 'Local availability and retained-byte integrity only; no document authenticity, certification, legal acceptance or authority established.' };
  if (!manifestPath) { result.manifestProblems.push('manifest-not-bound'); return result; }
  let manifest;
  try {
    if (!(await lstat(manifestPath)).isFile()) { result.manifestProblems.push('manifest-not-regular-file'); return result; }
    manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  } catch { result.manifestProblems.push('manifest-unreadable'); return result; }
  if (!validateJsonSchema(manifest, schema).valid) { result.manifestProblems.push('manifest-invalid'); return result; }
  if (manifest.caseId !== caseId) { result.manifestProblems.push('manifest-case-mismatch'); return result; }
  if (new Set(manifest.artifacts.map(a => a.sourceId)).size !== manifest.artifacts.length) { result.manifestProblems.push('duplicate-artifact-source'); return result; }
  for (const artifact of manifest.artifacts) {
    const issues = [];
    let handle;
    try {
      if (!safeName(artifact.file)) issues.push('artifact-path-not-contained');
      else {
        const path = resolve(dirname(manifestPath), artifact.file);
        if (!(await lstat(path)).isFile()) issues.push('artifact-not-regular-file');
        else {
          handle = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW);
          const before = await handle.stat();
          if (before.size !== artifact.bytes) issues.push('artifact-size-mismatch');
          else {
            const hash = createHash('sha256');
            for await (const chunk of handle.createReadStream({ autoClose: false })) hash.update(chunk);
            if (hash.digest('hex') !== artifact.sha256) issues.push('artifact-digest-mismatch');
            const after = await handle.stat();
            if (before.size !== after.size || before.mtimeMs !== after.mtimeMs || before.ctimeMs !== after.ctimeMs) issues.push('artifact-changed-during-audit');
          }
        }
      }
    } catch { issues.push('artifact-unavailable'); }
    finally { await handle?.close().catch(() => {}); }
    result.items.push({ sourceId: artifact.sourceId, state: issues.length ? 'unverified' : 'verified', issues });
  }
  result.state = result.items.every(item => item.state === 'verified') ? 'verified' : 'incomplete';
  return result;
}
