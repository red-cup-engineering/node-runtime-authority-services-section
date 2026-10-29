import { chmodSync, lstatSync, mkdirSync, readFileSync, rmdirSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { validateJsonSchema } from '@red-cup-engineering/json-schema-services-section/validation';
import { assess } from './identity-access.mjs';

const schema = JSON.parse(readFileSync(new URL('../data/schemas/case-template.schema.json', import.meta.url)));
const readOrdinaryJson = path => {
  if (!lstatSync(path).isFile()) throw new TypeError('Template inputs must be regular files, without symlinks');
  return JSON.parse(readFileSync(path, 'utf8'));
};
function bind(value, fields) {
  if (typeof value === 'string') return Object.hasOwn(fields, value) ? fields[value] : value;
  if (Array.isArray(value)) return value.map(item => bind(item, fields));
  if (value !== null && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, bind(item, fields)]));
  return value;
}

export function initializeCase({ templatePath, destination, caseId, asOf }) {
  if (typeof caseId !== 'string' || !/^[a-z][a-z0-9-]{2,95}$/.test(caseId)) throw new TypeError('Use an opaque case ID beginning with a lowercase letter; do not use an identifying number');
  if (typeof destination !== 'string' || !destination) throw new TypeError('An explicit new private destination is required');
  const source = resolve(templatePath);
  const manifest = readOrdinaryJson(source);
  const admitted = validateJsonSchema(manifest, schema);
  if (!admitted.valid) throw new TypeError('Invalid case template manifest');
  const names = Object.values(manifest.files);
  if (new Set(names).size !== 4) throw new TypeError('Template filenames must be distinct');
  const records = Object.fromEntries(Object.entries(manifest.files).map(([role, name]) => [role, readOrdinaryJson(resolve(dirname(source), name))]));
  if (records.case.caseId !== '__CASE_ID__' || records.model.caseId !== '__CASE_ID__') throw new TypeError('Template must be unbound to any existing client');
  if (records.case.recipient !== '__CLIENT_LABEL__') throw new TypeError('A blank template must not carry an existing client name');
  if (!Array.isArray(records.case.facts) || records.case.facts.length || !Array.isArray(records.case.attempts) || records.case.attempts.length) throw new TypeError('A new case template cannot contain existing facts or attempts');
  for (const field of ['routes', 'privateSourceIndex', 'recoveryInventory', 'intendedUses']) {
    if (records.case[field] !== undefined && (!Array.isArray(records.case[field]) || records.case[field].length)) throw new TypeError('A blank template cannot carry prior client state: ' + field);
  }
  const control = records.case.clientControl;
  if (control && (control.relationshipAccepted === true || (control.grants !== undefined && (!Array.isArray(control.grants) || control.grants.length)))) throw new TypeError('A blank template cannot carry client consent');
  if (records.case.decision?.filingAuthorized === true || records.case.decision?.spendingAuthorized === true) throw new TypeError('A blank template cannot carry filing or spending authority');
  if (!Array.isArray(records.model.nodes) || records.model.nodes.some(node => !Array.isArray(node.observations) || node.observations.length)) throw new TypeError('A new case template cannot contain evidence observations');
  const parameters = records.parameters;
  if (parameters.kind !== 'identity-document-access-service' || parameters.version !== 1 || parameters.casePath !== manifest.files.case || parameters.modelPath !== manifest.files.model || parameters.sourcesPath !== manifest.files.sources) throw new TypeError('Template service parameters must bind exactly these records');
  const bound = bind(records, { __CASE_ID__: caseId, __AS_OF__: asOf, __CLIENT_LABEL__: 'Client chosen label' });
  const assessment = assess({ caseRecord: bound.case, model: bound.model, sourceRegistry: bound.sources, asOf });
  const directory = resolve(destination);
  mkdirSync(directory, { mode: 0o700 });
  const created = [];
  try {
    chmodSync(directory, 0o700);
    for (const [role, name] of Object.entries(manifest.files)) {
      const path = resolve(directory, name);
      writeFileSync(path, JSON.stringify(bound[role], null, 2) + '\n', { flag: 'wx', mode: 0o600 });
      created.push(path);
      chmodSync(path, 0o600);
    }
  } catch (error) {
    for (const path of created.reverse()) { try { unlinkSync(path); } catch {} }
    try { rmdirSync(directory); } catch {}
    throw error;
  }
  return { kind: 'identity-case-initialized', caseId, directory, parameterPath: resolve(directory, manifest.files.parameters), files: created, goals: assessment.goals, authority: 'none granted by initialization' };
}
