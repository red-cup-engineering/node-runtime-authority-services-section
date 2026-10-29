#!/usr/bin/env node
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { assess, packet, sourceImpact, proposeObservation, renderAssessment, renderPacket } from '../src/identity-access.mjs';
import { initializeCase } from '../src/initialize-case.mjs';
import { auditEvidence } from '../src/evidence-audit.mjs';

const json = async path => JSON.parse(await readFile(path, 'utf8'));
export async function loadInput({ casePath, modelPath, sourcesPath, evidenceManifestPath, asOf, assume = [] }) {
  const [caseRecord, model, sourceRegistry] = await Promise.all([json(casePath), json(modelPath), json(sourcesPath)]);
  for (const source of sourceRegistry.sources) if (source.artifact) {
    try {
      const bytes = await readFile(resolve(dirname(sourcesPath), source.artifact));
      const hash = createHash('sha256').update(bytes).digest('hex');
      source.integrity = hash === source.sha256 ? 'verified' : 'failed';
    } catch { source.integrity = 'failed'; }
  }
  const evidenceAudit = evidenceManifestPath ? await auditEvidence({ manifestPath: evidenceManifestPath, caseId: caseRecord.caseId, asOf }) : null;
  return { caseRecord, model, sourceRegistry, evidenceAudit, asOf, assume };
}

export async function main(args) {
  const [command, ...rest] = args;
  const values = new Map();
  for (let i = 0; i < rest.length; i += 2) {
    if (!rest[i].startsWith('--') || !rest[i + 1] || rest[i + 1].startsWith('--') || values.has(rest[i])) throw new TypeError('Expected unique --option value pairs');
    values.set(rest[i], rest[i + 1]);
  }
  const allowed = ['--service', '--case', '--model', '--sources', '--as-of', '--format', '--assume', '--before', '--after', '--evidence', '--template', '--destination', '--case-id', '--evidence-manifest'];
  for (const key of values.keys()) if (!allowed.includes(key)) throw new TypeError('Unknown option: ' + key);
  if (command === 'init') {
    if (Array.from(values.keys()).some(key => !['--template', '--destination', '--case-id', '--as-of'].includes(key))) throw new TypeError('init accepts only template, destination, case-id and as-of');
    const required = key => { if (!values.has(key)) throw new TypeError('Required: ' + key); return values.get(key); };
    return JSON.stringify(initializeCase({ templatePath: required('--template'), destination: required('--destination'), caseId: required('--case-id'), asOf: required('--as-of') }), null, 2) + '\n';
  }
  if (['--template', '--destination', '--case-id'].some(key => values.has(key))) throw new TypeError('Case-opening options require the init command');
  if (values.has('--service')) {
    if (['--case', '--model', '--sources', '--before', '--after'].some(key => values.has(key))) throw new TypeError('Use service parameters or explicit input paths, not both');
    const parameterPath = resolve(values.get('--service'));
    const parameters = await json(parameterPath);
    if (parameters.kind !== 'identity-document-access-service' || parameters.version !== 1) throw new TypeError('Unknown service parameter contract');
    for (const [key, field] of [['--case', 'casePath'], ['--model', 'modelPath'], ['--sources', 'sourcesPath']]) {
      if (typeof parameters[field] !== 'string' || !parameters[field]) throw new TypeError('Missing service parameter: ' + field);
      values.set(key, resolve(dirname(parameterPath), parameters[field]));
    }
    if (parameters.evidenceManifestPath !== undefined) {
      if (typeof parameters.evidenceManifestPath !== 'string' || !parameters.evidenceManifestPath || values.has('--evidence-manifest')) throw new TypeError('Evidence manifest must be bound once in service parameters');
      values.set('--evidence-manifest', resolve(dirname(parameterPath), parameters.evidenceManifestPath));
    }
  }
  const required = name => { if (!values.has(name)) throw new TypeError('Required: ' + name); return values.get(name); };
  if (!['assess', 'packet', 'scenario', 'source-impact', 'observe', 'audit-evidence'].includes(command)) throw new TypeError('Commands: init, assess, packet, scenario, source-impact, observe, audit-evidence. See README.md for arguments.');
  const format = values.get('--format') ?? 'json';
  if (!['json', 'markdown'].includes(format)) throw new TypeError('Format must be json or markdown');
  if (command === 'audit-evidence') {
    if (format !== 'json') throw new TypeError('audit-evidence emits JSON without artifact paths or contents');
    const caseRecord = await json(required('--case'));
    return JSON.stringify(await auditEvidence({ manifestPath: required('--evidence-manifest'), caseId: caseRecord.caseId, asOf: required('--as-of') }), null, 2) + '\n';
  }
  if (command === 'source-impact') {
    if (format !== 'json') throw new TypeError('source-impact emits JSON');
    const report = sourceImpact({ model: await json(required('--model')), before: await json(required('--before')), after: await json(required('--after')) });
    return JSON.stringify(report, null, 2) + '\n';
  }
  if (values.has('--assume') && command !== 'scenario') throw new TypeError('Assumptions require the scenario command');
  const input = await loadInput({ casePath: required('--case'), modelPath: required('--model'), sourcesPath: required('--sources'), evidenceManifestPath: values.get('--evidence-manifest'), asOf: required('--as-of'),
    assume: command === 'scenario' ? required('--assume').split(',').filter(Boolean) : [] });
  if (command === 'scenario' && !input.assume.length) throw new TypeError('Scenario needs at least one explicit node assumption');
  if (command === 'observe') {
    if (format !== 'json') throw new TypeError('observe emits a JSON proposal; it never writes the case');
    return JSON.stringify(proposeObservation(input, await json(required('--evidence'))), null, 2) + '\n';
  }
  const report = command === 'packet' ? packet(input) : assess(input);
  return format === 'json' ? JSON.stringify(report, null, 2) + '\n' : command === 'packet' ? renderPacket(report) : renderAssessment(report);
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try { process.stdout.write(await main(process.argv.slice(2))); }
  catch (error) { process.stderr.write(error.message + '\n'); process.exitCode = 2; }
}
