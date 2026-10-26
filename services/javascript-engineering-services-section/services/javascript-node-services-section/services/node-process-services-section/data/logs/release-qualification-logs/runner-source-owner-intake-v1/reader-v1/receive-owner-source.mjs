import assert from 'node:assert/strict';
import {readFileSync,lstatSync,realpathSync,mkdirSync,openSync,writeFileSync,fsyncSync,closeSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const hash=b=>createHash('sha256').update(b).digest('hex'),[input,expected]=process.argv.slice(2),bytes=readFileSync(input);assert.equal(hash(bytes),expected);const c=JSON.parse(bytes);
for(const p of c.ancestors){const s=lstatSync(p);assert(s.isDirectory()&&!s.isSymbolicLink());assert.equal(realpathSync(p),p);}
for(const [p,h]of Object.entries(c.files)){assert(lstatSync(p).isFile()&&!lstatSync(p).isSymbolicLink());assert.equal(hash(readFileSync(p)),h,p);}
const group=readFileSync('/proc/self/cgroup','utf8').trim().slice(3);assert(group.endsWith('/'+c.unit));assert.equal(readFileSync('/sys/fs/cgroup'+group+'/memory.max','utf8').trim(),'2147483648');mkdirSync(c.workDirectory,{mode:0o700});
const save=(name,x)=>{const fd=openSync(c.workDirectory+'/'+name,'wx',0o600);try{writeFileSync(fd,JSON.stringify(x,null,2)+'\n');fsyncSync(fd);}finally{closeSync(fd);}};save('operation-start.json',{at:new Date().toISOString(),unit:c.unit,inputSHA256:expected,repository:c.repository,credential:false});
try{
 const {createClient}=await import(pathToFileURL(c.module).href),api=createClient({token:null,budgetFloor:10,secondaryRetries:0});
 const ref=await api.request('GET','/repos/'+c.repository+'/git/ref/heads/main');assert.equal(ref.object.type,'commit');save('ref.json',{ref:ref.ref,sha:ref.object.sha});
 const commit=await api.request('GET','/repos/'+c.repository+'/git/commits/'+ref.object.sha);save('commit.json',{sha:commit.sha,tree:commit.tree.sha,parents:commit.parents.map(x=>x.sha)});
 const tree=await api.request('GET','/repos/'+c.repository+'/git/trees/'+commit.tree.sha+'?recursive=1');assert.equal(tree.truncated,false);assert(tree.tree.length<=20000);save('source-tree.json',tree);
 const wanted=tree.tree.filter(z=>z.type==='blob'&&(['package.json','.gitmodules','README.md'].includes(z.path)||/(^|\/)(check-package-syntax|run-package-tests)\.(mjs|js|cjs|mts|ts)$/u.test(z.path)));assert(wanted.length<=16);let total=0;const rows=[];
 for(let i=0;i<wanted.length;i++){const z=wanted[i];assert(z.size<=524288);const blob=await api.request('GET','/repos/'+c.repository+'/git/blobs/'+z.sha);assert.equal(blob.encoding,'base64');const b=Buffer.from(blob.content,'base64');total+=b.length;assert(total<=4194304);assert.equal(createHash('sha1').update(Buffer.concat([Buffer.from('blob '+b.length+'\0'),b])).digest('hex'),z.sha);const fd=openSync(c.workDirectory+'/'+i+'-source','wx',z.mode==='100755'?0o700:0o600);writeFileSync(fd,b);fsyncSync(fd);closeSync(fd);rows.push({path:z.path,gitBlob:z.sha,mode:z.mode,sha256:hash(b),bytes:b.length,file:i+'-source'});}
 save('selected-source.json',{repository:c.repository,commit:commit.sha,tree:commit.tree.sha,rows});
 const slimRepo=r=>r?{id:r.id,full_name:r.full_name,private:r.private,default_branch:r.default_branch}:null;
 const pulls=await api.paginate('/repos/'+c.repository+'/pulls?state=all',{maxPages:2});save('all-state-pulls.json',pulls.map(x=>({number:x.number,title:x.title,state:x.state,draft:x.draft,html_url:x.html_url,body:x.body,merged_at:x.merged_at,head:{ref:x.head.ref,sha:x.head.sha,repo:slimRepo(x.head.repo)},base:{ref:x.base.ref,sha:x.base.sha,repo:slimRepo(x.base.repo)}})));
 const issues=await api.paginate('/repos/'+c.repository+'/issues?state=all',{maxPages:2});save('all-state-issues.json',issues.map(x=>({number:x.number,title:x.title,state:x.state,html_url:x.html_url,body:x.body,isPull:Boolean(x.pull_request)})));
 save('terminal.json',{at:new Date().toISOString(),status:0,commit:commit.sha,selectedFiles:rows.length,totalBytes:total,pulls:pulls.length,issues:issues.length,scope:'Read-only proper producer source intake, no source patch/installation/publication or native runner qualification'});console.log(JSON.stringify({status:0,commit:commit.sha,selectedFiles:rows.length,pulls:pulls.length,issues:issues.length}));
}catch(e){save('terminal.json',{at:new Date().toISOString(),status:1,error:{name:e.name,code:e.code??null,status:e.status??null,message:e.message}});console.error(JSON.stringify({name:e.name,code:e.code??null,status:e.status??null,message:e.message}));process.exitCode=1;}
