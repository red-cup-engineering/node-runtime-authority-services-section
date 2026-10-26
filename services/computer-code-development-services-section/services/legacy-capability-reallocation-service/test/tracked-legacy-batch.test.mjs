import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import test from 'node:test';
import {composeTrackedLegacyRetirementBatch as compose} from '../src/tracked-legacy-batch.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const json = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');
const recordBytes = Buffer.from('{ "decision": "accepted", "detail": "é\\noriginal" }\n');
function fixture() {
  const cap = (id, path, evidence) => ({id, disposition:'covered', reason:'Independently inspected living folder job', sourcePaths:[path], evidence});
  const plan = capabilities => ({kind:'legacy-capability-retirement-plan/v1', repositoryRoot:'/source',
    legacyRoot:'lib/legacy', revision:'a'.repeat(40), capabilities});
  return {id:'two-jobs',repositoryRoot:'/source/records',receivingPath:'batch/receiving.json',
    plans:[
      {path:'first-plan.json',bytes:json(plan([cap('first','a.mjs',[
        {path:'living/tool.mjs',sha256:'b'.repeat(64)},
        {repositoryRoot:'/source/records',path:'receipt.json',sha256:sha(recordBytes)},
      ])]))},
      {path:'second-plan.json',bytes:json(plan([cap('second','é\\n[b]*.mjs',[
        {path:'records/receipt.json',sha256:sha(recordBytes)},
      ])]))},
    ],
    supportingRecords:[{path:'receipt.json',bytes:recordBytes}]};
}
function edit(input, index, update) {
  const value = JSON.parse(input.plans[index].bytes);
  update(value); input.plans[index].bytes = json(value);
  return input;
}

test('combines reviewed jobs and exact raw records while preserving direct code witnesses', () => {
  const input = fixture(), before = input.plans.map(row => Buffer.from(row.bytes));
  const out = compose(input);
  assert.deepEqual(out.plan.capabilities.flatMap(row => row.sourcePaths), ['a.mjs','é\\n[b]*.mjs']);
  assert.equal(out.plan.repositoryRoot,'/source');
  assert.equal(out.plan.revision,'a'.repeat(40));
  assert.deepEqual(out.plan.capabilities[0].evidence[0],{path:'living/tool.mjs',sha256:'b'.repeat(64)});
  const witness = {repositoryRoot:'/source/records',path:'batch/receiving.json',sha256:sha(out.receivingBytes)};
  assert.deepEqual(out.plan.capabilities[0].evidence[1],witness);
  assert.deepEqual(out.plan.capabilities[1].evidence,[witness]);
  assert(Buffer.from(out.receiving.supportingRecords[0].text).equals(recordBytes));
  assert.equal(out.receiving.supportingRecords[0].sha256,sha(recordBytes));
  for (let i=0;i<before.length;i++) {
    assert(input.plans[i].bytes.equals(before[i]));
    assert(Buffer.from(out.receiving.plans[i].text).equals(before[i]));
    assert.equal(out.receiving.plans[i].sha256,sha(before[i]));
  }
  assert.match(out.receiving.claim,/no new capability, authority, installation or independent-review/u);
});

test('deterministic replay retains byte-identical plan and snapshot identities', () => {
  const first = compose(fixture()), repeated = compose(fixture());
  assert(first.planBytes.equals(repeated.planBytes));
  assert(first.receivingBytes.equals(repeated.receivingBytes));
});

test('different legitimate record bytes change the snapshot and every rebound witness', () => {
  const input = fixture(), first = compose(input);
  input.supportingRecords[0].bytes = Buffer.from('{"decision":"accepted","detail":"different supplied evidence"}\n');
  for (let i=0;i<2;i++) edit(input,i,p => {
    for (const evidence of p.capabilities[0].evidence) if (evidence.path.endsWith('receipt.json')) evidence.sha256=sha(input.supportingRecords[0].bytes);
  });
  const next = compose(input);
  assert.notEqual(sha(first.receivingBytes),sha(next.receivingBytes));
  assert.equal(next.plan.capabilities[1].evidence[0].sha256,sha(next.receivingBytes));
});

test('individually valid plans with different owner, subtree or revision cannot glue', () => {
  for (const [key,value] of [['repositoryRoot','/different'],['legacyRoot','other/legacy'],['revision','c'.repeat(40)]]) {
    assert.throws(() => compose(edit(fixture(),1,p=>{p[key]=value;})),/different source cuts/u);
  }
});

test('overlapping sources and duplicate capability identities cannot be counted twice', () => {
  assert.throws(() => compose(edit(fixture(),1,p=>{p.capabilities[0].sourcePaths=['a.mjs'];})),/repeated or unsafe source/u);
  assert.throws(() => compose(edit(fixture(),1,p=>{p.capabilities[0].id='first';})),/unique capability/u);
});

test('explicit upstream roots survive assembly and cannot be mixed or escape source', () => {
  const input=fixture();
  for(let i=0;i<2;i++)edit(input,i,p=>{p.sourceLegacyRoot='moved/legacy';});
  const out=compose(input);
  assert.equal(out.plan.sourceLegacyRoot,'moved/legacy');
  assert.equal(out.receiving.source.sourceLegacyRoot,'moved/legacy');
  assert.throws(()=>compose(edit(fixture(),1,p=>{p.sourceLegacyRoot='moved/legacy';})),/different source cuts/u);
  for(const root of ['../legacy','/tmp/legacy','source/.git/legacy','source\\..\\legacy','source/legacy\n'])
    assert.throws(()=>compose(edit(fixture(),0,p=>{p.sourceLegacyRoot=root;})),/confined source legacy root/u);
});

test('covered and deprecated judgments retain the ordinary authority contract', () => {
  assert.throws(() => compose(edit(fixture(),1,p=>{p.capabilities[0].evidence=[];})),/living implementation evidence/u);
  assert.throws(() => compose(edit(fixture(),1,p=>{p.capabilities[0].disposition='deprecated';})),/deprecation authority/u);
  const valid = edit(fixture(),1,p=>{
    p.capabilities[0].disposition='deprecated';p.capabilities[0].authorization='Leader explicitly deprecated this Lean material';
    p.capabilities[0].sourcePaths=['proof.lean'];delete p.capabilities[0].evidence;
  });
  assert.equal(compose(valid).plan.capabilities[1].authorization,'Leader explicitly deprecated this Lean material');
  assert.throws(() => compose(edit(fixture(),1,p=>{p.capabilities[0].id={arbitrary:'object'};})),/unique capability/u);
});

test('changed record bytes refuse before replacing their original evidence witness', () => {
  const input = fixture();input.supportingRecords[0].bytes=Buffer.from('{"decision":"not the reviewed bytes"}');
  assert.throws(() => compose(input),/supporting evidence changed/u);
  assert.throws(() => compose(edit(fixture(),0,p=>{delete p.capabilities[0].evidence[1].sha256;})),/lacks its reviewed digest/u);
});

test('unsafe, legacy, duplicate and self-referential record addresses refuse', () => {
  const cases=[
    x=>{x.supportingRecords[0].path='../outside.json';},
    x=>{x.supportingRecords[0].path='legacy/receipt.json';},
    x=>{x.supportingRecords.push({...x.supportingRecords[0]});},
    x=>{x.receivingPath=x.plans[0].path;},
  ];
  for (const update of cases) { const input=fixture();update(input);assert.throws(()=>compose(input)); }
});

test('input count, byte and UTF-8 bounds are checked without materializing a graph', () => {
  const count=fixture();count.plans=Array(33).fill(count.plans[0]);assert.throws(()=>compose(count),/bounded explicit plans/u);
  const size=fixture();size.supportingRecords[0].bytes=Buffer.alloc(1_048_577);assert.throws(()=>compose(size),/combined input/u);
  const utf8=fixture();utf8.supportingRecords[0].bytes=Buffer.from([0xff]);assert.throws(()=>compose(utf8),/exact UTF-8/u);
});

