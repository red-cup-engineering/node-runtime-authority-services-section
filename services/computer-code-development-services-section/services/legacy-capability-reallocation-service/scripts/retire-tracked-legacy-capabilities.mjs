#!/usr/bin/env node
import {accessSync, constants, readFileSync, lstatSync, writeFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {retireTrackedLegacyCapabilities, commitTrackedLegacyRetirement, publishTrackedLegacyRetirement, prepareTrackedLegacyRecordPublication, publishTrackedLegacyRecords} from '../src/tracked-legacy-retirement.mjs';
import {prepareTrackedLegacyRetirementBatch} from '../src/tracked-legacy-batch.mjs';
import {prepareTrackedLegacySourcePublication} from '../src/tracked-legacy-source-publication.mjs';

let [path, ...args] = process.argv.slice(2);
if (!path || args.some(x => !['--apply','--publish'].includes(x) && !['--output=','--publish-records=','--records-output='].some(prefix => x.startsWith(prefix)))) throw new TypeError('usage: retire-tracked-legacy-capabilities PLAN.json [--apply [--publish]] [--output=RESULT.json] [--publish-records=REQUEST.json --records-output=RECEIPT.json]');
let output = args.find(x => x.startsWith('--output='))?.slice('--output='.length);
let recordsRequest = args.find(x => x.startsWith('--publish-records='))?.slice('--publish-records='.length);
let recordsOutput = args.find(x => x.startsWith('--records-output='))?.slice('--records-output='.length);
let planBytes = readFileSync(path);
let plan = JSON.parse(planBytes.toString('utf8'));
if (plan.kind === 'legacy-capability-retirement-batch/v1') {
  if (output || recordsRequest || recordsOutput) throw new TypeError('batch outputs belong to its declared custody; do not mix output flags');
  if (args.includes('--publish') && !args.includes('--apply')) throw new TypeError('--publish requires --apply');
  const batch = await prepareTrackedLegacyRetirementBatch({batch:plan,batchPath:path});
  path = batch.planPath; output = batch.resultPath; plan = batch.plan; planBytes = batch.planBytes;
  if (args.includes('--publish')) { recordsRequest = batch.recordsRequest; recordsOutput = batch.recordsOutput; }
}
if (args.includes('--publish') && (!args.includes('--apply') || !output)) throw new TypeError('--publish requires --apply and a durable --output receipt');
if ((recordsRequest || recordsOutput) && (!recordsRequest || !recordsOutput || !args.includes('--publish'))) throw new TypeError('record publication requires --publish, --publish-records and a separate --records-output');
if (recordsRequest && [resolve(output),resolve(recordsOutput)].includes(resolve(recordsRequest))) throw new TypeError('record request and receipt destinations must be separate files');
let prior;
// Refuse a known unusable receipt destination before unlinking or committing.
if (output) {
  accessSync(dirname(resolve(output)), constants.W_OK);
  try {
    if (!lstatSync(output).isFile()) throw new TypeError('retirement result output must be a file');
    accessSync(output, constants.W_OK);
    if (lstatSync(output).size > 2 * 1024 * 1024) throw new TypeError('retirement receipt exceeds its bounded size');
    prior = JSON.parse(readFileSync(output, 'utf8'));
    if (prior.repositoryRoot !== resolve(plan.repositoryRoot) || prior.legacyRoot !== plan.legacyRoot || prior.revision !== plan.revision
        || prior.workingLegacyRoot !== plan.workingLegacyRoot || prior.sourceLegacyRoot !== plan.sourceLegacyRoot) throw new TypeError('retained receipt belongs to another retirement');
    if (prior.publication !== undefined && !args.includes('--publish')) throw new TypeError('retained source publication requires --apply --publish replay; its receipt cannot be replaced by preview or local apply');
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
}
let records, priorRecords;
if (recordsRequest) {
  accessSync(dirname(resolve(recordsOutput)), constants.W_OK);
  try {
    if (!lstatSync(recordsOutput).isFile() || lstatSync(recordsOutput).size > 2 * 1024 * 1024) throw new TypeError('record publication receipt must be a bounded regular file');
    accessSync(recordsOutput, constants.W_OK);
    priorRecords = JSON.parse(readFileSync(recordsOutput, 'utf8'));
  } catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (!lstatSync(recordsRequest).isFile() || lstatSync(recordsRequest).size > 2 * 1024 * 1024) throw new TypeError('record publication request must be a bounded regular file');
  records = await prepareTrackedLegacyRecordPublication({request:JSON.parse(readFileSync(recordsRequest,'utf8')), planPath:path, planBytes, resultPath:output, receiptPath:recordsOutput, previousPublication:priorRecords});
  if (records.replay && (!prior?.publication?.ok || !['committed','already-landed'].includes(prior?.landing?.state))) throw new TypeError('record publication replay requires its completed retirement result');
}
const sourcePreparation = !records?.replay && args.includes('--publish')
  ? await prepareTrackedLegacySourcePublication({result:retireTrackedLegacyCapabilities({plan}), previousPublication:prior?.publication})
  : undefined;
const result = records?.replay ? prior : retireTrackedLegacyCapabilities({plan, apply: args.includes('--apply')});
if (result.apply && !records?.replay) {
  if (sourcePreparation ?? prior?.sourcePreparation) result.sourcePreparation = sourcePreparation ?? prior.sourcePreparation;
  try { result.landing = commitTrackedLegacyRetirement({result}); }
  catch (error) { result.landing = {state: 'uncommitted', error: error.message}; process.exitCode = 1; }
}
if (!records?.replay && args.includes('--publish') && ['committed','already-landed'].includes(result.landing?.state)) {
  // Preserve local custody before any external effect, then retain its result.
  writeFileSync(output, JSON.stringify({...result, ...(prior?.publication ? {publication: prior.publication} : {})}, null, 2) + '\n');
  try { result.publication = await publishTrackedLegacyRetirement({result, previousPublication: prior?.publication}); }
  catch (error) { result.publication = {ok:false, phase:'precondition', obstructions:[String(error.message).slice(0,4096)]}; }
  if (!result.publication.ok) process.exitCode = 1;
}
if (output && !records?.replay) writeFileSync(output, JSON.stringify(result, null, 2) + '\n');
let recordsPublication;
if (records && result.publication?.ok) {
  recordsPublication = await publishTrackedLegacyRecords({publication:records, previousPublication:priorRecords, save:value=>writeFileSync(recordsOutput,JSON.stringify(value,null,2)+'\n')});
  if (!recordsPublication.ok) process.exitCode = 1;
}
const summary = output ? {kind: result.kind, revision: result.revision, legacyRoot: result.legacyRoot, apply: result.apply, selectedFiles: result.selectedFiles, counts: result.counts, landing: result.landing, ...(result.publication ? {publication:{ok:result.publication.ok,phase:result.publication.phase,mergeCommit:result.publication.candidate?.mergeCommit}} : {}), ...(recordsPublication ? {recordsPublication:{ok:recordsPublication.ok,phase:recordsPublication.phase,mergeCommit:recordsPublication.candidate?.mergeCommit,output:recordsOutput}} : {}), output} : {...result, outcomes: undefined};
process.stdout.write(JSON.stringify(summary, null, 2) + '\n');
if (result.counts.held || result.landing?.state === 'committed-with-recreated-files') process.exitCode = 1;
