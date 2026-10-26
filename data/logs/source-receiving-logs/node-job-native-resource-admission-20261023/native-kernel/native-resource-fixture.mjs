import assert from "node:assert/strict";
import fs from "node:fs";
import { join } from "node:path";
import { promisify } from "node:util";
import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { setTimeout as delay } from "node:timers/promises";
import { runNodeJob } from "/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/data/logs/source-receiving-logs/node-job-native-resource-admission-20261023/source/src/node-job.mjs";
const root="/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/data/logs/source-receiving-logs/node-job-native-resource-admission-20261023/native-kernel",prefix="nodejob-resource-inert-bcf-20261023",unit=prefix+"-job-inert.service";
const execute=promisify(execFile),node=process.execPath;
const limits={memoryMaxBytes:64*1048576,memoryHighBytes:48*1048576,memorySwapMaxBytes:0,tasksMax:12,cpuQuotaPercent:50,memoryReserveBytes:32*1048576};
const configuration={runtimeRoot:root,jobsDirectory:"jobs",stateRoot:join(root,"state"),unitPrefix:prefix,artifact:root};
const properties=["LoadState","ActiveState","SubState","UnitFileState","FragmentPath","MainPID","ControlPID","Job","InvocationID","Result","ExecMainCode","ExecMainStatus","MemoryMax","MemoryHigh","MemorySwapMax","TasksMax","CPUQuotaPerSecUSec","RuntimeMaxUSec","ControlGroup"];
async function shown(){
 const {stdout}=await execute("systemctl",["--user","show",unit,...properties.map(p=>"--property="+p)],{encoding:"utf8",timeout:3000,maxBuffer:65536});
 const values=Object.fromEntries(stdout.trim().split("\n").map(line=>{const at=line.indexOf("=");return[line.slice(0,at),line.slice(at+1)];}));
 return {at:new Date().toISOString(),raw:stdout,values};
}
const save=(name,value)=>fs.writeFileSync(join(root,name),JSON.stringify(value,null,2)+"\n",{flag:"wx"});
const sha=bytes=>createHash("sha256").update(bytes).digest("hex");
const job={id:"inert",summary:"Native bounded resource receiving fixture",directory:".",
 node:["--jitless","--max-old-space-size=16","--max-semi-space-size=2","inert.mjs"],maxSeconds:10,demand:true,
 environment:{NODE_JOB_FLEET:"",NODE_JOB_NODE_ID:"bcf-resource-fixture",NODE_OPTIONS:"--jitless --max-old-space-size=16 --max-semi-space-size=2"},
 resources:limits};
const receipt=join(root,"state/jobs/inert.json"),demand=join(root,"state/jobs/inert.demand.json");
const writeJob=value=>fs.writeFileSync(join(root,"jobs/inert.json"),JSON.stringify(value,null,2)+"\n");
const invoke=()=>runNodeJob({configuration,job:"inert",fleet:null,home:root,node});
async function terminal(){
 const deadline=performance.now()+15000;
 while(performance.now()<deadline){
  const observed=await shown(),s=observed.values;
  if(s.MainPID==="0"&&s.ControlPID==="0"&&(s.Job===""||s.Job==="0")&&s.ActiveState==="inactive"&&fs.existsSync(receipt))return observed;
  await delay(100);
 }
 throw Error("fixture did not receive terminal native cohort");
}
async function natural(label){
 const started=await invoke();assert.equal(started.state,"started");
 const active=await shown();assert.equal(active.values.ActiveState,"active");assert.ok(Number(active.values.MainPID)>0);assert.match(active.values.InvocationID,/^[0-9a-f]{32}$/u);
 for(const [name,value]of Object.entries({MemoryMax:String(limits.memoryMaxBytes),MemoryHigh:String(limits.memoryHighBytes),MemorySwapMax:"0",TasksMax:"12",CPUQuotaPerSecUSec:"500ms",RuntimeMaxUSec:"10s"}))assert.equal(active.values[name],value,name);
 const second=await invoke();assert.equal(second.state,"running");
 const after=await shown();assert.equal(after.values.MainPID,active.values.MainPID);assert.equal(after.values.InvocationID,active.values.InvocationID);
 const end=await terminal(),bytes=fs.readFileSync(receipt),record=JSON.parse(bytes);
 assert.equal(record.ok,true);assert.equal(record.result,"success");assert.equal(record.exit.code,"exited");assert.equal(record.exit.status,"0");assert.equal(record.demand.pending,7);
 let alive=true;try{process.kill(Number(active.values.MainPID),0);}catch(error){if(error.code==="ESRCH")alive=false;else throw error;}
 assert.equal(alive,false);
 save(label+"-receiving.json",{started,active,duplicateReturn:second,afterDuplicate:after,terminal:end,receipt:{bytes:bytes.length,sha256:sha(bytes),record},pidAbsent:true});
 return {invocation:active.values.InvocationID,receiptBytes:bytes,startedAt:record.startedAt};
}
try{
 const before=await shown();save("child-before.json",before);assert.equal(before.values.LoadState,"not-found");assert.equal(before.values.MainPID,"0");assert.equal(before.values.ControlPID,"0");assert.ok(!before.values.InvocationID);assert.ok(!before.values.Job||before.values.Job==="0");
 for(const d of["jobs","state/jobs"])fs.mkdirSync(join(root,d),{recursive:true});
 fs.writeFileSync(join(root,"inert.mjs"),`import fs from "node:fs";import{setTimeout}from"node:timers/promises";import{writeNodeJobDemand}from ${JSON.stringify("/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/data/logs/source-receiving-logs/node-job-native-resource-admission-20261023/source/src/node-job.mjs")};const row={pid:process.pid,invocation:process.env.INVOCATION_ID,at:new Date().toISOString()};fs.appendFileSync(${JSON.stringify(join(root,"inert-writer.ndjson"))},JSON.stringify({...row,event:"started"})+"\\n");console.log(JSON.stringify({...row,event:"fixture-started"}));await setTimeout(2000);writeNodeJobDemand({pending:7});fs.appendFileSync(${JSON.stringify(join(root,"inert-writer.ndjson"))},JSON.stringify({...row,event:"ended"})+"\\n");console.log(JSON.stringify({...row,event:"fixture-ended"}));\n`,{flag:"wx"});
 writeJob(job);
 const first=await natural("first-natural"),receiptBefore=fs.readFileSync(receipt),demandBefore=fs.readFileSync(demand);
 writeJob({...job,resources:{...limits,memoryMaxBytes:Number.MAX_SAFE_INTEGER-limits.memoryReserveBytes}});
 await assert.rejects(invoke,{code:"NODE_JOB_RESOURCE_ADMISSION"});
 assert.deepEqual(fs.readFileSync(receipt),receiptBefore);assert.deepEqual(fs.readFileSync(demand),demandBefore);
 const refused=await shown();assert.equal(refused.values.MainPID,"0");assert.equal(refused.values.ControlPID,"0");
 save("resource-refusal.json",{native:refused,receiptSha256:sha(receiptBefore),demandSha256:sha(demandBefore),preserved:true,realPhysicalReader:true});
 writeJob(job);const second=await natural("second-natural");assert.notEqual(second.invocation,first.invocation);
 const lines=fs.readFileSync(join(root,"inert-writer.ndjson"),"utf8").trim().split("\n").map(x=>JSON.parse(x));
 assert.equal(lines.length,4);assert.deepEqual(lines.map(x=>x.event),["started","ended","started","ended"]);
 const journal=await execute("journalctl",["--user","--user-unit="+unit,"--output=json","--no-pager","--lines=64"],{encoding:"utf8",timeout:3000,maxBuffer:262144});
 fs.writeFileSync(join(root,"native-journal.ndjson"),journal.stdout,{flag:"wx"});
 save("native-kernel-receiving.json",{type:"NodeJobNativeResourceReceiving",candidate:"93ab2190e28e3c1f703e10c76770bcd1f0f56b8e",unit,limits,firstInvocation:first.invocation,secondInvocation:second.invocation,runs:2,duplicateStarts:0,naturalSuccesses:2,resourceRefusalPreservedReceiptAndDemand:true,journal:{bytes:Buffer.byteLength(journal.stdout),sha256:sha(journal.stdout)},productionEffects:0});
 console.log(JSON.stringify({status:"received",unit,runs:2}));
}catch(error){save("native-kernel-failure.json",{type:"NodeJobNativeResourceReceivingFailed",message:error.message,stack:error.stack,unit,retryAuthorized:false});throw error;}
