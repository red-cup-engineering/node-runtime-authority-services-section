import {createHash} from 'node:crypto';
import {accessSync, constants, lstatSync, readFileSync, realpathSync, writeFileSync} from 'node:fs';
import {dirname, isAbsolute, relative, resolve, sep} from 'node:path';
import {execFileSync} from 'node:child_process';
import {readTrackedLegacyRetirementPlan, hasReceivedTrackedLegacyPublication} from './tracked-legacy-retirement.mjs';
import {prepareTrackedLegacyRecordSource} from './tracked-legacy-source-publication.mjs';

const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const textBytes = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');
const fail = message => { throw new TypeError('retirement batch: ' + message); };
const pathOk = value => typeof value === 'string' && value.length > 0 && !isAbsolute(value) && !value.includes('\0') && !value.split('/').some(part => !part || part === '.' || part === '..');
const ownPath = (root, path) => {
  if (!pathOk(path)) fail('exact owner-relative path required');
  return resolve(root, path);
};
const jsonRecord = (path, bytes) => {
  if (!Buffer.isBuffer(bytes) || bytes.length > 1_048_576) fail('bounded input bytes required');
  const text = bytes.toString('utf8');
  if (!Buffer.from(text).equals(bytes)) fail('input must be exact UTF-8');
  const value = JSON.parse(text);
  return {path, sha256: hash(bytes), text, value};
};

/** Assemble declared judgments only. No filesystem, Git, source effects or invented review. */
export function composeTrackedLegacyRetirementBatch({id, repositoryRoot, receivingPath, plans, supportingRecords = []}) {
  if (typeof id !== 'string' || !id.trim() || id.length > 256) fail('bounded batch id required');
  if (typeof repositoryRoot !== 'string' || !isAbsolute(repositoryRoot) || resolve(repositoryRoot) !== repositoryRoot) fail('actual normalized record owner required');
  ownPath(repositoryRoot, receivingPath);
  if (!Array.isArray(plans) || !plans.length || plans.length > 32 || !Array.isArray(supportingRecords) || supportingRecords.length > 64) fail('bounded explicit plans and supporting records required');
  const inputs = [...plans, ...supportingRecords], named = new Set();
  let totalBytes = 0;
  for (const input of inputs) {
    ownPath(repositoryRoot, input.path);
    if (input.path.split('/').includes('legacy') || named.has(input.path)) fail('input must be unique and outside legacy');
    named.add(input.path);
    totalBytes += input.bytes?.length ?? 0;
  }
  if (totalBytes > 1_048_576) fail('combined input exceeds one MiB');
  if (named.has(receivingPath)) fail('snapshot output aliases an input');
  const originals = plans.map(input => jsonRecord(input.path, input.bytes));
  const records = supportingRecords.map(input => jsonRecord(input.path, input.bytes));
  const support = new Map(records.map(row => [ownPath(repositoryRoot,row.path), row]));
  const supportingWitness = (evidence, sourceRoot) => {
    const owner = evidence.repositoryRoot ?? sourceRoot;
    if (typeof owner !== 'string' || !isAbsolute(owner) || resolve(owner) !== owner) fail('normalized evidence owner required');
    return support.get(ownPath(owner,evidence.path));
  };
  const combined = [];
  let common;
  for (const original of originals) {
    const plan = readTrackedLegacyRetirementPlan(original.value);
    if (typeof plan.repositoryRoot !== 'string' || !isAbsolute(plan.repositoryRoot) || resolve(plan.repositoryRoot) !== plan.repositoryRoot
        || !pathOk(plan.legacyRoot) || !plan.legacyRoot.split('/').includes('legacy')
        || !/^(?:[a-f0-9]{40}|[a-f0-9]{64})$/u.test(plan.revision ?? '')) fail('immutable normalized source cut required');
    const cut = [plan.repositoryRoot, plan.legacyRoot, plan.revision, plan.workingLegacyRoot, plan.sourceLegacyRoot];
    if (common && JSON.stringify(common) !== JSON.stringify(cut)) fail('plans name different source cuts');
    common = cut;
    for (const cap of plan.capabilities) {
      const copy = structuredClone(cap);
      for (const evidence of copy.evidence ?? []) {
        const record = supportingWitness(evidence,plan.repositoryRoot);
        if (record) {
          if (!/^[a-f0-9]{64}$/u.test(evidence.sha256 ?? '') || evidence.sha256 !== record.sha256) fail('supporting evidence changed or lacks its reviewed digest: ' + evidence.path);
        }
      }
      combined.push(copy);
    }
  }
  const plan = {kind:'legacy-capability-retirement-plan/v1', repositoryRoot:common[0], legacyRoot:common[1], revision:common[2],
    ...(common[3] === undefined ? {} : {workingLegacyRoot:common[3]}),
    ...(common[4] === undefined ? {} : {sourceLegacyRoot:common[4]}), capabilities:combined};
  // Reuse the ordinary declaration contract, including overlap and deprecation checks.
  readTrackedLegacyRetirementPlan(plan);
  const receiving = {kind:'legacy-capability-retirement-batch-receiving/v1', id,
    source:{repositoryRoot:common[0], legacyRoot:common[1], revision:common[2], ...(common[3] === undefined ? {} : {workingLegacyRoot:common[3]}),
      ...(common[4] === undefined ? {} : {sourceLegacyRoot:common[4]})},
    claim:'Mechanical assembly of supplied judgments; no new capability, authority, installation or independent-review assertion.',
    plans:originals.map(({value, ...raw}) => raw),
    supportingRecords:records.map(({value, ...raw}) => raw)};
  const receivingBytes = textBytes(receiving);
  if (receivingBytes.length > 2_097_152) fail('receiving snapshot exceeds two MiB');
  const witness = {repositoryRoot, path:receivingPath, sha256:hash(receivingBytes)};
  for (const cap of plan.capabilities) {
    const evidence = [], seen = new Set();
    for (const original of cap.evidence ?? []) {
      const replacement = supportingWitness(original,plan.repositoryRoot) ? witness : original;
      const key = JSON.stringify(replacement);
      if (!seen.has(key)) { evidence.push(replacement); seen.add(key); }
    }
    if (cap.evidence) cap.evidence = evidence;
  }
  return {plan, receiving, planBytes:textBytes(plan), receivingBytes};
}

const stat = file => {
  try { return lstatSync(file); } catch (error) { if (error.code === 'ENOENT') return null; throw error; }
};
const regular = (root, file, optional = false) => {
  let at = root;
  for (const part of relative(root, dirname(file)).split(sep).filter(Boolean)) {
    at = resolve(at, part);
    const entry = stat(at);
    if (!entry?.isDirectory() || entry.isSymbolicLink()) fail('missing or linked output/input ancestor');
  }
  const entry = stat(file);
  if (!entry && optional) return null;
  if (!entry?.isFile() || entry.isSymbolicLink()) fail('named input/output must be a regular file');
  return entry;
};

/** Prepare only named records, then let the existing CLI own preview/apply/publication. */
export async function prepareTrackedLegacyRetirementBatch({batch, batchPath}) {
  const allowed = ['kind','id','repositoryRoot','plans','supportingRecords','outputs','publication'];
  if (batch?.kind !== 'legacy-capability-retirement-batch/v1' || Object.keys(batch).some(key => !allowed.includes(key))) fail('declared batch input required');
  const root = batch.repositoryRoot;
  if (typeof root !== 'string' || !isAbsolute(root) || resolve(root) !== root) fail('record owner must be its actual Git root');
  const actualRoot = String(execFileSync('git',['-C',root,'rev-parse','--show-toplevel'],{stdio:['ignore','pipe','pipe']})).trim();
  const aliasReplay = actualRoot !== root;
  if (aliasReplay && realpathSync(root) !== realpathSync(actualRoot)) fail('record owner must be its actual Git root');
  const outputs = batch.outputs, keys = ['plan','receiving','result','publicationRequest','publicationReceipt'];
  if (!outputs || Object.keys(outputs).length !== keys.length || keys.some(key => !pathOk(outputs[key]))) fail('exact five output paths required');
  if (!Array.isArray(batch.plans) || !batch.plans.length || batch.plans.length > 32 || !Array.isArray(batch.supportingRecords ?? []) || (batch.supportingRecords ?? []).length > 64) fail('bounded explicit input lists required');
  const targets = keys.map(key => ownPath(root, outputs[key]));
  const inputPaths = [...batch.plans, ...(batch.supportingRecords ?? [])].map(path => ownPath(root, path));
  const all = [...targets, ...inputPaths, resolve(batchPath)];
  if (new Set(all).size !== all.length || targets.some(file => relative(root,file).split(sep).includes('legacy'))) fail('output paths alias an input or each other');
  const identities = [];
  for (const file of all) {
    // The batch manifest itself is explicit input and must also belong to this owner.
    if (relative(root,file).split(sep)[0] === '..') fail('batch input escapes record owner');
    const entry = regular(root,file,targets.includes(file));
    if (entry) {
      if (entry.size > 2_097_152) fail('named file exceeds two MiB');
      const key = String(entry.dev) + ':' + String(entry.ino);
      if (identities.includes(key)) fail('input/output inode alias');
      identities.push(key);
    }
  }
  for (const file of targets) accessSync(dirname(file),constants.W_OK);
  if (aliasReplay) {
    // A physical-root rename may leave the old explicit address as a symlink.
    // Only complete retained custody may use it; fresh work uses the actual root.
    if (targets.some(file => !stat(file))) fail('root alias requires complete retained publication');
    const retained = JSON.parse(readFileSync(targets[2],'utf8'));
    const records = JSON.parse(readFileSync(targets[4],'utf8'));
    if (!hasReceivedTrackedLegacyPublication(retained.publication)
        || !['committed','already-landed'].includes(retained.landing?.state)
        || !hasReceivedTrackedLegacyPublication(records) || records.root !== root) fail('root alias requires complete retained publication');
  }
  const read = path => ({path, bytes:readFileSync(ownPath(root,path))});
  const result = composeTrackedLegacyRetirementBatch({id:batch.id, repositoryRoot:root, receivingPath:outputs.receiving,
    plans:batch.plans.map(read), supportingRecords:(batch.supportingRecords ?? []).map(read)});
  const {readGitCommitPathsRequest} = await import('@red-cup-engineering/git-source-reading-service/git-command-codec');
  const publication = batch.publication;
  if (!publication || Object.keys(publication).some(key => !['message','candidate','reviewedSource'].includes(key))) fail('explicit existing-maker publication declaration required');
  const paths = [outputs.plan,outputs.receiving,outputs.result];
  // The generated request retains the original lease across every replay.
  let reviewedSource = publication.reviewedSource;
  if (reviewedSource === undefined) {
    reviewedSource = stat(targets[3])
      ? JSON.parse(readFileSync(targets[3],'utf8')).reviewedSource
      : await prepareTrackedLegacyRecordSource({repositoryRoot:root,paths});
    if (reviewedSource === undefined) fail('retained publication request lacks its original preimages');
  }
  const request = {repositoryRoot:root, paths, message:publication.message, push:true,
    ...(publication.candidate === undefined ? {} : {candidate:publication.candidate}), reviewedSource};
  const decoded = readGitCommitPathsRequest(request);
  if (!decoded.reviewedSource || !decoded.push) fail('reviewed publication preimages required');
  const generated = [[targets[0],result.planBytes],[targets[1],result.receivingBytes],[targets[3],textBytes(request)]];
  // Inspect every destination before the first generated-file write.
  for (const [file,bytes] of generated) {
    if (stat(file) && !readFileSync(file).equals(bytes)) fail('existing prepared bytes changed: ' + relative(root,file));
  }
  for (const [file,bytes] of generated) {
    if (!stat(file)) writeFileSync(file,bytes,{flag:'wx',mode:0o600});
  }
  return {planPath:targets[0], resultPath:targets[2], recordsRequest:targets[3], recordsOutput:targets[4],
    plan:result.plan, planBytes:result.planBytes};
}

