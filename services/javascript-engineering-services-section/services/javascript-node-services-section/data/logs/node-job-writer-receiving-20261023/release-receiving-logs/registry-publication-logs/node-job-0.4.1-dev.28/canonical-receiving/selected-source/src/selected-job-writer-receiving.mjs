/** Read only the writers named by an installed node-job selection. No job lifecycle effects. */
import {constants,openSync,closeSync,fstatSync,readSync,lstatSync,realpathSync,readdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {constants as osConstants} from 'node:os';
import {execFileSync} from 'node:child_process';
import {dirname,join,resolve,isAbsolute} from 'node:path';
import {readNodeJobDeclarations} from './node-job.mjs';

const fail=code=>{throw Object.assign(new Error(code),{code});};
const digest=b=>createHash('sha256').update(b).digest('hex');
const sha=/^[a-f0-9]{64}$/;
const id=/^[a-z0-9][a-z0-9-]*$/;
const instant=x=>typeof x==='string'&&x.length<=40&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(x)&&Number.isFinite(Date.parse(x));
const signalNames=new Set(Object.keys(osConstants.signals).map(n=>n.slice(3)));
const exitStatus=x=>x===null||(typeof x==='string'&&((/^\d{1,3}$/.test(x)&&Number(x)<=255)||signalNames.has(x)));
// Original selected native provider: systemd v255 service/state result tables.
const SERVICE_RESULTS=new Set(['success','resources','protocol','timeout','exit-code','signal','core-dump','watchdog','start-limit-hit','oom-kill','exec-condition']);
const SERVICE_STATES=Object.freeze(Object.fromEntries([
 ['inactive',['dead','dead-before-auto-restart','dead-resources-pinned']],
 ['failed',['failed','failed-before-auto-restart']],
 ['activating',['condition','start-pre','start','start-post','auto-restart','auto-restart-queued']],
 ['active',['running','exited']],['reloading',['reload','reload-signal','reload-notify']],
 ['deactivating',['stop','stop-watchdog','stop-sigterm','stop-sigkill','stop-post','final-watchdog','final-sigterm','final-sigkill']],
 ['maintenance',['cleaning']]
].flatMap(([active,states])=>states.map(state=>[state,active]))));
const TOOLS=Object.freeze({systemctl:'/usr/bin/systemctl',busctl:'/usr/bin/busctl'});
const PROPERTIES='Id,LoadState,ActiveState,SubState,Job,MainPID,ControlPID,InvocationID,ControlGroup,ExecMainPID,ExecMainStartTimestampMonotonic,ExecMainCode,ExecMainStatus,Result,Transient,WorkingDirectory,DropInPaths';
function regular(file,maxBytes,{owner=false}={}){
 let fd;
 try{
  fd=openSync(file,constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);
  const before=fstatSync(fd);
  if(!before.isFile()||(owner&&before.uid!==process.getuid())||before.size>maxBytes)fail('file-custody-unavailable');
  const chunks=[];let total=0;
  for(;;){const chunk=Buffer.allocUnsafe(Math.min(65536,maxBytes+1-total)),n=readSync(fd,chunk,0,chunk.length,null);if(!n)break;total+=n;if(total>maxBytes)fail('file-byte-budget');chunks.push(chunk.subarray(0,n));}
  const after=fstatSync(fd);
  if(before.dev!==after.dev||before.ino!==after.ino||before.size!==after.size||before.mtimeMs!==after.mtimeMs||before.ctimeMs!==after.ctimeMs)fail('file-changed');
  return {bytes:Buffer.concat(chunks,total),identity:{dev:before.dev,ino:before.ino,size:total,mode:before.mode&511,uid:before.uid}};
 }finally{if(fd!==undefined)closeSync(fd);}
}
function canonical(file){if(!isAbsolute(file)||resolve(file)!==file||realpathSync(file)!==file)fail('redirected-path');return file;}
function source(file,expected,maxBytes=256*1024*1024){
 if(typeof expected!=='string'||!sha.test(expected))fail('source-digest-required');
 canonical(file);let fd;
 try{
  fd=openSync(file,constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);const before=fstatSync(fd);
  if(!before.isFile()||before.size>maxBytes)fail('source-file-unavailable');
  const hash=createHash('sha256'),chunk=Buffer.allocUnsafe(65536);let total=0;
  for(;;){const n=readSync(fd,chunk,0,chunk.length,null);if(!n)break;total+=n;if(total>maxBytes)fail('source-byte-budget');hash.update(chunk.subarray(0,n));}
  const after=fstatSync(fd);
  if(before.dev!==after.dev||before.ino!==after.ino||before.size!==after.size||before.mtimeMs!==after.mtimeMs||before.ctimeMs!==after.ctimeMs||hash.digest('hex')!==expected)fail('source-changed');
  return {path:file,sha256:expected,bytes:total};
 }finally{if(fd!==undefined)closeSync(fd);}
}
function ownerPath(file,anchor){
 if(!isAbsolute(anchor)||resolve(anchor)!==anchor||!isAbsolute(file)||resolve(file)!==file||(file!==anchor&&!file.startsWith(anchor+'/')))fail('private-path-escape');
 // The selected existing legacy anchor is received without creating or changing it.
 const parts=anchor.split('/').filter(Boolean);let current='/';const received=[];
 for(const part of [...parts,...file.slice(anchor.length).split('/').filter(Boolean)]){
  current=join(current,part);const st=lstatSync(current);
  if(st.isSymbolicLink())fail('redirected-private-path');
  if(current===anchor&&(st.uid!==process.getuid()||!st.isDirectory()))fail('private-owner-unavailable');
  if(current!==file&&!st.isDirectory())fail('private-parent-unavailable');
  received.push({path:current,dev:st.dev,ino:st.ino,uid:st.uid,mode:st.mode});
 }
 return received;
}
function privateFile(file,anchor,maxBytes){
 try{
  const before=ownerPath(file,anchor);const held=regular(file,maxBytes,{owner:true}),after=ownerPath(file,anchor);
  if(JSON.stringify(before)!==JSON.stringify(after)||after.at(-1).dev!==held.identity.dev||after.at(-1).ino!==held.identity.ino)fail('file-changed');
  return {state:'retained',...held.identity,sha256:digest(held.bytes),bytes:held.bytes};
 }catch(error){return {state:error.code==='ENOENT'?'absent':'unknown',reason:error.code==='ENOENT'?'missing':publicFailure(error)};}
}
function publicFailure(error){return ['source-changed','file-changed','file-byte-budget','file-custody-unavailable','redirected-private-path','private-owner-unavailable','private-parent-unavailable','private-path-escape'].includes(error?.code)?error.code:'unavailable';}
function publicFile(held){const {bytes,...facts}=held;return facts;}
function factsOfReceipt(held,job,configuration){
 const facts=publicFile(held);
 if(held.state!=='retained')return facts;
 let value;try{value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(held.bytes));}catch{return {...facts,state:'unknown',reason:'malformed'};}
 if(value?.kind!=='node-job-run.v1'||value.job!==job.id||value.unit!==configuration.unitPrefix+'-job-'+job.id+'.service')return {...facts,state:'unknown',reason:'receipt-binding-mismatch'};
 const results=new Set([...SERVICE_RESULTS,'unknown']);
 if(!instant(value.startedAt)||!instant(value.endedAt)||!results.has(value.result)||typeof value.ok!=='boolean'
  ||typeof value.exit!=='object'||value.exit===null||!['exited','killed','dumped',null].includes(value.exit.code)
  ||!exitStatus(value.exit.status))return {...facts,state:'unknown',reason:'unreceived-receipt-shape'};
 if(value.ok!==(value.result==='success'&&value.exit.code==='exited'))return {...facts,state:'unknown',reason:'original-recorder-law-mismatch'};
 // No output tail, credentials, environment, demand payload or private principal data.
 return {...facts,outcome:{kind:value.kind,job:job.id,unit:value.unit,releaseMatches:value.release===(configuration.artifact??configuration.runtimeRoot),
  startedAt:value.startedAt,endedAt:value.endedAt,reportedOk:value.ok,result:value.result,exit:{code:value.exit.code,status:value.exit.status},
  interruptedSuccessRefused:value.result==='success'&&value.exit.code!=='exited',externalEffectsSettled:false}};
}
function boundedInt(n,min,max){if(!Number.isSafeInteger(n)||n<min||n>max)fail('invalid-allocation');return n;}
function admit(input){
 if(process.platform!=='linux')fail('linux-provider-required');
 const c=input?.configuration;
 if(!c||Object.keys(c).some(k=>!['runtimeRoot','jobsDirectory','stateRoot','unitPrefix','artifact'].includes(k))||!['runtimeRoot','stateRoot'].every(k=>typeof c[k]==='string'&&isAbsolute(c[k])&&resolve(c[k])===c[k])
  ||(c.artifact!==undefined&&(typeof c.artifact!=='string'||c.artifact.length<1||c.artifact.length>4096))
  ||typeof c.jobsDirectory!=='string'||isAbsolute(c.jobsDirectory)||resolve(c.runtimeRoot,c.jobsDirectory).indexOf(c.runtimeRoot+'/')!==0
  ||typeof c.unitPrefix!=='string'||!/^[a-z0-9][a-z0-9-]*$/.test(c.unitPrefix))fail('installed-selection-required');
 canonical(c.runtimeRoot);
 const instance=source(input.sourceInstance?.path,input.sourceInstance?.sha256,131072);
 const consumer=source(input.consumer?.realpath,input.consumer?.sha256,1048576);
 if(!Array.isArray(input.declarations)||input.declarations.length<1||input.declarations.length>64)fail('finite-declarations-required');
 const expected=new Map();
 const declarationsDirectory=canonical(resolve(c.runtimeRoot,c.jobsDirectory));
 for(const row of input.declarations){if(!id.test(row?.id)||expected.has(row.id)||row.source!==join(declarationsDirectory,row.id+'.json'))fail('declaration-selection-mismatch');expected.set(row.id,source(row.source,row.sha256,65536));}
 const names=readdirSync(declarationsDirectory).filter(n=>n.endsWith('.json')).sort();
 if(JSON.stringify(names)!==JSON.stringify([...expected.keys()].sort().map(n=>n+'.json')))fail('incomplete-declaration-selection');
 const jobs=readNodeJobDeclarations(declarationsDirectory);
 if(jobs.length!==expected.size||jobs.some(j=>!expected.has(j.id)))fail('declaration-reader-mismatch');
 const p=input.selectedProducer;
 if(typeof p?.packageRoot!=='string'||p.entry!==join(p.packageRoot,'src/node-job.mjs')||p.recorder!==join(p.packageRoot,'scripts/record-node-job-run.mjs'))fail('producer-binding-required');
 const producerEntry=source(p.entry,p.entrySHA256,1048576),recorder=source(p.recorder,p.recorderSHA256,1048576);
 if(realpathSync(createRequire(consumer.path).resolve('@red-cup-engineering/node-job-service'))!==producerEntry.path)fail('producer-resolution-changed');
 const manifest=JSON.parse(regular(join(canonical(p.packageRoot),'package.json'),65536).bytes);
 if(manifest.name!=='@red-cup-engineering/node-job-service'||manifest.version!==p.version)fail('producer-version-changed');
 const node=source(input.node?.path,input.node?.sha256);
 const tools={};for(const [key,path]of Object.entries(TOOLS)){
  if(input.nativeTools?.[key]?.path!==path)fail('native-provider-required');
  tools[key]=source(path,input.nativeTools[key].sha256,16*1048576);
 }
 const limits={timeoutMs:boundedInt(input.limits?.timeoutMs??30000,1,60000),commandBytes:boundedInt(input.limits?.commandBytes??65536,1024,1048576),receiptBytes:boundedInt(input.limits?.receiptBytes??65536,1,1048576)};
 return {configuration:c,jobs,expected,instance,consumer,producer:{version:p.version,entry:producerEntry,recorder},node,tools,limits};
}
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function managerPath(unit){return '/org/freedesktop/systemd1/unit/'+[...unit].map(c=>/[A-Za-z0-9]/.test(c)?c:'_'+c.charCodeAt(0).toString(16).padStart(2,'0')).join('');}
export function nativeJobWriterPorts(limits){
 boundedInt(limits?.timeoutMs,1,60000);boundedInt(limits?.commandBytes,1024,1048576);
 const deadline=performance.now()+limits.timeoutMs;
 const command=(path,args)=>{const timeout=Math.floor(deadline-performance.now());if(timeout<1)fail('native-budget-exhausted');try{return execFileSync(path,args,{encoding:'utf8',timeout,maxBuffer:limits.commandBytes,stdio:['ignore','pipe','pipe'],env:{...process.env,LC_ALL:'C',SYSTEMD_COLORS:'0'}});}catch{fail('native-command-unavailable');}};
 const typed=(unit,property,type)=>{
  let result;try{result=JSON.parse(command(TOOLS.busctl,['--user','--json=short','get-property','org.freedesktop.systemd1',managerPath(unit),'org.freedesktop.systemd1.Service',property]));}catch{fail('native-typed-property-unavailable');}
  if(result.type!==type||!Array.isArray(result.data))fail('native-typed-property-unavailable');return result.data;
 };
 return {
  boot:()=>regular('/proc/sys/kernel/random/boot_id',128).bytes.toString('utf8').trim(),
  unit:unit=>{
   const output=command(TOOLS.systemctl,['--user','show',unit,'--no-pager','--property='+PROPERTIES]);const result={};
   for(const line of output.trim().split('\n')){const i=line.indexOf('=');if(i<1||Object.hasOwn(result,line.slice(0,i)))fail('native-unit-shape');result[line.slice(0,i)]=line.slice(i+1);}
   return result;
  },
  execution:unit=>({start:typed(unit,'ExecStart','a(sasbttttuii)'),stopPost:typed(unit,'ExecStopPost','a(sasbttttuii)'),environment:typed(unit,'Environment','as')}),
  process:pid=>{
   const stat=()=>regular('/proc/'+pid+'/stat',65536).bytes.toString('utf8');
   try{const before=stat(),tail=before.slice(before.lastIndexOf(')')+2).split(' ');const result={pid,birth:tail[19],argv:regular('/proc/'+pid+'/cmdline',65536).bytes.toString('utf8').split('\0').filter(Boolean),exe:realpathSync('/proc/'+pid+'/exe'),cwd:realpathSync('/proc/'+pid+'/cwd'),cgroup:regular('/proc/'+pid+'/cgroup',65536).bytes.toString('utf8').trim()};const after=stat(),afterTail=after.slice(after.lastIndexOf(')')+2).split(' ');if(afterTail[19]!==result.birth)fail('process-changed');return result;}catch(error){if(error.code==='ENOENT'||error.code==='ESRCH')return {pid,absent:true};throw error;}
  },
  cohort:group=>{
   if(!/^\/[A-Za-z0-9_.@:/-]+$/.test(group)||group.split('/').includes('..'))fail('native-cgroup-shape');
   try{const text=regular('/sys/fs/cgroup'+group+'/cgroup.events',4096).bytes.toString('utf8');const m=/^populated ([01])$/m.exec(text);if(!m)fail('native-cgroup-shape');return {path:group,populated:m[1]==='1'};}catch(error){if(error.code==='ENOENT')return {path:group,populated:false,absent:true};throw error;}
  }
 };
}
function executionOf(value){
 if(!value||!Array.isArray(value.start)||!Array.isArray(value.stopPost)||!Array.isArray(value.environment))fail('native-execution-shape');
 const row=r=>{if(!Array.isArray(r)||r.length!==10||typeof r[0]!=='string'||!Array.isArray(r[1])||r[1].some(x=>typeof x!=='string')||typeof r[2]!=='boolean'||r[0]!==r[1][0]||r.slice(3).some(x=>!Number.isSafeInteger(x)||x<0))fail('native-execution-shape');return {path:r[0],argv:r[1],ignoreFailure:r[2],pid:r[7],code:r[8],status:r[9],started:r[4],ended:r[6]};};
 const environment={};
 for(const entry of value.environment){if(typeof entry!=='string')fail('native-environment-shape');const i=entry.indexOf('=');const key=entry.slice(0,i);if(['NODE_JOB_ID','NODE_JOB_UNIT','NODE_JOB_RELEASE','NODE_JOB_STARTED_AT','NODE_JOB_DEMAND'].includes(key)){if(Object.hasOwn(environment,key))fail('native-environment-shape');environment[key]=entry.slice(i+1);}}
 return {start:value.start.map(row),stopPost:value.stopPost.map(row),environment};
}
function positivePid(value){return typeof value==='string'&&/^[1-9]\d*$/.test(value)&&Number.isSafeInteger(Number(value))?Number(value):0;}
function nativeObservation(unit,job,selection,native,boot){
 const first=native.unit(unit);
 const decimal=(v,max=0xffffffff)=>typeof v==='string'&&/^(?:0|[1-9]\d*)$/.test(v)&&Number.isSafeInteger(Number(v))&&Number(v)<=max;
 if(!first||Object.keys(first).length!==PROPERTIES.split(',').length||PROPERTIES.split(',').some(k=>typeof first[k]!=='string')
  ||first.Id!==unit||!['loaded','not-found'].includes(first.LoadState)||!Object.values(SERVICE_STATES).includes(first.ActiveState)
  ||!decimal(first.MainPID)||!decimal(first.ControlPID)||!decimal(first.ExecMainPID)||!decimal(first.ExecMainCode,6)||!decimal(first.ExecMainStatus,255)
  ||!decimal(first.ExecMainStartTimestampMonotonic,Number.MAX_SAFE_INTEGER)||!(first.Job===''||decimal(first.Job))
  ||!(first.InvocationID===''||/^[a-f0-9]{32}$/.test(first.InvocationID))||SERVICE_STATES[first.SubState]!==first.ActiveState
  ||!(SERVICE_RESULTS.has(first.Result)||(first.LoadState==='not-found'&&first.Result===''))
  ||!['yes','no'].includes(first.Transient)||!(first.ControlGroup===''||(/^\/[A-Za-z0-9_.@:/-]+$/.test(first.ControlGroup)&&!first.ControlGroup.split('/').includes('..'))))fail('native-unit-binding');
 const found=first.LoadState==='loaded';let execution,provenance='not-observed';
 if(found&&(first.Transient!=='yes'||(first.DropInPaths??'')!==''))fail('native-transient-source-unreceived');
 if(found){
  execution=executionOf(native.execution(unit));
  const expand=s=>s.replaceAll('{release}',selection.configuration.runtimeRoot);
  const start=[selection.node.path,...job.node.map(expand)],receipt=join(selection.configuration.stateRoot,'jobs',job.id+'.json');
  const stop=[[selection.node.path,...(job.finally??[]).map(expand)],[selection.node.path,selection.producer.recorder.path,receipt]];
  const expectedPost=job.finally===undefined?stop.slice(1):stop;
  if(execution.start.length!==1||execution.start[0].ignoreFailure||!same(execution.start[0].argv,start)
   ||!same(execution.stopPost.map(x=>x.argv),expectedPost)||execution.stopPost.some(x=>x.ignoreFailure)
   ||first.WorkingDirectory!==resolve(selection.configuration.runtimeRoot,job.directory)
   ||execution.environment.NODE_JOB_ID!==job.id||execution.environment.NODE_JOB_UNIT!==unit
   ||execution.environment.NODE_JOB_RELEASE!==(selection.configuration.artifact??'')
   ||execution.environment.NODE_JOB_DEMAND!==receipt.slice(0,-5)+'.demand.json'||!instant(execution.environment.NODE_JOB_STARTED_AT))fail('native-programme-mismatch');
  provenance='selected-producer-command-and-recorder';
 }
 const pids=[...new Set([positivePid(first.MainPID),positivePid(first.ControlPID)].filter(Boolean))];
 const processes=pids.map(pid=>native.process(pid));
 if(processes.some((p,i)=>p.absent||p.pid!==pids[i]))fail('native-process-disappeared');
 if(processes.length>0&&first.InvocationID==='')fail('native-process-binding');
 const cohort=first.ControlGroup?native.cohort(first.ControlGroup):null;
 if(cohort&&(cohort.path!==first.ControlGroup||typeof cohort.populated!=='boolean'||(cohort.absent===true&&cohort.populated!==false)))fail('native-cgroup-shape');
 if(first.ControlGroup&&!cohort)fail('native-cgroup-shape');
 for(const p of processes){
  if(typeof p.birth!=='string'||!/^\d+$/.test(p.birth)||!Array.isArray(p.argv)||typeof p.cgroup!=='string'||!first.ControlGroup||!p.cgroup.split('\n').some(line=>line==='0::'+first.ControlGroup))fail('native-process-binding');
 }
 for(const p of processes){
  const allowed=p.pid===positivePid(first.MainPID)?execution.start:execution.stopPost;
  if(p.exe!==selection.node.path||p.cwd!==realpathSync(resolve(selection.configuration.runtimeRoot,job.directory))||!allowed.some(r=>same(r.argv,p.argv)))fail('native-process-programme-mismatch');
 }
 const second=native.unit(unit);
 if(!same(first,second)||native.boot()!==boot)fail('native-observation-changed');
 const queued=Boolean(first.Job&&first.Job!=='0');
 const nativeRunning=!['inactive','failed'].includes(first.ActiveState);
 const currentWriter=processes.length>0||cohort?.populated===true||nativeRunning;
 // An absent unit has no current writer only if it also has no native job,
 // main/control or cgroup evidence. It never acquires a successful old outcome.
 const knownEmpty=!queued&&!currentWriter;
 return {state:queued?'queued':currentWriter?'running':found?'inactive':'absent',currentWriter:knownEmpty?false:true,provenance,
  unit:{Id:unit,LoadState:first.LoadState,ActiveState:first.ActiveState,SubState:first.SubState,Job:first.Job??'',MainPID:first.MainPID,ControlPID:first.ControlPID,InvocationID:first.InvocationID??'',ControlGroup:first.ControlGroup??'',Result:first.Result??'',ExecMainPID:first.ExecMainPID??'',ExecMainCode:first.ExecMainCode??'',ExecMainStatus:first.ExecMainStatus??''},
  processes:processes.map(p=>({pid:p.pid,birth:p.birth,argvSHA256:digest(Buffer.from(JSON.stringify(p.argv))),exe:p.exe,cwd:p.cwd,cgroup:p.cgroup})),cohort,
  ...(execution===undefined?{}:{execution:{start:execution.start.map(({argv,...r})=>({...r,argvSHA256:digest(Buffer.from(JSON.stringify(argv)))})),stopPost:execution.stopPost.map(({argv,...r})=>({...r,argvSHA256:digest(Buffer.from(JSON.stringify(argv)))})),startedAt:execution.environment.NODE_JOB_STARTED_AT??null}}),
  nativeTerminalCustomerOutcomeClaimed:false};
}
/** Test injection is an in-process source assay only; the public CLI always constructs native ports. */
export function receiveNodeJobWriters(input,{native}={}){
 const selection=admit(input),port=native??nativeJobWriterPorts(selection.limits),startedAt=new Date().toISOString(),boot=port.boot();
 if(typeof boot!=='string'||!boot)fail('native-boot-required');
 const jobs=[];
 for(const job of selection.jobs){
  const unit=selection.configuration.unitPrefix+'-job-'+job.id+'.service';let current;
  try{current=nativeObservation(unit,job,selection,port,boot);}catch(error){const allowed=new Set(['native-unit-binding','native-transient-source-unreceived','native-execution-shape','native-environment-shape','native-programme-mismatch','native-process-disappeared','native-process-binding','native-process-programme-mismatch','native-observation-changed','native-command-unavailable','native-typed-property-unavailable','native-unit-shape','native-cgroup-shape','native-budget-exhausted']);current={state:'unknown',currentWriter:null,reason:allowed.has(error.code)?error.code:'native-current-writer-unreceived'};}
  const receipt=join(selection.configuration.stateRoot,'jobs',job.id+'.json'),demand=receipt.slice(0,-5)+'.demand.json';
  const held=privateFile(receipt,selection.configuration.stateRoot,selection.limits.receiptBytes);
  const history={lastRecordedOutcome:factsOfReceipt(held,job,selection.configuration),demand:publicFile(privateFile(demand,selection.configuration.stateRoot,selection.limits.receiptBytes)),
   receiptPart:publicFile(privateFile(receipt+'.part',selection.configuration.stateRoot,selection.limits.receiptBytes)),
   demandPart:publicFile(privateFile(demand+'.part',selection.configuration.stateRoot,selection.limits.receiptBytes))};
  const after=privateFile(receipt,selection.configuration.stateRoot,selection.limits.receiptBytes);
  if(!same(publicFile(held),publicFile(after)))history.lastRecordedOutcome={state:'unknown',reason:'receipt-changed'};
  jobs.push({id:job.id,unit,current,history});
 }
 // Re-receive the admitted source selection after all native/private observations.
 for(const row of selection.expected.values())source(row.path,row.sha256,65536);
 source(selection.producer.entry.path,selection.producer.entry.sha256);source(selection.producer.recorder.path,selection.producer.recorder.sha256);
 source(selection.instance.path,selection.instance.sha256);source(selection.consumer.path,selection.consumer.sha256);source(selection.node.path,selection.node.sha256);for(const t of Object.values(selection.tools))source(t.path,t.sha256);
 return {type:'SelectedNodeJobWriterReceiving',version:1,startedAt,endedAt:new Date().toISOString(),boot,uid:process.getuid(),observerPid:process.pid,readerNodeVersion:process.version,
  observer:'@red-cup-engineering/node-job-service/selected-job-writer-receiving',selectedProducer:selection.producer,node:selection.node,
  configuration:selection.configuration,sourceInstance:selection.instance,consumer:selection.consumer,declarations:[...selection.expected.values()],nativeTools:selection.tools,limits:selection.limits,
  complete:jobs.every(j=>j.current.state!=='unknown'),jobs,futureAdmissionFenceClaimed:false,historicalEffectsSettled:false,machineEffects:false};
}
