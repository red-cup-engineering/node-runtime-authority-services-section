import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,existsSync,rmSync,unlinkSync,renameSync,symlinkSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import test from 'node:test';
import {retireTrackedLegacyCapabilities,commitTrackedLegacyRetirement} from '../src/tracked-legacy-retirement.mjs';
import {composeTrackedLegacyRetirementBatch} from '../src/tracked-legacy-batch.mjs';

function fixture(t) {
 const root=mkdtempSync(join(tmpdir(),'legacy-staged-move-'));
 t.after(()=>rmSync(root,{recursive:true,force:true}));
 const git=(...args)=>execFileSync('git',['-C',root,...args],{stdio:['ignore','pipe','pipe']}).toString().trim();
 git('init');git('config','user.name','Test');git('config','user.email','test@example.invalid');
 mkdirSync(join(root,'source/legacy'),{recursive:true});mkdirSync(join(root,'lib'));mkdirSync(join(root,'living'));
 writeFileSync(join(root,'source/legacy/a.md'),'received historical information\n');
 writeFileSync(join(root,'source/legacy/unselected.md'),'keep\n');
 writeFileSync(join(root,'living/receiver.mjs'),'export const received=true;\n');
 writeFileSync(join(root,'README.md'),'before\n');
 git('add','.');git('commit','-m','original source');
 const revision=git('rev-parse','HEAD');
 git('mv','source/legacy','lib/legacy');
 writeFileSync(join(root,'README.md'),'another writer\n');git('add','README.md');
 const plan={kind:'legacy-capability-retirement-plan/v1',repositoryRoot:root,legacyRoot:'source/legacy',workingLegacyRoot:'lib/legacy',revision,
  capabilities:[{id:'received',disposition:'covered',reason:'Information reached its living reader',sourcePaths:['a.md'],evidence:[{path:'living/receiver.mjs'}]}]};
 return {root,git,plan};
}

test('ordinary original-path commit still lands while another file remains staged',t=>{
 const {root,git,plan}=fixture(t);git('mv','lib/legacy','source/legacy');delete plan.workingLegacyRoot;
 const other=git('diff','--cached','--raw','--','README.md');
 const applied=retireTrackedLegacyCapabilities({plan,apply:true});assert.deepEqual(applied.counts,{removed:1});assert.equal(applied.workingLegacyRoot,undefined);
 assert.equal(commitTrackedLegacyRetirement({result:applied}).state,'committed');
 assert.equal(git('ls-tree','HEAD','--','source/legacy/a.md'),'');assert.equal(git('diff','--cached','--raw','--','README.md'),other);
 assert.equal(readFileSync(join(root,'README.md'),'utf8'),'another writer\n');
});

test('staged move retires both old source and new addition, preserves other staging, and replays without a commit',t=>{
 const {root,git,plan}=fixture(t);
 const unselected=()=>git('diff','--cached','--no-renames','--raw','--','README.md','source/legacy/unselected.md','lib/legacy/unselected.md');
 const before=unselected();
 const preview=retireTrackedLegacyCapabilities({plan});assert.deepEqual(preview.counts,{eligible:1});assert.ok(existsSync(join(root,'lib/legacy/a.md')));
 const applied=retireTrackedLegacyCapabilities({plan,apply:true});assert.deepEqual(applied.counts,{removed:1});assert.equal(applied.workingLegacyRoot,'lib/legacy');
 const landed=commitTrackedLegacyRetirement({result:applied});assert.equal(landed.state,'committed');assert.equal(landed.retiredFiles,1);
 assert.equal(git('ls-tree','HEAD','--','source/legacy/a.md','lib/legacy/a.md'),'');
 assert.equal(git('ls-files','--stage','--','source/legacy/a.md','lib/legacy/a.md'),'');
 assert.equal(unselected(),before);assert.equal(readFileSync(join(root,'lib/legacy/unselected.md'),'utf8'),'keep\n');
 const head=git('rev-parse','HEAD'),index=readFileSync(join(root,'.git/index'));
 const replay=retireTrackedLegacyCapabilities({plan,apply:true});assert.deepEqual(replay.counts,{absent:1});
 assert.equal(commitTrackedLegacyRetirement({result:replay}).state,'already-landed');assert.equal(git('rev-parse','HEAD'),head);assert.deepEqual(readFileSync(join(root,'.git/index')),index);
});

for(const defect of ['changed-index','changed-working','old-recreated','old-indexed','linked-working-parent']) {
 test('staged move refuses '+defect+' before deletion',t=>{
  const {root,git,plan}=fixture(t);
  if(defect==='changed-index'){writeFileSync(join(root,'lib/legacy/a.md'),'foreign staged data');git('add','lib/legacy/a.md');}
  if(defect==='changed-working')writeFileSync(join(root,'lib/legacy/a.md'),'foreign working data');
  if(defect==='old-recreated'){mkdirSync(join(root,'source/legacy'),{recursive:true});writeFileSync(join(root,'source/legacy/a.md'),'restored');}
  if(defect==='old-indexed')git('reset','--','source/legacy/a.md');
  if(defect==='linked-working-parent'){renameSync(join(root,'lib/legacy'),join(root,'holding'));symlinkSync('../holding',join(root,'lib/legacy'));}
  const index=readFileSync(join(root,'.git/index')),body=readFileSync(join(root,'lib/legacy/a.md'));
  const result=retireTrackedLegacyCapabilities({plan,apply:true});assert.deepEqual(result.counts,{held:1});
  assert.deepEqual(readFileSync(join(root,'lib/legacy/a.md')),body);assert.deepEqual(readFileSync(join(root,'.git/index')),index);
 });
}

for(const defect of ['changed-index','recreated-working']) {
 test('commit rechecks '+defect+' and leaves the foreign edit intact',t=>{
  const {root,git,plan}=fixture(t),head=git('rev-parse','HEAD');
  const result=retireTrackedLegacyCapabilities({plan,apply:true});
  writeFileSync(join(root,'lib/legacy/a.md'),'foreign after apply');
  if(defect==='changed-index'){git('add','lib/legacy/a.md');unlinkSync(join(root,'lib/legacy/a.md'));}
  const index=readFileSync(join(root,'.git/index'));
  assert.throws(()=>commitTrackedLegacyRetirement({result}),/moved (index changed|source restored)/u);
  assert.equal(git('rev-parse','HEAD'),head);assert.deepEqual(readFileSync(join(root,'.git/index')),index);
  if(defect==='recreated-working')assert.equal(readFileSync(join(root,'lib/legacy/a.md'),'utf8'),'foreign after apply');
 });
}

test('unsafe or overlapping working roots refuse before source effects',t=>{
 const {root,plan}=fixture(t);
 for(const workingLegacyRoot of ['../legacy','/tmp/legacy','source/legacy','source/legacy/inside/legacy','lib/.git/legacy'])
  assert.throws(()=>retireTrackedLegacyCapabilities({plan:{...plan,workingLegacyRoot},apply:true}),/working legacy root/u);
 assert.ok(existsSync(join(root,'lib/legacy/a.md')));
});

test('batch retains the mapping and refuses different local cuts',t=>{
 const {plan}=fixture(t),args={id:'move',repositoryRoot:plan.repositoryRoot,receivingPath:'received.json',
  plans:[{path:'one.json',bytes:Buffer.from(JSON.stringify(plan))}]};
 const combined=composeTrackedLegacyRetirementBatch(args);
 assert.equal(combined.plan.workingLegacyRoot,plan.workingLegacyRoot);assert.equal(combined.receiving.source.workingLegacyRoot,plan.workingLegacyRoot);
 const other={...plan,workingLegacyRoot:'another/legacy',capabilities:[{...plan.capabilities[0],id:'other',sourcePaths:['unselected.md']}]};
 assert.throws(()=>composeTrackedLegacyRetirementBatch({...args,plans:[...args.plans,{path:'two.json',bytes:Buffer.from(JSON.stringify(other))}]}),/different source cuts/u);
});

