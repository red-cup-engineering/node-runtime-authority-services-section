import { readFileSync } from 'node:fs';
import { validateJsonSchema } from '@red-cup-engineering/json-schema-services-section/validation';
import { readingOfSides } from '@red-cup-engineering/computer-data-engineering-services-section/four';
import { createSourceStatement } from '@red-cup-engineering/signcell/source-statement';

const schema = JSON.parse(readFileSync(new URL('../data/schemas/analysis.schema.json', import.meta.url)));
const datePattern = /^\d{4}-\d{2}-\d{2}$/;
const day = value => {
  if (typeof value !== 'string' || !datePattern.test(value)) throw new TypeError('Explicit ISO assessment/source date required');
  const ms = Date.parse(value + 'T00:00:00Z');
  if (!Number.isFinite(ms) || new Date(ms).toISOString().slice(0, 10) !== value) throw new TypeError('Invalid calendar date: ' + value);
  return ms / 86400000;
};
export { day as validateAssessmentDate };
const unique = (items, label) => {
  const map = new Map();
  for (const item of items) {
    if (map.has(item.id)) throw new TypeError(`Duplicate ${label}: ${item.id}`);
    map.set(item.id, item);
  }
  return map;
};
const reference = (map, id, label) => {
  if (!map.has(id)) throw new TypeError(`Unknown ${label}: ${id}`);
  return map.get(id);
};
function atPointer(value, pointer) {
  for (const part of pointer.slice(1).split('/').map(p => p.replace(/~1/g, '/').replace(/~0/g, '~'))) {
    if (!value || !Object.hasOwn(value, part)) throw new TypeError('Unresolved case pointer: ' + pointer);
    value = value[part];
  }
  return value;
}

function receive({ caseRecord, model, sourceRegistry, evidenceAudit = null, asOf, assume = [] }) {
  day(asOf);
  const result = validateJsonSchema(model, schema);
  if (!result.valid) throw new TypeError('Invalid analysis model: ' + JSON.stringify(result.issues));
  if (caseRecord.recordType !== model.caseRecordType) throw new TypeError('Analysis/case record type mismatch');
  if (caseRecord.caseId !== model.caseId) throw new TypeError('Analysis belongs to a different case');
  if (evidenceAudit && evidenceAudit.caseId !== caseRecord.caseId) throw new TypeError('Evidence audit belongs to a different case');
  if (evidenceAudit && (evidenceAudit.kind !== 'identity-evidence-audit' || !Array.isArray(evidenceAudit.manifestProblems) || !Array.isArray(evidenceAudit.items) || evidenceAudit.items.some(item => !item || typeof item.sourceId !== 'string' || !Array.isArray(item.issues)))) throw new TypeError('Invalid evidence audit');
  const nodes = unique(model.nodes, 'node'), claims = unique(model.claims, 'claim');
  const sources = unique(sourceRegistry.sources, 'source'), steps = unique(model.steps, 'step');
  const routes = unique(caseRecord.routes, 'case route');
  unique(model.obligations, 'obligation'); unique(model.research, 'research task');
  for (const id of [...model.goals, ...assume]) reference(nodes, id, 'node');
  for (const id of model.goals) if (nodes.get(id).kind !== 'receipt') throw new TypeError('A terminal goal requires a receiver receipt: ' + id);
  for (const n of nodes.values()) if (n.kind === 'receipt' && !n.receiptContract) throw new TypeError('Receipt contract required: ' + n.id);
  for (const c of claims.values()) reference(sources, c.sourceId, 'source');
  for (const s of steps.values()) {
    reference(routes, s.routeId, 'case route');
    for (const id of [...s.inputs, s.output]) reference(nodes, id, 'node');
    for (const id of s.guards) reference(claims, id, 'claim');
    if (nodes.get(s.output).kind === 'receipt' && s.mode !== 'receiver-decision') throw new TypeError('Only a receiver can produce a receipt: ' + s.id);
    if (s.mode !== 'preparation' && s.guards.length === 0) throw new TypeError('External procedure requires a sourced guard: ' + s.id);
  }
  for (const o of model.obligations) {
    reference(claims, o.claimId, 'claim');
    for (const id of [...o.exhibits, ...(o.exhibitAlternatives ?? []).flat(), ...o.recoveryAttempts]) reference(nodes, id, 'node');
  }
  for (const task of model.research) {
    for (const id of task.resolvesNodes) reference(nodes, id, 'node');
    for (const id of task.resolvesClaims) reference(claims, id, 'claim');
  }
  return { caseRecord, model, sources, claims, nodes, steps, routes, evidenceAudit, asOf, assume: new Set(assume) };
}

function sourceProblems(source, asOf) {
  const problems = [];
  if (source.status !== 'current') problems.push('source-' + (source.status ?? 'unreviewed'));
  if (source.integrity === 'failed') problems.push('snapshot-integrity-failed');
  if (source.artifact && source.integrity !== 'verified') problems.push('snapshot-not-verified');
  if (!Number.isInteger(source.reviewAfterDays) || source.reviewAfterDays < 0) problems.push('source-review-interval-missing');
  if (!source.retrievedOn) problems.push('source-review-date-missing');
  else {
    const age = day(asOf) - day(source.retrievedOn);
    if (age < 0) problems.push('source-from-future');
    if (Number.isInteger(source.reviewAfterDays) && age > source.reviewAfterDays) problems.push('source-review-overdue');
  }
  return problems;
}

function claimReadings(ctx) {
  const admitted = [];
  for (const claim of ctx.claims.values()) {
    const source = ctx.sources.get(claim.sourceId);
    const statement = createSourceStatement({
      sourceSubject: source.id, sourceUrl: source.url, sourceTitle: source.title,
      text: claim.text, force: 'alleges', status: 'source-supported', attribution: 'required',
      scope: 'no broader than this source assertion', sourceAssertedAt: source.retrievedOn,
      ...(source.sha256 ? { evidenceDigest: 'sha256:' + source.sha256 } : {})
    });
    if (!statement.ok) throw new TypeError('Native source statement refused: ' + JSON.stringify(statement.refusal));
    const problems = sourceProblems(source, ctx.asOf);
    if (claim.statementId && claim.statementId !== statement.value.id) problems.push('native-study-statement-pin-mismatch');
    admitted.push({ ...claim, statementId: statement.value.id, sourceUrl: source.url, problems });
  }
  return admitted.map(claim => {
    const peers = admitted.filter(c => c.proposition === claim.proposition && c.problems.length === 0);
    return { ...claim, reading: readingOfSides('extremal', peers.some(c => c.side === 'for'), peers.some(c => c.side === 'against')) };
  });
}

function nodeReadings(ctx) {
  return [...ctx.nodes.values()].map(node => {
    const observations = node.observations.map(obs => {
      const witness = atPointer(ctx.caseRecord, obs.casePointer);
      if (typeof witness !== 'object' || witness === null) throw new TypeError('Case witness must be a record: ' + obs.casePointer);
      if (node.kind === 'receipt' || obs.basis === 'receiver-receipt') {
        if (!node.receiptContract || obs.basis !== 'receiver-receipt' || witness.outcome !== node.receiptContract.outcome || witness.receiver !== node.receiptContract.receiver || !witness.date || !witness.receiptRef)
          throw new TypeError('Unreceived or mismatched receiver outcome: ' + node.id);
        if (day(witness.date) > day(ctx.asOf)) throw new TypeError('Receipt is from the future: ' + node.id);
      }
      return obs;
    });
    const reading = readingOfSides('extremal', observations.some(o => o.side === 'for'), observations.some(o => o.side === 'against'));
    if (ctx.assume.has(node.id) && node.kind === 'receipt') throw new TypeError('Cannot assume a receiver receipt: ' + node.id);
    const evidenceProblems = (node.artifactSourceIds ?? []).flatMap(sourceId => {
      const audit = ctx.evidenceAudit;
      if (!audit || audit.asOf !== ctx.asOf || audit.manifestProblems.length) return [{ sourceId, problem: 'artifact-audit-unavailable' }];
      const matches = audit.items.filter(item => item.sourceId === sourceId);
      return matches.length !== 1 || matches[0].state !== 'verified' || matches[0].issues.length ? [{ sourceId, problem: 'required-artifact-unverified' }] : [];
    });
    return { ...node, reading, evidenceProblems, hypothetical: ctx.assume.has(node.id), usable: !evidenceProblems.length && (reading === 'held' || (ctx.assume.has(node.id) && reading !== 'contested')) };
  });
}

function circularPaths(ctx, known) {
  const paths = new Map();
  function walk(id, trail) {
    if (known.has(id)) return;
    if (trail.includes(id)) {
      const cycle = [...trail.slice(trail.indexOf(id)), id];
      const key = [...new Set(cycle)].sort().join('|');
      paths.set(key, cycle); return;
    }
    for (const step of ctx.steps.values()) {
      if (step.output !== id || !routeActive(ctx.routes.get(step.routeId))) continue;
      for (const input of step.inputs) walk(input, [...trail, id]);
    }
  }
  for (const id of ctx.model.goals) walk(id, []);
  return [...paths.values()];
}
const routeActive = route => ['assessing', 'ready-for-review', 'authorized', 'submitted', 'additional-evidence-requested', 'denied', 'issued', 'received', 'use-confirmed'].includes(route.state);

export function assess(input) {
  const ctx = receive(input);
  const claims = claimReadings(ctx), nodes = nodeReadings(ctx);
  const claimMap = new Map(claims.map(c => [c.id, c]));
  const nodeMap = new Map(nodes.map(n => [n.id, n]));
  const held = new Set(nodes.filter(n => n.usable).map(n => n.id));
  const steps = [...ctx.steps.values()].map(step => {
    const missingInputs = step.inputs.filter(id => !held.has(id));
    const guardProblems = step.guards.flatMap(id => {
      const c = claimMap.get(id);
      return [...c.problems.map(problem => ({ claimId: id, problem })), ...(c.reading !== 'held' || c.side !== 'for' ? [{ claimId: id, problem: 'assertion-' + c.reading }] : [])];
    });
    const active = routeActive(ctx.routes.get(step.routeId));
    const inputsContested = step.inputs.filter(id => nodeMap.get(id).reading === 'contested');
    return { ...step, active, missingInputs, inputsContested, guardProblems,
      state: !active ? 'inactive' : guardProblems.length ? 'source-blocked' : missingInputs.length ? 'prerequisites-missing' : step.mode === 'receiver-decision' ? 'await-receiver-decision' : 'ready-for-review' };
  });
  // This is a conditional plan closure, never evidence of possession or acceptance.
  const reachable = new Set(held);
  let changed = true;
  while (changed) {
    changed = false;
    for (const step of steps) if (step.active && !step.guardProblems.length && step.mode !== 'receiver-decision' && !reachable.has(step.output) && nodeMap.get(step.output).reading !== 'contested' && step.inputs.every(id => reachable.has(id))) {
      reachable.add(step.output); changed = true;
    }
  }
  const relevant = new Set(ctx.model.goals);
  let enlarged = true;
  while (enlarged) {
    enlarged = false;
    for (const step of steps) if (step.active && relevant.has(step.output)) for (const id of step.inputs) if (!relevant.has(id)) { relevant.add(id); enlarged = true; }
  }
  const neededClaims = new Set(steps.filter(s => s.active && relevant.has(s.output)).flatMap(s => s.guards));
  const research = ctx.model.research.filter(task => task.resolvesNodes.some(id => relevant.has(id) && !held.has(id)) || task.resolvesClaims.some(id => neededClaims.has(id) && (claimMap.get(id).reading !== 'held' || claimMap.get(id).problems.length)))
    .sort((a, b) => a.priority - b.priority || a.id.localeCompare(b.id));
  return {
    kind: 'identity-document-access-assessment', asOf: ctx.asOf, recipient: ctx.caseRecord.recipient,
    jurisdiction: ctx.model.jurisdiction, hypothetical: ctx.assume.size > 0, assumptions: [...ctx.assume],
    outcome: ctx.model.goals.every(id => held.has(id)) && !ctx.assume.size ? 'received-outcome-recorded' : 'open',
    limitations: 'Source-bound planning. No legal sufficiency, government acceptance, external action or physical receipt is inferred.',
    nodes, claims, steps, evidenceAudit: ctx.evidenceAudit, circularDependencies: circularPaths(ctx, held),
    conditionalReachability: [...reachable].filter(id => !held.has(id)), research,
    unseededPrerequisites: [...relevant].filter(id => !held.has(id) && !steps.some(s => s.active && s.output === id)),
    goals: ctx.model.goals.map(id => ({ id, label: nodeMap.get(id).label, reading: nodeMap.get(id).reading }))
  };
}

export function packet(input) {
  const assessment = assess(input);
  const nodes = new Map(assessment.nodes.map(n => [n.id, n]));
  const claims = new Map(assessment.claims.map(c => [c.id, c]));
  const obligations = input.model.obligations.map(o => {
    const claim = claims.get(o.claimId);
    const exhibit = id => {
      const node = nodes.get(id);
      return { id, label: node.label, reading: node.reading, usable: node.usable, evidenceProblems: node.evidenceProblems, provenance: node.provenance ?? null, limits: node.limits ?? null };
    };
    const exhibits = o.exhibits.map(exhibit);
    const alternatives = (o.exhibitAlternatives ?? []).map(ids => ids.map(exhibit));
    const alternativeReady = !alternatives.length || alternatives.some(group => group.every(e => e.usable && e.provenance));
    const missing = exhibits.filter(e => !e.usable).map(e => e.id);
    const provenanceMissing = exhibits.filter(e => e.usable && !e.provenance).map(e => e.id);
    const recovery = o.recoveryAttempts.map(id => ({ id, reading: nodes.get(id).reading, usable: nodes.get(id).usable }));
    return { ...o, sourceUrl: claim.sourceUrl, locator: claim.locator, exhibits, alternatives, recovery,
      state: claim.problems.length || claim.reading !== 'held' || claim.side !== 'for' ? 'source-blocked' : !o.argument || (!exhibits.length && !alternatives.length) || missing.length || provenanceMissing.length || !alternativeReady || recovery.some(r => !r.usable) || o.objections.length ? 'incomplete' : 'assembled-for-review',
      missing, provenanceMissing };
  });
  return { kind: 'identity-document-access-packet', asOf: input.asOf, recipient: assessment.recipient,
    state: obligations.length && obligations.every(o => o.state === 'assembled-for-review') ? 'assembled-for-review' : 'incomplete',
    limitations: 'Even an assembled packet is not an agency finding that these conditions are satisfied.', obligations };
}

/** Propose a case-bound observation update using a witness already in the case owner.
 * This returns an updated model for review; it does not mutate the case or invent evidence. */
export function proposeObservation(input, evidence) {
  const received = validateJsonSchema(evidence, {
    $schema: schema.$schema, $defs: schema.$defs, type: 'object', additionalProperties: false,
    required: ['nodeId', 'observation'], properties: { nodeId: { type: 'string', minLength: 1 }, observation: { $ref: '#/$defs/observation' } }
  });
  if (!received.valid) throw new TypeError('Invalid observation proposal: ' + JSON.stringify(received.issues));
  const model = structuredClone(input.model);
  const node = model.nodes.find(n => n.id === evidence.nodeId);
  if (!node) throw new TypeError('Unknown observation node: ' + evidence.nodeId);
  const duplicate = node.observations.some(o => o.side === evidence.observation.side && o.basis === evidence.observation.basis && o.casePointer === evidence.observation.casePointer);
  if (!duplicate) node.observations.push(evidence.observation);
  const assessment = assess({ ...input, model });
  return { kind: 'identity-document-access-observation-proposal', caseId: model.caseId, duplicate, model, assessment };
}

export function sourceImpact({ model, before, after }) {
  const old = unique(before.sources, 'source'), next = unique(after.sources, 'source');
  const sourceIds = [...new Set([...old.keys(), ...next.keys()])].filter(id => JSON.stringify(old.get(id)) !== JSON.stringify(next.get(id)));
  const claimIds = model.claims.filter(c => sourceIds.includes(c.sourceId)).map(c => c.id);
  const stepIds = model.steps.filter(s => s.guards.some(id => claimIds.includes(id))).map(s => s.id);
  const obligationIds = model.obligations.filter(o => claimIds.includes(o.claimId)).map(o => o.id);
  return { kind: 'identity-document-access-source-impact', sourceIds, claimIds, stepIds, obligationIds,
    instruction: 'Re-review these assertions and their consumers. Do not infer that changed bytes mean changed law.' };
}

export function renderAssessment(report) {
  const lines = [`# Identity document access assessment`, '', `${report.recipient}; ${report.jurisdiction}; assessed ${report.asOf}. Outcome: ${report.outcome}.${report.hypothetical ? ' HYPOTHETICAL: ' + report.assumptions.join(', ') : ''}`, '', report.limitations, '', '## Evidence dependencies', ''];
  if (report.evidenceAudit) lines.push(`Retained-artifact audit: ${report.evidenceAudit.state}. ${report.evidenceAudit.limits}`, '');
  for (const node of report.nodes.filter(n => n.evidenceProblems.length)) lines.push(`- ${node.id}: attributed reading ${node.reading}; unavailable for preparation: ${node.evidenceProblems.map(p => p.sourceId + ': ' + p.problem).join('; ')}.`);
  for (const step of report.steps) lines.push(`- **${step.id}: ${step.label}** — ${step.state}. ${step.missingInputs.length ? 'Missing: ' + step.missingInputs.join(', ') + '. ' : ''}${step.guardProblems.map(p => p.claimId + ': ' + p.problem).join('; ')}${step.limits ? ' ' + step.limits : ''}`.trimEnd());
  lines.push('', '## Circular dependencies', '');
  for (const cycle of report.circularDependencies) lines.push('- ' + cycle.join(' → '));
  if (!report.circularDependencies.length) lines.push('No cycle found in the modeled active dependencies. This does not prove all real-world prerequisites have been modeled.');
  lines.push('', '## Research frontier', '');
  for (const task of report.research) lines.push(`### ${task.id}: ${task.question}`, '', task.method, '', `Already checked: ${task.checked.join('; ')}.`, '', `Stop when: ${task.stopWhen}`, '', `Fallback: ${task.fallback}`, '');
  lines.push('## Source-bound assertions', '');
  for (const c of report.claims) lines.push(`- ${c.id}: ${c.text} [${c.sourceId}, ${c.locator}](${c.sourceUrl}). ${c.problems.length ? c.problems.join(', ') : c.reading}.`);
  return lines.join('\n') + '\n';
}

export function renderPacket(report) {
  const lines = ['# Variance evidence matrix', '', `${report.recipient}; ${report.asOf}. Packet: ${report.state}.`, '', report.limitations, ''];
  for (const o of report.obligations) {
    lines.push(`## ${o.id}: ${o.label}`, '', `State: ${o.state}. [Authority: ${o.locator}](${o.sourceUrl}).`, '', o.argument || 'No case argument recorded.', '');
    for (const e of o.exhibits) lines.push(`- ${e.id}: ${e.label}; attributed reading ${e.reading}; usable for preparation: ${e.usable}.${e.evidenceProblems.length ? ' Artifact problems: ' + e.evidenceProblems.map(p => p.sourceId + ': ' + p.problem).join('; ') + '.' : ''} Provenance: ${(e.provenance ?? 'missing').replace(/\.+$/u, '')}.${e.limits ? ' Limitation: ' + e.limits : ''}`);
    for (const [index, group] of o.alternatives.entries()) lines.push(`- Alternative ${index + 1}: ` + group.map(e => `${e.id} (${e.reading}; usable for preparation ${e.usable}; provenance ${e.provenance ? 'specified' : 'missing'})`).join('; ') + '.');
    for (const r of o.recovery) lines.push(`- Recovery attempt ${r.id}: ${r.reading}; usable for preparation ${r.usable}.`);
    if (o.objections.length) lines.push('', 'Unresolved objections:', '', ...o.objections.map(s => '- ' + s));
    lines.push('');
  }
  return lines.join('\n') + '\n';
}
