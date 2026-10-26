import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync,lstatSync,realpathSync,openSync,fsyncSync,closeSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const hash=b=>createHash('sha256').update(b).digest('hex');
const [config,expected]=process.argv.slice(2),raw=readFileSync(config);assert.equal(hash(raw),expected);const c=JSON.parse(raw);
const save=(name,value)=>{const p=c.workDirectory+'/'+name,fd=openSync(p,'wx',0o600);try{writeFileSync(fd,JSON.stringify(value,null,2)+'\n');fsyncSync(fd);}finally{closeSync(fd);}};
assert(!process.env.NODE_AUTH_TOKEN,'Public registry intake carries no credential');assert.equal(realpathSync(c.owner),c.owner);assert.equal(hash(readFileSync(c.source+'/package.json')),c.sourceManifestSHA256);
for(const [p,h]of Object.entries(c.files)){assert(lstatSync(p).isFile()&&!lstatSync(p).isSymbolicLink());assert.equal(hash(readFileSync(p)),h,p);}
const group=readFileSync('/proc/self/cgroup','utf8').trim().slice(3);assert(group.endsWith('/'+c.unit));assert.equal(readFileSync('/sys/fs/cgroup'+group+'/memory.max','utf8').trim(),'2147483648');
mkdirSync(c.workDirectory,{mode:0o700});save('operation-start.json',{at:new Date().toISOString(),unit:c.unit,sourceCommit:c.sourceCommit,inputsSHA256:expected,credential:false,queries:c.queries});
try{
 const api=await import(pathToFileURL(c.code.components.find(x=>x.path.endsWith('/registry.mjs')).path).href);
 const results=[];
 for(let i=0;i<c.queries.length;i++){
  const q=c.queries[i],start=new Date().toISOString();save(i+'-metadata-start.json',{at:start,...q,operation:'readRegistryPackageVersion'});
  const receipt=await api.readRegistryPackageVersion(c.registry,q.name,q.version);save(i+'-metadata-result.json',receipt);
  const row={...q,reachable:receipt.reachable,found:receipt.found};
  if(receipt.found){
   const m=receipt.manifest;assert.equal(m.name,q.name);assert.equal(m.version,q.version);
   save(i+'-archive-start.json',{at:new Date().toISOString(),operation:'receiveRegistryTarball',tarball:m.dist.tarball,integrity:m.dist.integrity});
   const a=await api.receiveRegistryTarball({registry:c.registry,tarball:m.dist.tarball,integrity:m.dist.integrity,destination:c.workDirectory+'/'+i+'.tgz'});save(i+'-archive-result.json',a);row.artifact=a;row.gitHead=m.gitHead??null;
  }
  results.push(row);
 }
 save('terminal.json',{at:new Date().toISOString(),status:0,results,scope:'Exact metadata/archive intake only; no install, package runner, registry PUT or full-package acceptance.'});
 console.log(JSON.stringify({status:0,results}));
}catch(e){save('terminal.json',{at:new Date().toISOString(),status:1,error:{name:e.name,code:e.code??null,message:e.message},scope:'Preserve any received metadata/archive and actual phase; no automatic replay.'});console.error(JSON.stringify({name:e.name,code:e.code??null,message:e.message}));process.exitCode=1;}
