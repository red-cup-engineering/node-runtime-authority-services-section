import { spawnSync } from 'node:child_process';
import { realpathSync, statSync, readFileSync } from 'node:fs';
import { resolve, relative, isAbsolute } from 'node:path';
import { createHash } from 'node:crypto';

/** Bounded compiler adapter. The surrounding service MUST authorize callers,
 * pin workspace revisions and isolate CPU/memory/processes.
 * The lake override is only for trusted operators and test injection.
 */
export function checkLean({workspace, file, lake = 'lake', timeoutMs = 15000}) {
  if (typeof workspace !== 'string' || !workspace || typeof file !== 'string' || !file.endsWith('.lean') || file.includes('\0')) throw new TypeError('invalid workspace/file');
  if (!Number.isInteger(timeoutMs) || timeoutMs < 100 || timeoutMs > 60000) throw new RangeError('invalid timeout');
  const root = realpathSync(workspace);
  const target = realpathSync(resolve(root, file));
  const rel = relative(root, target);
  if (!rel || rel === '..' || rel.startsWith('../') || isAbsolute(rel) || !statSync(target).isFile()) throw new Error('file outside workspace');
  const sourceSha256 = createHash('sha256').update(readFileSync(target)).digest('hex');
  const started = Date.now();
  const proc = spawnSync(lake, ['env', 'lean', rel], {
    cwd: root, timeout: timeoutMs, encoding: 'utf8', maxBuffer: 1024 * 1024,
    shell: false,
    env: {PATH: process.env.PATH ?? '/usr/bin:/bin', HOME: process.env.HOME ?? '/tmp'}
  });
  return {
    kind: 'lean.check.receipt', file: rel, sourceSha256,
    exitCode: proc.status, timedOut: proc.error?.code === 'ETIMEDOUT',
    error: proc.error?.message ?? null, stdout: proc.stdout ?? '',
    stderr: proc.stderr ?? '', elapsedMs: Date.now() - started,
    compilerSucceeded: proc.status === 0 && !proc.error,
    kernelVerified: false
  };
}
