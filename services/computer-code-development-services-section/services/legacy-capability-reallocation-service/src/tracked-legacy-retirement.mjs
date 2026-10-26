import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {lstatSync, readFileSync, readlinkSync, realpathSync, unlinkSync} from 'node:fs';
import {isAbsolute, relative, resolve, sep} from 'node:path';

const git = (root, args) => execFileSync('git', ['-C', root, ...args], {maxBuffer: 32 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe']});
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const validPath = value => typeof value === 'string' && value.length > 0 && !isAbsolute(value) && !value.split('/').some(x => !x || x === '.' || x === '..');
function confined(root, path) {
  if (!validPath(path)) throw new TypeError('exact repository-relative path required');
  const absolute = resolve(root, path);
  if (relative(root, absolute).split(sep)[0] === '..') throw new TypeError('path escapes repository');
  return absolute;
}
function noLinkedParents(root, path) {
  const parts = relative(root, path).split(sep);
  let here = root;
  for (const part of parts.slice(0, -1)) {
    here = resolve(here, part);
    if (lstatSync(here).isSymbolicLink()) throw new Error('symbolic-link ancestor');
  }
}
function bytesAndMode(root, path) {
  noLinkedParents(root, path);
  const stat = lstatSync(path);
  if (stat.isSymbolicLink()) return {bytes: Buffer.from(readlinkSync(path)), mode: '120000'};
  if (!stat.isFile()) throw new Error('source is not a regular file or link');
  return {bytes: readFileSync(path), mode: stat.mode & 0o100 ? '100755' : '100644'};
}

function indexEntries(root, roots) {
  return new Map(git(root, ['ls-files', '--stage', '-z', '--', ...roots]).toString().split('\0').filter(Boolean).map(row => {
    const tab = row.indexOf('\t');
    return [row.slice(tab + 1), row.slice(0, tab)];
  }));
}
function requireAbsent(root, path, message) {
  try { noLinkedParents(root, confined(root, path)); lstatSync(confined(root, path)); }
  catch (error) { if (error.code === 'ENOENT') return; throw error; }
  throw new Error(message);
}
function workingCut(plan) {
  const root = resolve(plan.repositoryRoot), moved = plan.workingLegacyRoot !== undefined;
  const workingLegacyRoot = plan.workingLegacyRoot ?? plan.legacyRoot;
  const index = indexEntries(root, moved ? [plan.legacyRoot, workingLegacyRoot] : [plan.legacyRoot]);
  if (!moved) return {workingLegacyRoot, index};
  const originalHead = new Map(inventoryTrackedLegacyCapabilities({...plan, revision:'HEAD'}).entries.map(row => [row.path, row]));
  const workingHead = new Map(inventoryTrackedLegacyCapabilities({...plan, legacyRoot:workingLegacyRoot, revision:'HEAD'}).entries.map(row => [row.path, row]));
  return {workingLegacyRoot, index, originalHead, workingHead};
}
function admitStagedMove(root, plan, cut, original) {
  const oldPath = plan.legacyRoot + '/' + original.path, newPath = cut.workingLegacyRoot + '/' + original.path;
  if (cut.index.has(oldPath)) throw new Error('original path is still indexed; not an exact staged relocation');
  requireAbsent(root, oldPath, 'original working source was recreated during relocation');
  const current = cut.originalHead.get(original.path);
  if (current && (current.blob !== original.blob || current.mode !== original.mode || current.type !== 'blob')) throw new Error('original HEAD changed during relocation');
  if (cut.workingHead.has(original.path)) throw new Error('moved source already exists in HEAD; not an uncommitted relocation');
  if (!current && cut.index.has(newPath)) throw new Error('moved source was recreated after retirement');
}

/** Metadata only, selected Git subtree only. No worktree walk or source-body census. */
export function inventoryTrackedLegacyCapabilities({repositoryRoot, legacyRoot, revision = 'HEAD'}) {
  const root = resolve(repositoryRoot);
  if (git(root, ['rev-parse', '--show-toplevel']).toString().trim() !== root) throw new TypeError('repositoryRoot must be its actual Git root');
  confined(root, legacyRoot);
  if (!legacyRoot.split('/').includes('legacy')) throw new TypeError('an explicit legacy subtree is required');
  const commit = git(root, ['rev-parse', '--verify', `${revision}^{commit}`]).toString().trim();
  const rows = git(root, ['ls-tree', '-rz', commit, '--', legacyRoot]).toString().split('\0').filter(Boolean);
  const entries = rows.map(row => {
    const tab = row.indexOf('\t');
    const [mode, type, blob] = row.slice(0, tab).split(' ');
    const path = row.slice(tab + 1);
    if (!path.startsWith(legacyRoot + '/')) throw new TypeError('legacyRoot must be a directory subtree');
    return {path: path.slice(legacyRoot.length + 1), mode, type, blob};
  });
  return {kind: 'tracked-legacy-capability-inventory/v1', repositoryRoot: root, legacyRoot, revision: commit, entries};
}

/** Shared declaration contract; this validates no capability judgment or Git custody. */
export function readTrackedLegacyRetirementPlan(plan) {
  if (plan?.kind !== 'legacy-capability-retirement-plan/v1' || !Array.isArray(plan.capabilities)) throw new TypeError('capability retirement plan required');
  if (plan.sourceLegacyRoot !== undefined && (!validPath(plan.sourceLegacyRoot)
      || /[\0\r\n\t]/u.test(plan.sourceLegacyRoot) || !plan.sourceLegacyRoot.split('/').includes('legacy')
      || plan.sourceLegacyRoot.split(/[\\/]/u).some(part => part.toLowerCase() === '.git' || part === '..')))
    throw new TypeError('confined source legacy root required');
  if (plan.workingLegacyRoot !== undefined) {
    const moved = plan.workingLegacyRoot, original = plan.legacyRoot;
    if (!validPath(moved) || /[\0\r\n\t]/u.test(moved) || moved.split('/').some(part => part.toLowerCase() === '.git')
        || !moved.split('/').includes('legacy') || !validPath(original) || moved === original
        || moved.startsWith(original + '/') || original.startsWith(moved + '/')) throw new TypeError('distinct nonoverlapping confined working legacy root required');
  }
  const ids = new Set(), paths = new Set();
  for (const cap of plan.capabilities) {
    if (typeof cap?.id !== 'string' || !cap.id.trim() || ids.has(cap.id) || !['covered', 'deprecated'].includes(cap.disposition) || !cap.reason?.trim() || !Array.isArray(cap.sourcePaths) || !cap.sourcePaths.length) throw new TypeError('unique capability, disposition, reason and sources required');
    ids.add(cap.id);
    if (cap.disposition === 'deprecated' && !cap.authorization?.trim()) throw new TypeError('deprecation authority required');
    if (cap.disposition === 'covered' && (!Array.isArray(cap.evidence) || !cap.evidence.length)) throw new TypeError('living implementation evidence required');
    for (const path of cap.sourcePaths) {
      if (!validPath(path) || paths.has(path)) throw new TypeError('unknown, repeated or unsafe source: ' + path);
      paths.add(path);
    }
  }
  return plan;
}

/** Reviewer judgments remain explicit; Git custody and local edits are checked mechanically. */
export function retireTrackedLegacyCapabilities({plan, apply = false}) {
  readTrackedLegacyRetirementPlan(plan);
  const inventory = inventoryTrackedLegacyCapabilities(plan);
  if (plan.revision !== inventory.revision) throw new TypeError('retirement requires an immutable commit revision');
  const root = inventory.repositoryRoot;
  const entries = new Map(inventory.entries.map(x => [x.path, x]));
  const cut = workingCut(plan), {index} = cut;
  const algorithm = git(root, ['rev-parse', '--show-object-format']).toString().trim();
  const seen = new Set(), outcomes = [], capabilities = [], evidenceRoots = new Set([root]);
  // Validate the entire declaration before any effects.
  for (const cap of plan.capabilities) {
    for (const path of cap.sourcePaths) {
      if (!validPath(path) || !entries.has(path) || seen.has(path)) throw new TypeError('unknown, repeated or unsafe source: ' + path);
      seen.add(path);
    }
  }
  for (const cap of plan.capabilities) {
    const witnesses = [];
    let failure;
    try {
      for (const evidence of cap.evidence ?? []) {
        const evidenceRoot = resolve(evidence.repositoryRoot ?? root);
        if (!evidenceRoots.has(evidenceRoot)) {
          if (git(evidenceRoot, ['rev-parse', '--show-toplevel']).toString().trim() !== evidenceRoot) throw new Error('evidence repositoryRoot must be its actual Git root');
          evidenceRoots.add(evidenceRoot);
        }
        const path = confined(evidenceRoot, evidence.path);
        if (evidence.path.split('/').includes('legacy')) throw new Error('evidence points into legacy');
        const current = bytesAndMode(evidenceRoot, path);
        if (current.mode === '120000') throw new Error('evidence must be an actual living file');
        const sha256 = digest(current.bytes);
        if (evidence.sha256 && evidence.sha256 !== sha256) throw new Error('living evidence changed');
        witnesses.push({...(evidence.repositoryRoot === undefined ? {} : {repositoryRoot: evidenceRoot}), path: evidence.path, sha256});
      }
    } catch (error) { failure = error.message; }
    capabilities.push({id: cap.id, disposition: cap.disposition, witnesses, ...(failure ? {failure} : {})});
    for (const path of cap.sourcePaths) {
      const entry = entries.get(path), full = cut.workingLegacyRoot + '/' + path;
      const outcome = {capability: cap.id, ...entry};
      try {
        if (failure) throw new Error(failure);
        if (entry.type !== 'blob') throw new Error('Gitlink or non-blob source retained');
        if (plan.workingLegacyRoot !== undefined) admitStagedMove(root, plan, cut, entry);
        const source = confined(root, full);
        if (!index.has(full)) {
          try { noLinkedParents(root, source); lstatSync(source); }
          catch (error) { if (error.code === 'ENOENT') { outcomes.push({...outcome, state: 'absent'}); continue; } throw error; }
          throw new Error('untracked source recreated after retirement');
        }
        if (index.get(full) !== `${entry.mode} ${entry.blob} 0`) throw new Error('index differs from selected source');
        let current;
        try { current = bytesAndMode(root, source); }
        catch (error) { if (error.code === 'ENOENT') { outcomes.push({...outcome, state: 'absent'}); continue; } throw error; }
        const blob = createHash(algorithm).update(`blob ${current.bytes.length}\0`).update(current.bytes).digest('hex');
        if (blob !== entry.blob || current.mode !== entry.mode) throw new Error('working bytes or mode differ from selected source');
        if (apply) unlinkSync(source);
        outcomes.push({...outcome, state: apply ? 'removed' : 'eligible'});
      } catch (error) { outcomes.push({...outcome, state: 'held', reason: error.message}); }
    }
  }
  const counts = outcomes.reduce((all, row) => ({...all, [row.state]: (all[row.state] ?? 0) + 1}), {});
  return {kind: 'legacy-capability-retirement-result/v1', repositoryRoot: root, legacyRoot: plan.legacyRoot,
    ...(plan.workingLegacyRoot === undefined ? {} : {workingLegacyRoot:plan.workingLegacyRoot}),
    ...(plan.sourceLegacyRoot === undefined ? {} : {sourceLegacyRoot:plan.sourceLegacyRoot}),
    revision: inventory.revision, apply, inventoryFiles: entries.size, selectedFiles: seen.size, unselectedFiles: entries.size - seen.size, counts, capabilities, outcomes};
}

/** Land only this reviewed batch; unrelated staged changes remain staged. */
export function commitTrackedLegacyRetirement({result}) {
  if (result?.kind !== 'legacy-capability-retirement-result/v1' || result.apply !== true) throw new TypeError('applied retirement result required');
  const root = resolve(result.repositoryRoot);
  const inventory = inventoryTrackedLegacyCapabilities({...result, revision: result.revision});
  const originals = new Map(inventory.entries.map(x => [x.path, x]));
  const head = new Map(inventoryTrackedLegacyCapabilities({...result, revision: 'HEAD'}).entries.map(x => [x.path, x]));
  readTrackedLegacyRetirementPlan({...result, kind:'legacy-capability-retirement-plan/v1', capabilities:[]});
  const cut = workingCut(result), {index} = cut;
  const paths = [], unstaged = [], movedAdditions = [];
  for (const row of result.outcomes) {
    if (!['removed', 'absent'].includes(row.state)) continue;
    const original = originals.get(row.path);
    if (!original || original.type !== 'blob' || original.blob !== row.blob || original.mode !== row.mode) throw new Error('retirement result differs from selected source');
    const full = result.legacyRoot + '/' + row.path;
    if (result.workingLegacyRoot !== undefined) {
      admitStagedMove(root, result, cut, original);
      const working = cut.workingLegacyRoot + '/' + row.path;
      requireAbsent(root, working, 'moved source restored before retirement commit: ' + working);
      if (index.has(working)) {
        if (index.get(working) !== `${original.mode} ${original.blob} 0`) throw new Error('moved index changed before retirement commit');
        movedAdditions.push(working);
      }
      if (head.has(row.path)) paths.push(full);
      continue;
    }
    const source = confined(root, full);
    try { noLinkedParents(root, source); lstatSync(source); }
    catch (error) {
      if (error.code !== 'ENOENT') throw error;
      if (!index.has(full)) {
        const current = head.get(row.path);
        if (!current) continue;
        if (current.blob !== original.blob || current.mode !== original.mode) throw new Error('HEAD changed before retirement commit');
        paths.push(full);
        continue;
      }
      if (index.get(full) !== `${original.mode} ${original.blob} 0`) throw new Error('index changed before retirement commit');
      paths.push(full);
      unstaged.push(full);
      continue;
    }
    throw new Error('source restored before retirement commit: ' + full);
  }
  if (!paths.length) return {state: 'already-landed', commit: git(root, ['rev-parse', 'HEAD']).toString().trim(), retiredFiles: 0};
  const input = Buffer.from(paths.join('\0') + '\0');
  const run = (args, bytes = input) => execFileSync('git', ['--literal-pathspecs', '-C', root, ...args], {input: bytes, maxBuffer: 32 * 1024 * 1024, stdio: ['pipe', 'pipe', 'pipe']});
  if (movedAdditions.length) run(['update-index', '--force-remove', '-z', '--stdin'], Buffer.from(movedAdditions.join('\0') + '\0'));
  if (unstaged.length) run(['add', '-u', '--pathspec-from-file=-', '--pathspec-file-nul'], Buffer.from(unstaged.join('\0') + '\0'));
  run(['commit', '--only', '-m', 'Retire reviewed Git-preserved legacy capabilities', '--pathspec-from-file=-', '--pathspec-file-nul']);
  const landed = inventoryTrackedLegacyCapabilities({...result, revision: 'HEAD'});
  const selected = new Set(paths);
  if (landed.entries.some(x => selected.has(result.legacyRoot + '/' + x.path))) throw new Error('selected source remains in retirement commit');
  const recreatedFiles = [];
  for (const full of [...paths, ...movedAdditions]) {
    try { noLinkedParents(root, confined(root, full)); lstatSync(confined(root, full)); }
    catch (error) { if (error.code === 'ENOENT') continue; }
    recreatedFiles.push(full);
  }
  if (recreatedFiles.length) return {state: 'committed-with-recreated-files', commit: landed.revision, retiredFiles: paths.length, recreatedFiles};
  return {state: 'committed', commit: landed.revision, retiredFiles: paths.length};
}

/** Feed the committed retirement directly to Fabrication's ordinary source
 * maker. This owner supplies the reviewed cut; Fabrication owns GitHub effects,
 * immutable merge receiving and uncertain-effect recovery. */
export async function publishTrackedLegacyRetirement({result, previousPublication, maker}) {
  if (result?.apply !== true || !['committed', 'already-landed'].includes(result.landing?.state)) throw new TypeError('committed retirement required before source publication');
  const selected = result.outcomes.filter(row => ['removed', 'absent'].includes(row.state));
  if (!selected.length) return {ok: true, phase: 'unchanged', paths: []};
  const paths = selected.map(row => (result.sourceLegacyRoot ?? result.legacyRoot) + '/' + row.path);
  let reviewedSource;
  if (!previousPublication?.candidate) {
    const {reviewedSourceForTrackedLegacyRetirement} = await import('./tracked-legacy-source-publication.mjs');
    reviewedSource = await reviewedSourceForTrackedLegacyRetirement(result, selected);
  }
  return publishRetirementPaths({root: result.repositoryRoot, previousPublication, maker, request: {
    paths, message: 'Retire reviewed Git-preserved legacy capabilities', push: true,
    ...(reviewedSource ? {reviewedSource} : {})
  }});
}

async function publishRetirementPaths({root, request, previousPublication, maker}) {
  const paths = request.paths;
  const provider = maker ?? await import('@red-cup-engineering/computer-systems-fabrication-engineering-services-section/git/github-candidate');
  if (previousPublication?.candidate) {
    if (previousPublication.root !== root || JSON.stringify([...previousPublication.paths].sort()) !== JSON.stringify([...paths].sort())) throw new TypeError('retained source publication differs from this retirement cut');
    try {
      const candidate = hasReceivedTrackedLegacyPublication(previousPublication)
        ? provider.receiveCandidateMergeSync({repository: root, candidate: previousPublication.candidate, mergeCommit: previousPublication.candidate.mergeCommit})
        : provider.landCandidateSync({repository: root, candidate: previousPublication.candidate});
      return {...previousPublication, ok: true, phase: 'landed', candidate, obstructions: []};
    } catch (error) {
      return {...previousPublication, ok: false, phase: error.code === 'CANDIDATE_RECEIVING_UNRESOLVED' ? 'receiving' : 'effect', candidate: error.sourceCandidate ?? previousPublication.candidate, obstructions: [String(error.message).slice(0,4096)]};
    }
  }
  return provider.publishGitPaths({packageRoot: root}, request);
}

/** Completed publication can be reobserved without granting another source effect. */
export function hasReceivedTrackedLegacyPublication(value) {
  const receiving = value?.candidate?.receiving;
  return value?.ok === true && value.phase === 'landed' && receiving?.state === 'received'
    && receiving.completeTransformation === true && receiving.allUnselectedPreserved === true;
}

function retirementRecordFiles(root, paths, optionalPath) {
  return paths.map(path => {
    const file = confined(root, path);
    let current;
    try { current = bytesAndMode(root, file); }
    catch (error) { if (error.code === 'ENOENT' && file === optionalPath) return null; throw error; }
    if (current.mode === '120000') throw new TypeError('retirement records must be regular files');
    const blob = String(execFileSync('git', ['-C', root, 'hash-object', '--stdin'], {input:current.bytes, maxBuffer:1024, stdio:['pipe','pipe','pipe']})).trim();
    return {path, mode:current.mode, sha256:digest(current.bytes), blob};
  }).filter(Boolean);
}

/** Validate the caller's record custody and canonical maker request before any
 * retirement effect. The result may be absent only on the first invocation. */
export async function prepareTrackedLegacyRecordPublication({request, planPath, planBytes, resultPath, receiptPath, previousPublication}) {
  if (typeof request?.repositoryRoot !== 'string') throw new TypeError('record publication requires its actual repositoryRoot');
  const root = resolve(request.repositoryRoot);
  const actualRoot = git(root, ['rev-parse', '--show-toplevel']).toString().trim();
  if (actualRoot !== root && (!hasReceivedTrackedLegacyPublication(previousPublication)
      || realpathSync(root) !== realpathSync(actualRoot))) throw new TypeError('record repositoryRoot must be its actual Git root');
  const {readGitCommitPathsRequest} = await import('@red-cup-engineering/git-source-reading-service/git-command-codec');
  const input = readGitCommitPathsRequest(request);
  if (!input.push || input.dryRun || !input.reviewedSource) throw new TypeError('record publication requires a reviewed source publication request');
  const absolute = input.paths.map(path => {
    if (path.split('/').includes('legacy')) throw new TypeError('retirement records cannot be published into legacy');
    return confined(root, path);
  });
  if (resolve(planPath) === resolve(resultPath)) throw new TypeError('retirement plan and result must be separate files');
  if (!absolute.includes(resolve(planPath)) || !absolute.includes(resolve(resultPath))) throw new TypeError('record publication must include its exact plan and result');
  if (absolute.includes(resolve(receiptPath)) || resolve(receiptPath) === resolve(resultPath)) throw new TypeError('record publication receipt must remain outside its publication cut');
  noLinkedParents(root, resolve(receiptPath));
  const present = file => {
    try { return lstatSync(file); }
    catch (error) { if (error.code === 'ENOENT') return null; throw error; }
  };
  const receipt = present(resolve(receiptPath)), result = present(resolve(resultPath));
  if (receipt && !receipt.isFile()) throw new TypeError('record publication receipt must be a regular file');
  const sameFile = (a,b) => a && b && a.dev === b.dev && a.ino === b.ino;
  if (absolute.some(file => sameFile(receipt,present(file)) ||
      (file !== resolve(resultPath) && sameFile(result,present(file))))) throw new TypeError('record publication destinations must not alias selected records');
  const files = retirementRecordFiles(root, input.paths, previousPublication ? undefined : resolve(resultPath));
  const inputFiles = files.filter(file => confined(root, file.path) !== resolve(resultPath));
  if (!planBytes || inputFiles.find(file => confined(root, file.path) === resolve(planPath))?.sha256 !== digest(planBytes)) throw new TypeError('record plan bytes differ from the plan being retired');
  if (previousPublication !== undefined && (!previousPublication || previousPublication.root !== root ||
      JSON.stringify(previousPublication.paths) !== JSON.stringify(input.paths) ||
      JSON.stringify(previousPublication.recordFiles) !== JSON.stringify(files))) throw new TypeError('retained record publication owner, paths or bytes differ');
  return {root, request:input, inputFiles, replay:previousPublication !== undefined};
}

/** Compose record publication with the same maker used for the retirement.
 * save retains custody before effects; the result being published stays fixed. */
export async function publishTrackedLegacyRecords({publication, previousPublication, maker, save}) {
  if (typeof save !== 'function') throw new TypeError('record publication requires a durable receipt writer');
  const {root, request} = publication;
  const recordFiles = retirementRecordFiles(root, request.paths);
  if (publication.inputFiles.some(expected => JSON.stringify(recordFiles.find(file => file.path === expected.path)) !== JSON.stringify(expected))) throw new TypeError('retirement input records changed before publication');
  if (previousPublication && JSON.stringify(previousPublication.recordFiles) !== JSON.stringify(recordFiles)) throw new TypeError('retirement records changed before publication replay');
  const readOnly = hasReceivedTrackedLegacyPublication(previousPublication);
  const prepared = {...previousPublication, kind:'metroplat.git.commit-paths', ok:false, phase:'prepared', root, paths:request.paths, recordFiles};
  if (!readOnly) save(prepared);
  let received;
  try {
    received = {...await publishRetirementPaths({root, request, previousPublication, maker}), recordFiles};
    if (received.ok && received.candidate?.receiving) {
      for (const entry of received.candidate.receiving.entries) {
        const original = recordFiles.find(file => file.path === entry.path);
        if (!original || entry.after?.type !== 'blob' || entry.after.mode !== original.mode || entry.after.object !== original.blob) {
          received = {...received, ok:false, phase:'receiving', obstructions:['published records differ from the retained file identities']};
          break;
        }
      }
    }
  } catch (error) {
    received = {...prepared, phase:'effect', obstructions:[String(error.message).slice(0,4096)]};
  }
  // A transient failed observation does not invalidate the immutable effect or
  // erase the completed custody needed for the next read-only replay.
  if (!readOnly) save(received);
  return received;
}
