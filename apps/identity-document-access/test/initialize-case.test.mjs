import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, statSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { initializeCase } from '../src/initialize-case.mjs';
import { main } from '../bin/identity-access.mjs';

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'identity-case-opening-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const pack = join(root, 'pack'); mkdirSync(pack);
  const files = { case: 'case.json', model: 'model.json', sources: 'sources.json', parameters: 'service.json' };
  const records = {
    case: { recordType: 'personal-government-photo-id-case', caseId: '__CASE_ID__', recipient: '__CLIENT_LABEL__', updatedOn: '__AS_OF__', facts: [], attempts: [], routes: [] },
    model: { version: 1, caseId: '__CASE_ID__', caseRecordType: 'personal-government-photo-id-case', jurisdiction: 'Unselected', goals: ['id-received'], nodes: [{ id: 'id-received', label: 'Physical credential received', kind: 'receipt', observations: [], receiptContract: { receiver: 'unselected-issuer', outcome: 'physical-id-received' } }], claims: [], steps: [], obligations: [], research: [] },
    sources: { sources: [] },
    parameters: { kind: 'identity-document-access-service', version: 1, casePath: files.case, modelPath: files.model, sourcesPath: files.sources }
  };
  const templatePath = join(pack, 'template.json');
  const save = () => {
    writeFileSync(templatePath, JSON.stringify({ kind: 'identity-case-template', version: 1, files }));
    for (const [role, name] of Object.entries(files)) writeFileSync(join(pack, name), JSON.stringify(records[role]));
  };
  save();
  return { root, pack, files, records, save, templatePath, options: { templatePath, destination: join(root, 'client-alpha'), caseId: 'client-alpha', asOf: '2026-10-26' } };
}

test('opens two private isolated clients and the actual CLI can assess each without creating evidence', async t => {
  const f = fixture(t);
  const first = initializeCase(f.options);
  const second = initializeCase({ ...f.options, destination: join(f.root, 'client-bravo'), caseId: 'client-bravo' });
  for (const r of [first, second]) {
    assert.equal(statSync(r.directory).mode & 0o777, 0o700);
    for (const file of r.files) assert.equal(statSync(file).mode & 0o777, 0o600);
    const c = JSON.parse(readFileSync(join(r.directory, 'case.json')));
    assert.equal(c.caseId, r.caseId); assert.deepEqual(c.facts, []);
    const report = JSON.parse(await main(['assess', '--service', r.parameterPath, '--as-of', '2026-10-26']));
    assert.equal(report.goals[0].reading, 'unknown');
  }
  assert.equal(JSON.parse(readFileSync(join(f.pack, 'case.json'))).caseId, '__CASE_ID__');
  assert.notEqual(readFileSync(join(first.directory, 'case.json'), 'utf8'), readFileSync(join(second.directory, 'case.json'), 'utf8'));
});

test('refuses an existing destination and preserves its content', t => {
  const f = fixture(t); mkdirSync(f.options.destination); const old = join(f.options.destination, 'case.json'); writeFileSync(old, 'previous client');
  assert.throws(() => initializeCase(f.options), { code: 'EEXIST' }); assert.equal(readFileSync(old, 'utf8'), 'previous client');
});

test('refuses destination symlinks, traversal and aliased template roles', t => {
  const f = fixture(t); symlinkSync(f.pack, f.options.destination); assert.throws(() => initializeCase(f.options), { code: 'EEXIST' });
  f.files.case = '../outside.json'; f.save(); assert.throws(() => initializeCase({ ...f.options, destination: join(f.root, 'other') }), /Invalid case template/);
  f.files.case = 'model.json'; f.save(); assert.throws(() => initializeCase({ ...f.options, destination: join(f.root, 'other') }), /distinct/);
});

test('refuses a source symlink before creating any case', t => {
  const f = fixture(t); rmSync(join(f.pack, 'sources.json')); symlinkSync(join(f.pack, 'case.json'), join(f.pack, 'sources.json'));
  assert.throws(() => initializeCase(f.options), /regular files/);
  assert.throws(() => statSync(f.options.destination), { code: 'ENOENT' });
});

test('refuses cloning a populated or bound client and mismatched service inputs', t => {
  const f = fixture(t);
  for (const edit of [() => { f.records.case.facts = [{ claim: 'previous client' }]; }, () => { f.records.case.facts = []; f.records.model.nodes[0].observations = [{ side: 'for', basis: 'case-report', casePointer: '/facts/0' }]; }, () => { f.records.model.nodes[0].observations = []; f.records.case.caseId = 'another-client'; }, () => { f.records.case.caseId = '__CASE_ID__'; f.records.parameters.casePath = 'other.json'; }]) {
    edit(); f.save(); assert.throws(() => initializeCase(f.options)); assert.throws(() => statSync(f.options.destination), { code: 'ENOENT' });
  }
});

test('invalid date, identifying-number-like case ID and invalid model fail before writes', t => {
  const f = fixture(t);
  assert.throws(() => initializeCase({ ...f.options, asOf: '2026-02-30' }));
  assert.throws(() => initializeCase({ ...f.options, caseId: '123456789' }), /opaque case ID/);
  f.records.model.goals = ['missing']; f.save(); assert.throws(() => initializeCase(f.options), /Unknown node/);
  assert.throws(() => statSync(f.options.destination), { code: 'ENOENT' });
});

test('refuses inherited client identity, record inventory, route selection or consent', t => {
  const f = fixture(t);
  for (const [field, value] of [['recipient', 'Prior client name'], ['privateSourceIndex', [{ id: 'old-source' }]], ['routes', [{ id: 'prior-choice' }]], ['clientControl', { grants: [{ effect: 'contact' }] }], ['decision', { spendingAuthorized: true }]]) {
    const previous = f.records.case[field]; f.records.case[field] = value; f.save();
    assert.throws(() => initializeCase(f.options)); assert.throws(() => statSync(f.options.destination), { code: 'ENOENT' });
    if (previous === undefined) delete f.records.case[field]; else f.records.case[field] = previous;
  }
});
