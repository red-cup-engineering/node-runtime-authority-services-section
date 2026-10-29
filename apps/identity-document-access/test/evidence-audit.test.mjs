import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { auditEvidence } from '../src/evidence-audit.mjs';
import { assess, packet, renderAssessment } from '../src/identity-access.mjs';
import { main } from '../bin/identity-access.mjs';

async function fixture(t) {
  const dir = await mkdtemp(join(tmpdir(), 'identity-evidence-'));
  t.after(() => rm(dir, {recursive:true, force:true}));
  const bytes = Buffer.from('private original fixture');
  const manifest = {kind:'identity-evidence-acquisition-manifest', version:1, caseId:'test-client', artifacts:[{sourceId:'original', file:'original.bin', bytes:bytes.length, sha256:createHash('sha256').update(bytes).digest('hex')}]};
  const manifestPath = join(dir, 'manifest.json');
  await writeFile(join(dir, 'original.bin'), bytes);
  const save = () => writeFile(manifestPath, JSON.stringify(manifest));
  await save();
  const input = {asOf:'2026-10-26',caseRecord:{caseId:'test-client',recordType:'test-case',recipient:'Synthetic',routes:[{id:'local',state:'assessing'}],facts:[{claim:'Original recovered'}]},sourceRegistry:{sources:[]},model:{version:1,caseId:'test-client',caseRecordType:'test-case',jurisdiction:'Synthetic',goals:['received'],claims:[],nodes:[{id:'original',label:'Original',kind:'document',artifactSourceIds:['original'],provenance:'Synthetic',observations:[{side:'for',basis:'case-report',casePointer:'/facts/0'}]},{id:'assembled',label:'Prepared',kind:'document',observations:[]},{id:'received',label:'Received',kind:'receipt',receiptContract:{receiver:'Agency',outcome:'photo-id-physically-received'},observations:[]}],steps:[{id:'prepare',label:'Prepare',inputs:['original'],output:'assembled',guards:[],mode:'preparation',routeId:'local'}],obligations:[],research:[]}};
  return {dir,bytes,manifest,manifestPath,save,input,audit:()=>auditEvidence({manifestPath,caseId:'test-client',asOf:input.asOf})};
}

test('CLI binds retained originals to one case and audits without exposing or changing them', async t => {
  const f=await fixture(t);
  for (const [name,value] of [['case',f.input.caseRecord],['model',f.input.model],['sources',f.input.sourceRegistry]]) await writeFile(join(f.dir,name+'.json'),JSON.stringify(value));
  await writeFile(join(f.dir,'service.json'),JSON.stringify({kind:'identity-document-access-service',version:1,casePath:'case.json',modelPath:'model.json',sourcesPath:'sources.json',evidenceManifestPath:'manifest.json'}));
  const before=await readFile(f.manifestPath);
  const output=await main(['assess','--service',join(f.dir,'service.json'),'--as-of',f.input.asOf]);
  const r=JSON.parse(output);
  assert.equal(r.evidenceAudit.state,'verified');
  assert.equal(r.steps[0].state,'ready-for-review');
  assert.equal(r.nodes.at(-1).reading,'unknown');
  assert.equal(r.outcome,'open');
  assert.ok(!output.includes(f.dir));
  assert.ok(!output.includes('private original fixture'));
  assert.deepEqual(await readFile(join(f.dir,'original.bin')),f.bytes);
  assert.deepEqual(await readFile(f.manifestPath),before);
});

test('same-size corruption blocks preparation but preserves the attributed observation', async t => {
  const f=await fixture(t);
  await writeFile(join(f.dir,'original.bin'),Buffer.alloc(f.bytes.length,42));
  const audit=await f.audit();
  assert.deepEqual(audit.items[0].issues,['artifact-digest-mismatch']);
  const r=assess({...f.input,evidenceAudit:audit});
  assert.equal(r.nodes[0].reading,'held');
  assert.equal(r.nodes[0].usable,false);
  assert.equal(r.steps[0].state,'prerequisites-missing');
  assert.match(renderAssessment(r),/unavailable for preparation/);
  assert.equal(r.nodes.at(-1).reading,'unknown');
});

test('missing, truncated, symlink and escaping originals cannot satisfy an exhibit', async t => {
  const f=await fixture(t);
  await rm(join(f.dir,'original.bin'));
  assert.equal((await f.audit()).state,'incomplete');
  await writeFile(join(f.dir,'original.bin'),'short');
  assert.ok((await f.audit()).items[0].issues.includes('artifact-size-mismatch'));
  await symlink('original.bin',join(f.dir,'linked.bin'));
  f.manifest.artifacts[0].file='linked.bin'; await f.save();
  assert.deepEqual((await f.audit()).items[0].issues,['artifact-not-regular-file']);
  f.manifest.artifacts[0].file='../outside'; await f.save();
  assert.deepEqual((await f.audit()).items[0].issues,['artifact-path-not-contained']);
});

test('wrong-case, malformed and duplicated manifests fail without admitting artifact rows', async t => {
  const f=await fixture(t);
  f.manifest.caseId='other-client'; await f.save();
  assert.deepEqual((await f.audit()).manifestProblems,['manifest-case-mismatch']);
  assert.equal((await f.audit()).items.length,0);
  f.manifest.caseId='test-client'; f.manifest.artifacts.push({...f.manifest.artifacts[0]}); await f.save();
  assert.deepEqual((await f.audit()).manifestProblems,['duplicate-artifact-source']);
  await writeFile(f.manifestPath,'{}');
  assert.deepEqual((await f.audit()).manifestProblems,['manifest-invalid']);
});

test('unaudited and stale exhibits stay unavailable; a foreign or malformed audit is refused', async t => {
  const f=await fixture(t);
  assert.equal(assess(f.input).nodes[0].usable,false);
  const audit=await f.audit();
  assert.equal(assess({...f.input,evidenceAudit:{...audit,asOf:'2026-10-25'}}).nodes[0].usable,false);
  assert.throws(()=>assess({...f.input,evidenceAudit:{...audit,caseId:'other-client'}}),/different case/);
  assert.throws(()=>assess({...f.input,evidenceAudit:{caseId:'test-client'}}),/Invalid evidence audit/);
});

test('a reported recovery attempt with unavailable bytes cannot complete a review packet', async t => {
  const f=await fixture(t);
  f.input.sourceRegistry.sources=[{id:'rule',title:'Synthetic rule',url:'https://example.org/rule',retrievedOn:f.input.asOf,reviewAfterDays:14,status:'current'}];
  f.input.model.claims=[{id:'guard',proposition:'synthetic',sourceId:'rule',locator:'test',text:'Synthetic packet obligation.',side:'for'}];
  f.input.model.nodes.push({id:'argument',label:'Argument',kind:'document',provenance:'Synthetic',observations:[{side:'for',basis:'case-report',casePointer:'/facts/0'}]});
  f.input.model.obligations=[{id:'proof',label:'Proof',claimId:'guard',argument:'Synthetic argument.',exhibits:['argument'],recoveryAttempts:['original'],objections:[]}];
  assert.equal(packet({...f.input,evidenceAudit:await f.audit()}).state,'assembled-for-review');
  await rm(join(f.dir,'original.bin'));
  const r=packet({...f.input,evidenceAudit:await f.audit()});
  assert.equal(r.obligations[0].recovery[0].reading,'held');
  assert.equal(r.state,'incomplete');
});
