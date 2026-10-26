import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { assess, packet, sourceImpact, proposeObservation, renderAssessment } from '../src/identity-access.mjs';
import { loadInput, main } from '../bin/identity-access.mjs';

function fixture() {
  return {
    asOf: '2026-10-26',
    caseRecord: { caseId: 'synthetic-case-a', recordType: 'test-case', recipient: 'Synthetic client A', routes: [{ id: 'local', state: 'assessing' }], facts: [{ claim: 'Signed request is available' }], attempts: [{ date: '2026-10-20', receiver: 'Agency', outcome: 'draft-created', receiptRef: null }] },
    sourceRegistry: { sources: [{ id: 'law', title: 'Synthetic law fixture', url: 'https://example.org/law', retrievedOn: '2026-10-26', reviewAfterDays: 30, status: 'current' }] },
    model: { version: 1, caseId: 'synthetic-case-a', caseRecordType: 'test-case', jurisdiction: 'Synthetic test jurisdiction', goals: ['id-received'],
      claims: [{ id: 'waiver', proposition: 'waiver-exists', sourceId: 'law', locator: 'test §1', text: 'Synthetic waiver procedure exists.', side: 'for' }],
      nodes: [
        { id: 'signed', label: 'Signed request', kind: 'document', observations: [{ side: 'for', basis: 'case-report', casePointer: '/facts/0' }], provenance: 'Fixture only' },
        { id: 'birth', label: 'Birth record', kind: 'document', observations: [] },
        { id: 'old-id', label: 'Existing photo ID', kind: 'document', observations: [] },
        { id: 'id-received', label: 'ID received', kind: 'receipt', receiptContract: { outcome: 'photo-id-physically-received', receiver: 'Agency' }, observations: [] }
      ],
      steps: [
        { id: 'birth-from-id', label: 'Request birth record with ID', inputs: ['old-id'], output: 'birth', guards: ['waiver'], mode: 'record-request', routeId: 'local' },
        { id: 'issue', label: 'Agency decision', inputs: ['birth'], output: 'id-received', guards: ['waiver'], mode: 'receiver-decision', routeId: 'local' },
        { id: 'use-id', label: 'Use received ID', inputs: ['id-received'], output: 'old-id', guards: [], mode: 'preparation', routeId: 'local' }
      ],
      obligations: [{ id: 'trust', label: 'Trustworthy evidence', claimId: 'waiver', argument: 'A proposed argument.', exhibits: ['birth'], recoveryAttempts: [], objections: [] }],
      research: [{ id: 'locate', priority: 1, resolvesNodes: ['birth'], resolvesClaims: [], question: 'Is a record available without ID?', method: 'Read custodian access procedure.', checked: ['Synthetic fixture'], stopWhen: 'Actual access method known.', fallback: 'Record the specific barrier.' }]
    }
  };
}

test('a published waiver neither solves the no-ID cycle nor creates an approval', () => {
  const r = assess(fixture());
  assert.equal(r.outcome, 'open');
  assert.equal(r.circularDependencies.length, 1);
  assert.deepEqual(new Set(r.circularDependencies[0]), new Set(['id-received', 'birth', 'old-id']));
  assert.deepEqual(r.conditionalReachability, []);
  assert.equal(r.steps.find(s => s.id === 'issue').state, 'prerequisites-missing');
  assert.equal(r.research[0].id, 'locate');
});

test('an alternative signed-request path breaks the dependency cycle without creating possession', () => {
  const f = fixture();
  f.model.steps.push({ id: 'mail', label: 'Published no-photo-ID route', inputs: ['signed'], output: 'birth', guards: ['waiver'], mode: 'record-request', routeId: 'local' });
  const r = assess(f);
  assert.equal(r.steps.find(s => s.id === 'mail').state, 'ready-for-review');
  assert.ok(r.conditionalReachability.includes('birth'));
  assert.equal(r.nodes.find(n => n.id === 'birth').reading, 'unknown');
  assert.ok(!r.conditionalReachability.includes('id-received'));
  assert.equal(r.outcome, 'open');
});

test('a bounced email or draft cannot satisfy a matching receiver contract', () => {
  for (const outcome of ['draft-created', 'delivery-failed-user-unknown', 'biometrics-invitation-received']) {
    const f = fixture(); f.caseRecord.attempts[0].outcome = outcome;
    f.model.nodes.at(-1).observations.push({ side: 'for', basis: 'receiver-receipt', casePointer: '/attempts/0' });
    assert.throws(() => assess(f), /Unreceived or mismatched/);
  }
});

test('an attributed case report cannot impersonate a receiver outcome', () => {
  const f = fixture(); f.model.nodes.at(-1).observations.push({ side: 'for', basis: 'case-report', casePointer: '/facts/0' });
  assert.throws(() => assess(f), /Unreceived or mismatched/);
});

test('a matching dated physical receipt can close only its own case outcome', () => {
  const f = fixture(); f.caseRecord.attempts[0] = { date: '2026-10-26', receiver: 'Agency', outcome: 'photo-id-physically-received', receiptRef: 'private-source:synthetic-receipt' };
  f.model.nodes.at(-1).observations.push({ side: 'for', basis: 'receiver-receipt', casePointer: '/attempts/0' });
  assert.equal(assess(f).outcome, 'received-outcome-recorded');
  assert.equal(assess(fixture()).outcome, 'open');
  f.caseRecord.attempts[0].date = '2026-10-27';
  assert.throws(() => assess(f), /future/);
});

test('contradictory observations remain contested and cannot unlock an action', () => {
  const f = fixture();
  const n = f.model.nodes.find(n => n.id === 'birth');
  n.observations = [{ side: 'for', basis: 'case-report', casePointer: '/facts/0' }, { side: 'against', basis: 'case-report', casePointer: '/facts/0' }];
  const r = assess(f);
  assert.equal(r.nodes.find(n => n.id === 'birth').reading, 'contested');
  assert.equal(r.steps.find(s => s.id === 'issue').state, 'prerequisites-missing');
  assert.deepEqual(r.steps.find(s => s.id === 'issue').inputsContested, ['birth']);
});

test('source contradiction is retained even with repeated positive assertions', () => {
  const f = fixture(); f.model.claims.push({ ...f.model.claims[0], id: 'opposed', side: 'against' });
  f.model.claims.push({ ...f.model.claims[0], id: 'repeat' });
  const r = assess(f);
  assert.equal(r.claims[0].reading, 'contested');
  assert.equal(r.claims[0].statementId, r.claims[2].statementId);
  assert.equal(r.steps[0].state, 'source-blocked');
});

test('a receiving case must preserve the native source statement selected by its study', () => {
  const f = fixture(); const original = assess(f).claims[0].statementId;
  f.model.claims[0].statementId = original;
  assert.equal(assess(f).claims[0].reading, 'held');
  f.model.claims[0].text = 'A broader claim that the source study did not admit.';
  const changed = assess(f);
  assert.ok(changed.claims[0].problems.includes('native-study-statement-pin-mismatch'));
  assert.equal(changed.steps[0].state, 'source-blocked');
  assert.equal(changed.nodes[0].reading, 'held');
});

test('source supersession, future dates, overdue reviews and corrupt snapshots prevent recommendation', () => {
  for (const patch of [{ status: 'superseded' }, { retrievedOn: '2026-10-27' }, { retrievedOn: '2026-01-01' }, { artifact: 'x.pdf', integrity: 'failed' }]) {
    const f = fixture(); Object.assign(f.sourceRegistry.sources[0], patch);
    assert.equal(assess(f).steps[0].state, 'source-blocked');
  }
});

test('a source change reports affected assertions, actions and obligations rather than claiming changed law', () => {
  const f = fixture(), after = structuredClone(f.sourceRegistry);
  after.sources[0].status = 'superseded';
  const r = sourceImpact({ model: f.model, before: f.sourceRegistry, after });
  assert.deepEqual(r.claimIds, ['waiver']);
  assert.deepEqual(r.stepIds, ['birth-from-id', 'issue']);
  assert.deepEqual(r.obligationIds, ['trust']);
});

test('closed routes cannot become current recommendations', () => {
  const f = fixture(); f.caseRecord.routes[0].state = 'inactive-by-recorded-user-direction';
  const r = assess(f);
  assert.ok(r.steps.every(s => s.state === 'inactive'));
  assert.deepEqual(r.circularDependencies, []);
  assert.deepEqual(r.research, []);
});

test('a scenario changes neither the case nor its receipt state', () => {
  const f = fixture(), before = structuredClone(f);
  const r = assess({ ...f, assume: ['birth'] });
  assert.equal(r.hypothetical, true);
  assert.equal(r.outcome, 'open');
  assert.equal(r.steps.find(s => s.id === 'issue').state, 'await-receiver-decision');
  assert.deepEqual(f, before);
  assert.throws(() => assess({ ...f, assume: ['id-received'] }), /Cannot assume a receiver receipt/);
});

test('a written argument without held exhibits cannot pass the packet check', () => {
  const f = fixture();
  assert.equal(packet(f).state, 'incomplete');
  f.model.obligations[0].exhibits = [];
  assert.equal(packet(f).state, 'incomplete');
});

test('an assembled review packet still does not mean legal sufficiency', () => {
  const f = fixture(); f.model.obligations[0].exhibits = ['signed'];
  assert.equal(packet(f).state, 'assembled-for-review');
  assert.equal(assess(f).outcome, 'open');
  f.model.obligations[0].objections.push('Current-person match is unresolved.');
  assert.equal(packet(f).state, 'incomplete');
});

test('one supported exhibit alternative can be used without imposing every other acquisition route', () => {
  const f = fixture(); f.model.obligations[0].exhibits = []; f.model.obligations[0].exhibitAlternatives = [['birth'], ['signed']];
  assert.equal(packet(f).state, 'assembled-for-review');
  assert.equal(assess(f).nodes.find(n => n.id === 'birth').reading, 'unknown');
});

test('new observations are case-bound, idempotent proposals rather than fabricated evidence or silent writes', () => {
  const f = fixture(), before = structuredClone(f);
  const evidence = { nodeId: 'birth', observation: { basis: 'case-report', side: 'for', casePointer: '/facts/0' } };
  const first = proposeObservation(f, evidence);
  assert.equal(first.assessment.nodes.find(n => n.id === 'birth').reading, 'held');
  assert.deepEqual(f, before);
  assert.equal(proposeObservation({ ...f, model: first.model }, evidence).duplicate, true);
  assert.throws(() => proposeObservation(f, { ...evidence, observation: { ...evidence.observation, casePointer: '/missing/0' } }), /Unresolved case pointer/);
  assert.throws(() => proposeObservation(f, { ...evidence, nodeId: 'id-received' }), /Unreceived or mismatched/);
});

test('dangling references, duplicate IDs, invalid schema and fabricated terminal goals are refused', () => {
  const f = fixture(); f.model.steps[0].inputs = ['missing']; assert.throws(() => assess(f), /Unknown node/);
  const g = fixture(); g.model.nodes.push(g.model.nodes[0]); assert.throws(() => assess(g), /Duplicate node/);
  const h = fixture(); delete h.model.claims[0].locator; assert.throws(() => assess(h), /Invalid analysis model/);
  const i = fixture(); i.model.goals = ['signed']; assert.throws(() => assess(i), /terminal goal requires/);
  assert.throws(() => assess({ ...fixture(), asOf: '2026-02-30' }), /Invalid calendar/);
});

test('snapshot hashes are checked against actual files rather than a supplied verified flag', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'identity-access-'));
  try {
    const f = fixture(); f.sourceRegistry.sources[0] = { ...f.sourceRegistry.sources[0], artifact: 'form.pdf', sha256: 'incorrect', integrity: 'verified' };
    await Promise.all([writeFile(join(dir, 'case.json'), JSON.stringify(f.caseRecord)), writeFile(join(dir, 'model.json'), JSON.stringify(f.model)), writeFile(join(dir, 'sources.json'), JSON.stringify(f.sourceRegistry)), writeFile(join(dir, 'form.pdf'), 'changed source')]);
    const input = await loadInput({ casePath: join(dir, 'case.json'), modelPath: join(dir, 'model.json'), sourcesPath: join(dir, 'sources.json'), asOf: f.asOf });
    assert.equal(assess(input).steps[0].state, 'source-blocked');
    await assert.rejects(() => main(['assess', '--wat', 'x']), /Unknown option/);
    await assert.rejects(() => main(['assess', '--assume', 'birth']), /Assumptions require/);
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test('separate clients share no case facts, observations or mutable state', () => {
  const a = fixture(), b = fixture(); b.caseRecord.recipient = 'Synthetic client B'; b.caseRecord.caseId = b.model.caseId = 'synthetic-case-b'; b.model.nodes[0].observations = [];
  assess(a);
  const r = assess(b);
  assert.equal(r.nodes[0].reading, 'unknown');
  assert.ok(!JSON.stringify(r).includes('Synthetic client A'));
  assert.ok(!renderAssessment(r).includes('Synthetic client A'));
  assert.throws(() => assess({ ...b, model: a.model }), /different case/);
});
