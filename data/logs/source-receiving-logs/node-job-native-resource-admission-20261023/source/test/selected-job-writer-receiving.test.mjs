import assert from 'node:assert/strict';
import test from 'node:test';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,rmSync,symlinkSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {receiveNodeJobWriters,nativeJobWriterPorts} from '../src/selected-job-writer-receiving.mjs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const hash=b=>createHash('sha256').update(b).digest('hex');
const fileHash=p=>hash(readFileSync(p));
const row=argv=>[argv[0],argv,false,0,0,0,0,0,0,0];
const tools=Object.fromEntries(['systemctl','busctl'].map(n=>[n,{path:'/usr/bin/'+n,sha256:fileHash('/usr/bin/'+n)}]));
function fixture(ids=['one']){
 const root=mkdtempSync(join(tmpdir(),'job-writer-'));
 mkdirSync(join(root,'deploy/jobs'),{recursive:true});mkdirSync(join(root,'src'));mkdirSync(join(root,'scripts'));mkdirSync(join(root,'lib'));mkdirSync(join(root,'state/jobs'),{recursive:true});
 writeFileSync(join(root,'package.json'),JSON.stringify({name:'@red-cup-engineering/node-job-service',version:'0.1.3-dev.0',type:'module',exports:{'.':'./src/node-job.mjs'}}));
 for(const p of ['src/node-job.mjs','scripts/record-node-job-run.mjs','consumer.mjs'])writeFileSync(join(root,p),'export {};\n');
 writeFileSync(join(root,'instance.json'),'{}');writeFileSync(join(root,'node'),'fixture node',{mode:0o700});
 const declarations=ids.map(id=>{const source=join(root,'deploy/jobs',id+'.json');writeFileSync(source,JSON.stringify({id,summary:id,directory:'lib',node:['run.mjs'],maxSeconds:60}));return {id,source,sha256:fileHash(source)};});
 const config={runtimeRoot:root,jobsDirectory:'deploy/jobs',stateRoot:join(root,'state'),unitPrefix:'fixture',artifact:root};
 const input={configuration:config,sourceInstance:{path:join(root,'instance.json'),sha256:fileHash(join(root,'instance.json'))},consumer:{realpath:join(root,'consumer.mjs'),sha256:fileHash(join(root,'consumer.mjs'))},
  selectedProducer:{packageRoot:root,version:'0.1.3-dev.0',entry:join(root,'src/node-job.mjs'),entrySHA256:fileHash(join(root,'src/node-job.mjs')),recorder:join(root,'scripts/record-node-job-run.mjs'),recorderSHA256:fileHash(join(root,'scripts/record-node-job-run.mjs'))},
  node:{path:join(root,'node'),sha256:fileHash(join(root,'node'))},nativeTools:tools,declarations};
 let calls=0;
 const unitFor=id=>({Id:'fixture-job-'+id+'.service',LoadState:'loaded',ActiveState:'inactive',SubState:'dead',Job:'',MainPID:'0',ControlPID:'0',InvocationID:'a'.repeat(32),ControlGroup:'',Result:'success',ExecMainPID:'0',ExecMainStartTimestampMonotonic:'0',ExecMainCode:'0',ExecMainStatus:'0',Transient:'yes',WorkingDirectory:join(root,'lib'),DropInPaths:''});
 const native={boot:()=> 'boot-fixture',unit:unit=>{calls++;return unitFor(unit.slice('fixture-job-'.length,-8));},
  execution:unit=>{const id=unit.slice('fixture-job-'.length,-8),receipt=join(root,'state/jobs',id+'.json');return {start:[row([input.node.path,'run.mjs'])],stopPost:[row([input.node.path,input.selectedProducer.recorder,receipt])],environment:['NODE_JOB_ID='+id,'NODE_JOB_UNIT='+unit,'NODE_JOB_RELEASE='+root,'NODE_JOB_STARTED_AT=2026-10-23T00:00:00Z','NODE_JOB_DEMAND='+receipt.slice(0,-5)+'.demand.json']};},
  process:pid=>({pid,birth:'123',argv:[input.node.path,'run.mjs'],exe:input.node.path,cwd:join(root,'lib'),cgroup:'0::/fixture'}),
  cohort:group=>({path:group,populated:false})};
 return {root,input,native,unitFor,calls:()=>calls,done:()=>rmSync(root,{recursive:true,force:true})};
}
function runFixture(fn,ids){const f=fixture(ids);try{return fn(f);}finally{f.done();}}
const receipt=(f,id='one',extra={})=>{const value={kind:'node-job-run.v1',job:id,unit:'fixture-job-'+id+'.service',release:f.root,startedAt:'2026-10-23T00:00:00Z',endedAt:'2026-10-23T00:01:00Z',ok:true,result:'success',exit:{code:'exited',status:'0'},tail:['PRIVATE-TAIL'],...extra};writeFileSync(join(f.root,'state/jobs',id+'.json'),JSON.stringify(value),{mode:0o600});};

test('all16 exact fixture declarations are observed without any state publication',()=>runFixture(f=>{
 const r=receiveNodeJobWriters(f.input,{native:f.native});assert.equal(r.jobs.length,16);assert.equal(f.calls(),32);assert.equal(r.complete,true);assert.ok(r.jobs.every(j=>j.current.currentWriter===false&&j.history.lastRecordedOutcome.state==='absent'));assert.equal(r.futureAdmissionFenceClaimed,false);assert.equal(r.historicalEffectsSettled,false);
},Array.from({length:16},(_,i)=>'job-'+i)));
test('a collected/not-found unit has no current writer and no invented successful history',()=>runFixture(f=>{
 f.native.unit=()=>({...f.unitFor('one'),LoadState:'not-found',InvocationID:'',Result:''});f.native.execution=()=>{throw Error('must not inspect absent service properties');};
 const j=receiveNodeJobWriters(f.input,{native:f.native}).jobs[0];assert.equal(j.current.state,'absent');assert.equal(j.current.currentWriter,false);assert.equal(j.history.lastRecordedOutcome.outcome,undefined);
}));
test('queued native job remains separate from completed old receipt',()=>runFixture(f=>{
 receipt(f);f.native.unit=()=>({...f.unitFor('one'),Job:'123'});const j=receiveNodeJobWriters(f.input,{native:f.native}).jobs[0];assert.equal(j.current.state,'queued');assert.equal(j.current.currentWriter,true);assert.equal(j.history.lastRecordedOutcome.outcome.reportedOk,true);
}));
test('live main and actual bound process/cohort remain running despite absent receipt',()=>runFixture(f=>{
 f.native.unit=()=>({...f.unitFor('one'),MainPID:'88',ExecMainPID:'88',ControlGroup:'/fixture',ActiveState:'active',SubState:'running'});f.native.cohort=path=>({path,populated:true});const j=receiveNodeJobWriters(f.input,{native:f.native}).jobs[0];assert.equal(j.current.state,'running');assert.equal(j.current.processes[0].birth,'123');assert.equal(j.history.lastRecordedOutcome.state,'absent');
}));
test('original finalizer/recorder control process is a current writer',()=>runFixture(f=>{
 f.native.unit=()=>({...f.unitFor('one'),ControlPID:'99',ControlGroup:'/fixture',ActiveState:'deactivating',SubState:'stop-post'});f.native.process=pid=>({pid,birth:'123',argv:[f.input.node.path,f.input.selectedProducer.recorder,join(f.root,'state/jobs/one.json')],exe:f.input.node.path,cwd:join(f.root,'lib'),cgroup:'0::/fixture'});const j=receiveNodeJobWriters(f.input,{native:f.native}).jobs[0];assert.equal(j.current.state,'running');assert.equal(j.current.unit.ControlPID,'99');
}));
test('populated descendants remain current writer even with both native PIDs zero',()=>runFixture(f=>{
 f.native.unit=()=>({...f.unitFor('one'),ControlGroup:'/fixture'});f.native.cohort=path=>({path,populated:true});assert.equal(receiveNodeJobWriters(f.input,{native:f.native}).jobs[0].current.currentWriter,true);
}));
test('changed native observation remains unknown',()=>runFixture(f=>{
 let n=0;f.native.unit=()=>({...f.unitFor('one'),InvocationID: (++n===1?'a':'b').repeat(32)});const r=receiveNodeJobWriters(f.input,{native:f.native});assert.equal(r.complete,false);assert.equal(r.jobs[0].current.currentWriter,null);
}));
test('wrong actual executable or command remains native provenance unknown',()=>runFixture(f=>{
 f.native.unit=()=>({...f.unitFor('one'),MainPID:'88',ControlGroup:'/fixture',ActiveState:'active',SubState:'running'});f.native.process=pid=>({pid,birth:'123',argv:['secret-unrelated'],exe:'/other',cwd:join(f.root,'lib'),cgroup:'0::/fixture'});const r=receiveNodeJobWriters(f.input,{native:f.native});assert.equal(r.jobs[0].current.state,'unknown');assert.ok(!JSON.stringify(r).includes('secret-unrelated'));
}));
for(const [name,write]of [
 ['malformed',f=>writeFileSync(join(f.root,'state/jobs/one.json'),'not-json',{mode:0o600})],
 ['oversized',f=>writeFileSync(join(f.root,'state/jobs/one.json'),'x'.repeat(65537),{mode:0o600})],
 ['redirected',f=>symlinkSync('/proc/self/environ',join(f.root,'state/jobs/one.json'))],
 ['partial',f=>{writeFileSync(join(f.root,'state/jobs/one.json.part'),'PRIVATE-PART',{mode:0o600});writeFileSync(join(f.root,'state/jobs/one.demand.json.part'),'PRIVATE-DEMAND-PART',{mode:0o600});}]
])test('historical '+name+' custody does not create a current native writer',()=>runFixture(f=>{
 write(f);const r=receiveNodeJobWriters(f.input,{native:f.native}),j=r.jobs[0];assert.equal(r.complete,true);assert.equal(j.current.currentWriter,false);assert.equal(j.current.state,'inactive');assert.ok(!JSON.stringify(r).includes('PRIVATE-'));if(name!=='partial')assert.equal(j.history.lastRecordedOutcome.state,'unknown');else{assert.equal(j.history.receiptPart.state,'retained');assert.equal(j.history.demandPart.state,'retained');}
}));
test('SIGTERM with service success is retained as interrupted without customer fulfillment',()=>runFixture(f=>{
 receipt(f,'one',{ok:false,exit:{code:'killed',status:'TERM'}});const j=receiveNodeJobWriters(f.input,{native:f.native}).jobs[0];assert.equal(j.history.lastRecordedOutcome.outcome.interruptedSuccessRefused,true);assert.equal(j.history.lastRecordedOutcome.outcome.reportedOk,false);assert.equal(j.history.lastRecordedOutcome.outcome.externalEffectsSettled,false);assert.ok(!JSON.stringify(j).includes('PRIVATE-TAIL'));
}));
test('normal accepted nonzero success remains the original recorded outcome',()=>runFixture(f=>{
 receipt(f,'one',{exit:{code:'exited',status:'77'}});const h=receiveNodeJobWriters(f.input,{native:f.native}).jobs[0].history.lastRecordedOutcome;assert.equal(h.outcome.reportedOk,true);assert.equal(h.outcome.exit.status,'77');assert.equal(h.outcome.interruptedSuccessRefused,false);
}));
for(const [name,mutate]of [
 ['omitted declaration',f=>{f.input.declarations=[];}],
 ['extra declaration',f=>{writeFileSync(join(f.root,'deploy/jobs/two.json'),JSON.stringify({id:'two',summary:'two',directory:'lib',node:['run.mjs']}));}],
 ['duplicate declaration',f=>{f.input.declarations.push(f.input.declarations[0]);}],
 ['changed producer',f=>{writeFileSync(f.input.selectedProducer.entry,'changed');}],
 ['changed recorder',f=>{writeFileSync(f.input.selectedProducer.recorder,'changed');}],
 ['changed node',f=>{writeFileSync(f.input.node.path,'changed');}],
 ['wrong producer version',f=>{f.input.selectedProducer.version='0.4.1-dev.27';}],
 ['wrong tool',f=>{f.input.nativeTools={...tools,systemctl:{...tools.systemctl,path:'/unselected/systemctl'}};}],
])test(name+' refuses before native observations or private receipt reads',()=>runFixture(f=>{
 mutate(f);assert.throws(()=>receiveNodeJobWriters(f.input,{native:f.native}));assert.equal(f.calls(),0);
}));
test('unavailable native evidence remains unknown and does not expose raw failure text',()=>runFixture(f=>{
 f.native.unit=()=>{throw Error('PRIVATE-NATIVE-STDERR');};const r=receiveNodeJobWriters(f.input,{native:f.native});assert.equal(r.complete,false);assert.equal(r.jobs[0].current.state,'unknown');assert.ok(!JSON.stringify(r).includes('PRIVATE-NATIVE-STDERR'));
}));
test('incompatible source-owned native recorder argv refuses current provenance only',()=>runFixture(f=>{
 receipt(f);const execution=f.native.execution;f.native.execution=u=>({...execution(u),stopPost:[row([f.input.node.path,'/wrong-recorder'])]});const j=receiveNodeJobWriters(f.input,{native:f.native}).jobs[0];assert.equal(j.current.state,'unknown');assert.equal(j.history.lastRecordedOutcome.outcome.reportedOk,true);
}));


for(const [name,change]of [
 ['private identifier in exit status',f=>receipt(f,'one',{exit:{code:'exited',status:'PRIVATE_EXIT_TOKEN'}})],
 ['private timestamp suffix',f=>receipt(f,'one',{startedAt:'2026-10-23T00:00:00Z_PRIVATE_TOKEN'})]
])test(name+' remains opaque historical uncertainty',()=>runFixture(f=>{
 change(f);const r=receiveNodeJobWriters(f.input,{native:f.native});assert.equal(r.jobs[0].history.lastRecordedOutcome.state,'unknown');assert.equal(r.jobs[0].current.currentWriter,false);assert.ok(!JSON.stringify(r).includes('PRIVATE_'));
}));
test('an unknown configuration member refuses before native activity',()=>runFixture(f=>{
 f.input.configuration.PRIVATE_VALUE='PRIVATE_SECRET';assert.throws(()=>receiveNodeJobWriters(f.input,{native:f.native}));assert.equal(f.calls(),0);
}));
test('private native environment content is not exposed as a run timestamp',()=>runFixture(f=>{
 const read=f.native.execution;f.native.execution=u=>{const x=read(u);x.environment=x.environment.map(v=>v.startsWith('NODE_JOB_STARTED_AT=')?'NODE_JOB_STARTED_AT=PRIVATE_ENV_SECRET':v);return x;};const r=receiveNodeJobWriters(f.input,{native:f.native});assert.equal(r.jobs[0].current.state,'unknown');assert.ok(!JSON.stringify(r).includes('PRIVATE_ENV_SECRET'));
}));
test('native own-process reader binds a stable birth despite changing process counters',()=>{
 const n=nativeJobWriterPorts({timeoutMs:1000,commandBytes:65536});const a=n.process(process.pid);for(let i=0;i<10000;i++)Math.sqrt(i);const b=n.process(process.pid);assert.equal(a.pid,process.pid);assert.match(a.birth,/^[0-9]+$/);assert.equal(a.birth,b.birth);assert.ok(a.argv.includes(process.execPath));
});
test('closed public CLI refuses a malformed private input without native commands or raw error data',()=>runFixture(f=>{
 const input=join(f.root,'private-input.json');writeFileSync(input,'{"PRIVATE_SECRET":true}',{mode:0o600});const cli=fileURLToPath(new URL('../scripts/receive-job-writers.mjs',import.meta.url));const r=spawnSync(process.execPath,[cli,input],{encoding:'utf8',timeout:3000});assert.equal(r.status,1);assert.equal(r.stderr,'');const value=JSON.parse(r.stdout);assert.equal(value.type,'SelectedNodeJobWriterReceivingRefused');assert.ok(!r.stdout.includes('PRIVATE_SECRET'));
}));

test('a contradictory old positive TERM record remains historical unknown without inventing a current writer',()=>runFixture(f=>{
 receipt(f,'one',{ok:true,exit:{code:'killed',status:'TERM'}});const j=receiveNodeJobWriters(f.input,{native:f.native}).jobs[0];assert.equal(j.current.currentWriter,false);assert.equal(j.history.lastRecordedOutcome.state,'unknown');assert.equal(j.history.lastRecordedOutcome.reason,'original-recorder-law-mismatch');
}));

test('retained nested exit extensions cannot leave the private historical carrier',()=>runFixture(f=>{
 receipt(f,'one',{exit:{code:'exited',status:'0',private:'PRIVATE_NESTED_SENTINEL'}});const r=receiveNodeJobWriters(f.input,{native:f.native});assert.deepEqual(r.jobs[0].history.lastRecordedOutcome.outcome.exit,{code:'exited',status:'0'});assert.ok(!JSON.stringify(r).includes('PRIVATE_NESTED_SENTINEL'));
}));
for(const property of ['Job','ControlGroup','InvocationID','SubState','MainPID','ControlPID','ExecMainPID','ExecMainStartTimestampMonotonic','Result','Transient'])test('missing native '+property+' cannot prove no current writer',()=>runFixture(f=>{
 f.native.unit=()=>{const u=f.unitFor('one');delete u[property];return u;};const r=receiveNodeJobWriters(f.input,{native:f.native});assert.equal(r.complete,false);assert.equal(r.jobs[0].current.currentWriter,null);
}));
for(const property of ['MainPID','ControlPID','ExecMainPID'])test('unsafe native '+property+' cannot fall through to zero',()=>runFixture(f=>{
 f.native.unit=()=>({...f.unitFor('one'),[property]:'9007199254740992'});assert.equal(receiveNodeJobWriters(f.input,{native:f.native}).jobs[0].current.state,'unknown');
}));
test('unreceived cgroup population cannot imply an empty cohort',()=>runFixture(f=>{
 f.native.unit=()=>({...f.unitFor('one'),ControlGroup:'/fixture'});f.native.cohort=path=>({path,populated:null});assert.equal(receiveNodeJobWriters(f.input,{native:f.native}).jobs[0].current.currentWriter,null);
}));

for(const property of ['SubState','Result','InvocationID','Job'])test('malformed native '+property+' cannot escape as public private payload',()=>runFixture(f=>{
 f.native.unit=()=>({...f.unitFor('one'),[property]:'PRIVATE_NATIVE_SENTINEL'});const r=receiveNodeJobWriters(f.input,{native:f.native});assert.equal(r.jobs[0].current.state,'unknown');assert.ok(!JSON.stringify(r).includes('PRIVATE_NATIVE_SENTINEL'));
}));
test('inconsistent service active/substate cannot attest an empty current writer',()=>runFixture(f=>{
 f.native.unit=()=>({...f.unitFor('one'),SubState:'running'});assert.equal(receiveNodeJobWriters(f.input,{native:f.native}).jobs[0].current.currentWriter,null);
}));
test('collected native response omitting service properties remains unknown',()=>runFixture(f=>{
 f.native.unit=()=>({Id:'fixture-job-one.service',LoadState:'not-found',ActiveState:'inactive',SubState:'dead',Job:'',InvocationID:'',ControlGroup:''});const r=receiveNodeJobWriters(f.input,{native:f.native});assert.equal(r.complete,false);assert.equal(r.jobs[0].current.currentWriter,null);
}));
