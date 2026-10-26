/** Storage admission for one explicitly budgeted fabrication stage. No reservation or cleanup. */
import { statSync, statfsSync, realpathSync, openSync, closeSync, constants, fstatSync, lstatSync, readSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { release } from 'node:os';
import { isAbsolute, dirname, resolve, join, basename } from 'node:path';
import { setImmediate } from 'node:timers/promises';
import { createHash } from 'node:crypto';

const need = (ok, message) => { if (!ok) throw new TypeError(message); };
const line = v => typeof v === 'string' && v.trim().length > 0 && !/[\r\n\0]/u.test(v);
const count = v => Number.isSafeInteger(v) && v >= 0;
const absolute = v => line(v) && isAbsolute(v) && resolve(v) === v;
const HEX = /^[a-f0-9]{64}$/u;

/** Receive the actual mutable-data owner, never a home/installed-package default.
 * This is a metadata admission, not a sandbox or a claim of exclusive access.
 * Native store/profile/source input ports keep their separate original contracts.
 */
export function receiveOwnerDataRoot(root) {
  need(absolute(root) && basename(root) === 'data' && basename(dirname(root)).endsWith('-services-section')
    && !root.includes('/.local/') && !root.includes('/node_modules/') && !root.startsWith('/gnu/store/'),
  'ownerDataRoot must name the actual owning services-section/data; no home or installed-package fallback');
  const info = lstatSync(root);
  need(info.isDirectory() && realpathSync(root) === root, 'ownerDataRoot must be an existing unredirected directory');
  return root;
}

/** Missing descendants are allowed, but existing redirected/wrong-kind paths are not. */
export function receiveOwnedDataDestination(ownerDataRoot, destination, { kind = 'directory', label = 'data destination' } = {}) {
  const root = receiveOwnerDataRoot(ownerDataRoot);
  need(['directory', 'file'].includes(kind), 'owned destination kind must be directory or file');
  need(absolute(destination) && destination.startsWith(root + '/'), `${label} must be strictly inside ownerDataRoot`);
  let at = destination, target = true;
  while (true) {
    let info;
    try { info = lstatSync(at); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (info) {
      need((target && kind === 'file' ? info.isFile() : info.isDirectory()) && realpathSync(at) === at,
        `${label} or existing parent is redirected or has the wrong kind`);
      break;
    }
    at = dirname(at); target = false;
  }
  return destination;
}

/** The original formation and promotion entrances share the same mutable work law. */
export function receiveReleaseWork(options) {
  receiveOwnedDataDestination(options.ownerDataRoot, options.work, { label: 'work' });
  receiveOwnedDataDestination(options.ownerDataRoot, join(options.work, 'logs'), { label: 'work logs' });
  return options.work;
}

/** Receive writer destinations before storage callbacks, native commands or mkdir. */
export function receiveReleaseFormationDestinations(options, { uncached = false } = {}) {
  receiveReleaseWork(options);
  receiveOwnedDataDestination(options.ownerDataRoot, options.productRoots, { label: 'productRoots' });
  if (options.output !== undefined) receiveOwnedDataDestination(options.ownerDataRoot, options.output, { kind: 'file', label: 'output' });
  if (uncached) for (const key of ['pnpmStore', 'pnpmCache'])
    receiveOwnedDataDestination(options.ownerDataRoot, options[key], { label: key });
  return options;
}

/** Shared lifecycle metadata; these fields describe custody, never prove a resource unreferenced. */
export function validateStageLifecycle(value) {
  need(value && typeof value === 'object', 'stage lifecycle required');
  for (const k of ['owner', 'invocation', 'purpose', 'retention']) need(line(value[k]), `lifecycle.${k} required`);
  need(['reproducible', 'unique'].includes(value.kind), 'lifecycle.kind required');
  need(['planned', 'active', 'received', 'refused', 'failed', 'unknown'].includes(value.status), 'lifecycle.status required');
  need(Array.isArray(value.source) && value.source.length > 0 && value.source.length <= 32, 'lifecycle.source required');
  for (const s of value.source) need(s && line(s.repository) && /^[a-f0-9]{40}$/u.test(s.commit) && line(s.path), 'invalid lifecycle source');
  need(Array.isArray(value.custody) && value.custody.length <= 128, 'lifecycle.custody required');
  for (const c of value.custody) need(c && absolute(c.path) && HEX.test(c.sha256) && ['creation', 'terminal', 'independent-receiving', 'product'].includes(c.role), 'invalid lifecycle custody');
  return structuredClone(value);
}

export function validateStoragePlan(value) {
  need(value?.version === 1 && Array.isArray(value.stages) && value.stages.length > 0 && value.stages.length <= 32, 'invalid fabrication storage plan');
  const names = new Set();
  for (const stage of value.stages) {
    need(stage && /^[a-z0-9][a-z0-9._-]{0,79}$/u.test(stage.name) && !names.has(stage.name), 'invalid or duplicate storage stage'); names.add(stage.name);
    validateStageLifecycle(stage.lifecycle);
    if (stage.backingCapacity !== undefined) validateBackingCapacityPort(stage.backingCapacity);
    const h = stage.headroom;
    need(h && typeof h.minFreePercent === 'number' && h.minFreePercent >= 0 && h.minFreePercent < 100 && /^\d+(?:\.\d{1,6})?$/u.test(String(h.minFreePercent)), 'explicit minFreePercent required');
    for (const k of ['minFreeInodes', 'growthBytes', 'growthInodes']) need(count(h[k]), `explicit ${k} required`);
    need(Array.isArray(stage.destinations) && stage.destinations.length > 0 && stage.destinations.length <= 32, 'stage destinations required');
    const paths = new Set();
    for (const d of stage.destinations) {
      need(d && absolute(d.path) && !paths.has(d.path), 'invalid or duplicate storage destination'); paths.add(d.path);
      need(count(d.peakBytes) && count(d.peakInodes), 'explicit peak bytes and inodes required');
      need(line(d.basis) && ['estimate', 'upper-bound'].includes(d.estimateKind), 'peak basis and estimateKind required');
    }
    need(Array.isArray(stage.command) && stage.command.length > 0 && stage.command.length <= 512 && absolute(stage.command[0]) && stage.command.every(v => typeof v === 'string' && !v.includes('\0')), 'exact absolute stage command required');
  }
  return structuredClone(value);
}

/** Bounded exact regular bytes shared by finite source-owned stage inputs. */
export function readRegularBytes(path, { maxBytes = 131072 } = {}) {
  need(Number.isSafeInteger(maxBytes) && maxBytes > 0 && maxBytes <= 33554432, 'regular input byte bound must be within 32 MiB');
  const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK); let bytes;
  try {
    const before = fstatSync(fd, { bigint: true });
    need(before.isFile() && before.size <= BigInt(maxBytes), `regular input exceeds ${maxBytes} byte bound`);
    const buffer = Buffer.alloc(maxBytes + 1); let used = 0, n;
    while ((n = readSync(fd, buffer, used, buffer.length - used, null)) > 0) { used += n; need(used <= maxBytes, `regular input exceeds ${maxBytes} byte bound`); }
    const after = fstatSync(fd, { bigint: true }), selected = lstatSync(path, { bigint: true });
    need(!['dev', 'ino', 'size', 'mtimeNs', 'ctimeNs'].some(k => before[k] !== after[k] || after[k] !== selected[k]), 'regular input changed during receiving');
    bytes = buffer.subarray(0, used);
  } finally { closeSync(fd); }
  return bytes;
}

/** One bounded regular-file receiving boundary for both existing CLI entrances. */
export function receiveStoragePlan(path, expectedDigest) {
  const bytes = readRegularBytes(path);
  const digest = createHash('sha256').update(bytes).digest('hex');
  need(expectedDigest === undefined || expectedDigest === digest, 'storage plan digest mismatch');
  return { plan: validateStoragePlan(JSON.parse(bytes)), digest };
}

function ancestor(destination) {
  let p = destination;
  for (let depth = 0; depth < 128; depth++) {
    try { return { path: p, realpath: realpathSync(p), stat: statSync(p, { bigint: true }) }; }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    const next = dirname(p); need(next !== p, 'cannot locate destination filesystem'); p = next;
  }
  throw new Error('destination ancestor bound exceeded');
}

/** Metadata only; no mkdir, traversal, payload reads or Guix queries. */
export function observeStorageStage(stage) {
  const requiresBacking = /microsoft|wsl/iu.test(release()) || Boolean(process.env.WSL_DISTRO_NAME || process.env.WSL_INTEROP);
  return stage.destinations.map(d => {
    const a = ancestor(d.path), s = statfsSync(a.realpath, { bigint: true });
    return { destination: d.path, ancestor: a.path, realpath: a.realpath, device: String(a.stat.dev),
      blockSize: String(s.bsize), blocks: String(s.blocks), availableBlocks: String(s.bavail),
      inodes: String(s.files), freeInodes: String(s.ffree), requiresBacking, at: new Date().toISOString() };
  });
}

function integer(v, name) { need(typeof v === 'string' && /^\d+$/u.test(v), `unknown ${name}`); return BigInt(v); }
function share(total, percent) {
  const [whole, fraction = ''] = String(percent).split('.'), scale = 10n ** BigInt(fraction.length);
  const numerator = BigInt(whole) * scale + BigInt(fraction || '0'), denominator = 100n * scale;
  return (total * numerator + denominator - 1n) / denominator;
}

/** All simultaneous allocations on one filesystem are charged together. */
export function assessStorageStage(stage, observations, { chargePeaks = true } = {}) {
  need(Array.isArray(observations) && observations.length === stage.destinations.length, 'incomplete filesystem observations');
  const groups = new Map(), destinations = new Map(stage.destinations.map(d => [d.path, d]));
  for (const o of observations) {
    const d = destinations.get(o.destination); need(d, 'unexpected filesystem observation'); destinations.delete(o.destination);
    need(line(o.device), 'unknown filesystem device');
    const bs = integer(o.blockSize, 'allocation block size'), blocks = integer(o.blocks, 'blocks'), available = integer(o.availableBlocks, 'available blocks'), inodes = integer(o.inodes, 'inode total'), free = integer(o.freeInodes, 'free inodes');
    need(bs > 0n && blocks > 0n && available <= blocks && inodes > 0n && free <= inodes, 'unmeasurable filesystem capacity');
    let g = groups.get(o.device);
    if (!g) { g = { device: o.device, bytes: blocks * bs, availableBytes: available * bs, inodes, freeInodes: free, blockSize: bs, peakBytes: 0n, peakInodes: 0n, paths: [], requiresBacking: false }; groups.set(o.device, g); }
    g.requiresBacking ||= o.requiresBacking === true;
    need(g.bytes === blocks * bs && g.inodes === inodes && g.blockSize === bs, 'filesystem changed during observation');
    // A concurrent allocation between samples is charged by keeping the least available observation.
    g.availableBytes = g.availableBytes < available * bs ? g.availableBytes : available * bs;
    g.freeInodes = g.freeInodes < free ? g.freeInodes : free;
    if (chargePeaks) { const bytes = BigInt(d.peakBytes); g.peakBytes += ((bytes + bs - 1n) / bs) * bs; g.peakInodes += BigInt(d.peakInodes); }
    g.paths.push(d.path);
  }
  const h = stage.headroom;
  const filesystems = [...groups.values()].map(g => {
    const reserveBytes = share(g.bytes, h.minFreePercent), requiredBytes = reserveBytes + BigInt(h.growthBytes) + g.peakBytes;
    const requiredInodes = BigInt(h.minFreeInodes) + BigInt(h.growthInodes) + g.peakInodes;
    return { ...Object.fromEntries(Object.entries(g).map(([k, v]) => [k, typeof v === 'bigint' ? String(v) : v])), reserveBytes: String(reserveBytes), requiredBytes: String(requiredBytes), requiredInodes: String(requiredInodes), admitted: g.availableBytes >= requiredBytes && g.freeInodes >= requiredInodes };
  });
  return { admitted: filesystems.every(f => f.admitted), filesystems, admissionKind: 'snapshot-not-reservation', concurrency: 'Owner growth allowance is charged; unrelated concurrent activity can change capacity after this observation.' };
}

/** Only the original machine-owner capacity protocol, never an arbitrary argv probe. */
export function validateBackingCapacityPort(port) {
  need(port?.kind === 'wsl-host-service/1', 'original WSL machine-owner backing capacity port required');
  for (const k of ['node', 'script', 'parameters']) need(absolute(port[k]), `backing capacity ${k} required`);
  for (const k of ['scriptSha256', 'parametersSha256']) need(HEX.test(port[k]), `backing capacity ${k} required`);
  const root = dirname(dirname(port.script)), names = ['scripts/wsl-host.mjs', 'src/wsl-host.mjs', 'src/backing-capacity.mjs', 'assets/observe-backing-capacity.ps1'];
  need(port.script === join(root, names[0]), 'original machine-owner capacity CLI path required');
  need(Array.isArray(port.sourceFiles) && port.sourceFiles.length === names.length, 'complete finite machine-owner source closure required');
  const files = new Map();
  for (const f of port.sourceFiles) { need(absolute(f?.path) && HEX.test(f.sha256) && !files.has(f.path), 'invalid or duplicate machine-owner source file'); files.set(f.path, f.sha256); }
  need(names.every(p => files.has(join(root, p))) && files.get(port.script) === port.scriptSha256, 'machine-owner executable source closure differs');
  need(Object.keys(port).every(k => ['kind', 'node', 'script', 'scriptSha256', 'parameters', 'parametersSha256', 'sourceFiles'].includes(k)), 'unknown backing capacity port field');
  return port;
}

export function observeBackingCapacity(stage, observations) {
  if (!stage.backingCapacity) {
    need(!observations.some(o => o.requiresBacking), 'WSL destination requires declared physical backing capacity');
    return null;
  }
  const p = validateBackingCapacityPort(stage.backingCapacity), paths = [...new Set(observations.map(o => o.destination))];
  need(paths.length > 0 && paths.length <= 32, 'backing capacity destination bound exceeded');
  need(realpathSync(p.node) === realpathSync(process.execPath), 'backing capacity must use the qualified current Node supplier');
  const bindings = [...p.sourceFiles, { path: p.parameters, sha256: p.parametersSha256 }];
  const inputs = bindings.map(b => ({ ...b, bytes: readRegularBytes(b.path, { maxBytes: b.path === p.parameters ? 131072 : 1048576 }) }));
  for (const b of inputs) need(createHash('sha256').update(b.bytes).digest('hex') === b.sha256, 'backing capacity source/parameters changed');
  const result = spawnSync(p.node, [p.script, 'capacity', '--parameters=' + p.parameters, '--destinations-json=' + JSON.stringify(paths)],
    { timeout: 15000, killSignal: 'SIGKILL', maxBuffer: 65536, stdio: ['ignore', 'pipe', 'pipe'] });
  const stderr = result.stderr ?? Buffer.alloc(0);
  const refusal = errorCode => {
    const error = new Error('original machine-owner capacity probe refused or is unknown');
    error.backingCapacityProbe = { status: result.status, signal: result.signal,
      errorCode: errorCode ?? (/^[A-Z0-9_]+$/u.test(result.error?.code ?? '') ? result.error.code : null),
      stderrBytes: stderr.length, stderrSha256: createHash('sha256').update(stderr).digest('hex') };
    return error;
  };
  if (result.error || result.status !== 0 || result.signal !== null || stderr.length) throw refusal();
  const response = result.stdout.toString('utf8');
  for (const b of inputs) need(readRegularBytes(b.path, { maxBytes: b.path === p.parameters ? 131072 : 1048576 }).equals(b.bytes), 'backing capacity source/parameters changed during observation');
  let value;
  try { value = JSON.parse(response); } catch { throw refusal('ERR_CAPACITY_RESPONSE_JSON'); }
  return { ...value, port: p, responseSha256: createHash('sha256').update(result.stdout).digest('hex') };
}

/** Logical capacity and physical capacity are independent constraints. */
export function assessBackingCapacity(assessment, observations, observed, { chargePeaks = true, now = Date.now() } = {}) {
  if (observed === null) { need(!observations.some(o => o.requiresBacking), 'missing physical backing observation'); return null; }
  need(observed?.type === 'WslBackingVolumeCapacity' && observed.version === 1, 'invalid machine-owner backing capacity observation');
  const at = Date.parse(observed.at);
  need(Number.isFinite(at) && new Date(at).toISOString() === observed.at && now - at <= 30000 && at - now <= 1000, 'stale or invalid physical backing observation');
  need(Array.isArray(observed.mappings) && observed.mappings.length <= 32 && Array.isArray(observed.volumes) && observed.volumes.length <= 32, 'invalid backing mappings/volumes');
  const wanted = new Map();
  for (const o of observations) { const previous = wanted.get(o.destination); need(!previous || previous.device === o.device, 'destination device changed during backing observation'); wanted.set(o.destination, o); }
  const mappings = new Map(), devices = new Map();
  for (const m of observed.mappings) {
    need(absolute(m.path) && absolute(m.linuxMount) && line(m.volumeId) && line(m.device) && !mappings.has(m.path), 'invalid or duplicate backing mapping');
    need(wanted.get(m.path)?.device === m.device, 'unknown or mismatched backing destination device');
    need(!devices.has(m.device) || devices.get(m.device) === m.volumeId, 'one destination filesystem mapped to different backing volumes');
    mappings.set(m.path, m); devices.set(m.device, m.volumeId);
  }
  need(mappings.size === wanted.size && [...wanted.keys()].every(p => mappings.has(p)), 'unmapped physical backing destination');
  const ids = new Set(), volumes = [];
  for (const v of observed.volumes) {
    need(line(v.id) && !ids.has(v.id), 'invalid or duplicate physical volume'); ids.add(v.id);
    const total = integer(v.totalBytes, 'physical total bytes'), available = integer(v.availableBytes, 'physical available bytes'), unit = integer(v.allocationUnitBytes, 'physical allocation unit');
    need(total > 0n && available <= total && unit > 0n, 'unknown physical volume capacity');
    const p = v.policy;
    need(p && typeof p.minFreePercent === 'number' && p.minFreePercent >= 0 && p.minFreePercent < 100 && /^\d+(?:\.\d{1,6})?$/u.test(String(p.minFreePercent)), 'independent physical free-share policy required');
    const minimum = integer(p.minFreeBytes, 'physical minimum bytes'), growth = integer(p.growthBytes, 'physical growth bytes'), overhead = integer(p.overheadBytes, 'physical allocation overhead');
    need(v.vhd && line(v.vhd.path) && typeof v.vhd.sparse === 'boolean' && Number.isSafeInteger(v.vhd.attributes) && v.vhd.attributes >= 0, 'physical VHD identity required'); integer(v.vhd.lengthBytes, 'VHD length');
    const fs = assessment.filesystems.filter(f => devices.get(f.device) === v.id);
    need(fs.length > 0, 'unreferenced physical volume');
    const peak = fs.reduce((n, f) => n + ((BigInt(f.peakBytes) + unit - 1n) / unit) * unit, 0n);
    const percent = share(total, p.minFreePercent), reserve = minimum > percent ? minimum : percent;
    const required = reserve + growth + peak + (chargePeaks ? overhead : 0n);
    volumes.push({ ...v, peakBytes: String(peak), reserveBytes: String(reserve), requiredBytes: String(required), devices: fs.map(f => f.device), admitted: available >= required });
  }
  need([...devices.values()].every(id => ids.has(id)), 'missing physical volume observation');
  return { at: observed.at, mappings: [...mappings.values()], volumes, port: observed.port ?? null, responseSha256: observed.responseSha256 ?? null, admitted: volumes.every(v => v.admitted), admissionKind: 'snapshot-not-reservation' };
}

function backingIdentity(value) {
  if (!value) return null;
  return { mappings: value.mappings.map(m => [m.path, m.device, m.linuxMount, m.volumeId]).sort((a, b) => a[0].localeCompare(b[0])),
    volumes: value.volumes.map(v => [v.id, v.totalBytes, v.allocationUnitBytes, v.vhd.path]).sort((a, b) => a[0].localeCompare(b[0])) };
}

/** The same actual-path coverage receiving used before dispatch and each growth phase. */
export async function observeStorageAdmission(stage, requiredPaths = [], observe = observeStorageStage, observeBacking = observeBackingCapacity) {
  need(Array.isArray(requiredPaths) && requiredPaths.length <= 128 && requiredPaths.every(absolute), 'invalid required fabrication destinations');
  const requiredStage = { ...stage, destinations: [...new Set(requiredPaths)].map(path => ({ path })) };
  const requiredBefore = requiredPaths.length ? await observe(requiredStage) : [];
  const requiredAssessment = requiredPaths.length ? assessStorageStage(requiredStage, requiredBefore, { chargePeaks: false }) : null;
  const beforeObservations = await observe(stage), before = assessStorageStage(stage, beforeObservations);
  const covered = new Set(before.filesystems.filter(f => BigInt(f.peakBytes) > 0n && BigInt(f.peakInodes) > 0n).map(f => f.device));
  const uncovered = requiredBefore.filter(o => !covered.has(o.device)).map(o => o.destination);
  if (uncovered.length) return { admitted: false, reason: 'uncovered-fabrication-destination', uncovered, before, beforeObservations, requiredBefore, requiredStage };
  for (const f of requiredAssessment?.filesystems ?? []) {
    const declared = before.filesystems.find(d => d.device === f.device);
    need(declared && ['blockSize', 'bytes', 'inodes'].every(k => declared[k] === f[k]), 'destination filesystem changed during coverage receiving');
  }
  if (!before.admitted || (requiredAssessment && !requiredAssessment.admitted)) return { admitted: false, reason: 'storage-headroom', before, beforeObservations, requiredBefore, requiredStage };
  const backing = assessBackingCapacity(before, [...beforeObservations, ...requiredBefore], await observeBacking(stage, [...beforeObservations, ...requiredBefore]));
  before.backing = backing; before.admitted &&= backing?.admitted ?? true;
  return { admitted: before.admitted && (!requiredAssessment || requiredAssessment.admitted), reason: before.admitted && (!requiredAssessment || requiredAssessment.admitted) ? null : 'storage-headroom', before, beforeObservations, requiredBefore, requiredStage };
}

export async function runStorageStage(plan, name, { observe = observeStorageStage, observeBacking = observeBackingCapacity, execute, interrupted = () => false, onAdmission = () => {}, requiredPaths = [], operationIdentity = null } = {}) {
  const received = validateStoragePlan(plan), stage = received.stages.find(s => s.name === name);
  need(stage, 'unknown storage stage'); need(stage.lifecycle.status === 'planned', 'only a planned stage may execute'); need(typeof execute === 'function', 'stage executor required');
  const admission = await observeStorageAdmission(stage, requiredPaths, observe, observeBacking);
  const { before, beforeObservations, requiredBefore, requiredStage } = admission;
  if (!admission.admitted) return { stage: name, executed: false, state: 'refused', reason: admission.reason, uncovered: admission.uncovered ?? [], before };
  await onAdmission({ phase: 'admitted-before-dispatch', stage: name, lifecycle: stage.lifecycle, destinations: stage.destinations, headroom: stage.headroom, ...(operationIdentity ? { operationIdentity } : { command: stage.command }), requiredDestinations: requiredBefore, before });
  // Let pending native signals run before the original operation. The outer manager's
  // control-group stop remains the process fence; this is not an atomic signal barrier.
  await setImmediate();
  if (interrupted()) return { stage: name, executed: false, state: 'interrupted', reason: 'interrupted-before-dispatch', before };
  // No materialization occurs between the fresh observation and this original operation seam.
  let result, error;
  try { result = await execute(stage.command, stage); } catch (e) { error = e; }
  let after, observationError, probeDiagnostic, filesystemDrift = [];
  try {
    const requiredAfter = requiredPaths.length ? await observe(requiredStage) : [];
    const observations = await observe(stage); after = assessStorageStage(stage, observations, { chargePeaks: false });
    after.backing = assessBackingCapacity(after, [...observations, ...requiredAfter], await observeBacking(stage, [...observations, ...requiredAfter]), { chargePeaks: false });
    after.admitted &&= after.backing?.admitted ?? true;
    if (JSON.stringify(backingIdentity(before.backing)) !== JSON.stringify(backingIdentity(after.backing))) filesystemDrift.push({ destination: 'physical-backing', changed: ['mapping/volume identity'] });
    for (const before of [...beforeObservations, ...requiredBefore]) {
      const current = [...observations, ...requiredAfter].find(o => o.destination === before.destination);
      const changed = ['device', 'blockSize', 'blocks', 'inodes'].filter(k => current?.[k] !== before[k]);
      if (changed.length) filesystemDrift.push({ destination: before.destination, changed });
    }
  } catch (e) { observationError = e.message; probeDiagnostic = e.backingCapacityProbe; }
  const wasInterrupted = interrupted() || result?.interrupted === true;
  const reason = wasInterrupted ? 'interrupted' : error || result?.code !== 0 ? 'original-command-failed' : observationError ? 'post-stage-observation-unknown' : filesystemDrift.length ? 'destination-filesystem-changed' : !after?.admitted ? 'post-stage-headroom' : null;
  return { stage: name, executed: true, state: wasInterrupted ? 'interrupted' : reason ? 'failed' : 'completed', reason, before, after: after ?? null, filesystemDrift, observationError: observationError ?? null,
    commandResult: result ?? null, error: error ? error.message : null,
    backingCapacityProbe: probeDiagnostic ?? error?.backingCapacityProbe ?? null };
}
