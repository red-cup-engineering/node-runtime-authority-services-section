import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
const root=new URL('.',import.meta.url).pathname;
const supplier='/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/services/computer-code-development-services-section/services/version-control-services-section/services/git-services-section/data/logs/github-source-operation-suppliers/github-rest-client-0.2.4/github-rest-client.mjs';
if(createHash('sha256').update(readFileSync(supplier)).digest('hex')!=='8a3ea5787f79ef656a546596ab1b5d87b5b61f8419323a1416b7937432efeba5')throw Error('supplier changed');
for(const sub of ['gh-cache','tmp'])mkdirSync(root+sub,{recursive:true});
const token=execFileSync('/usr/bin/gh',['auth','token'],{encoding:'utf8',timeout:10000,stdio:['ignore','pipe','pipe'],env:{...process.env,GH_CACHE_DIR:root+'gh-cache',TMPDIR:root+'tmp'}}).trim();
const {createClient}=await import(pathToFileURL(supplier));
const client=createClient({token,budgetFloor:250,secondaryRetries:0});
const repo='red-cup-engineering/node-process-services-section',head='f0b7cf0a64738c5b08ffea973f2869c66f83958c',base='23113a67473de9784fdea1d1d45757fc0dd1569b';
const snapshotIndex='/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/services/javascript-engineering-services-section/services/javascript-node-services-section/services/node-process-services-section/data/logs/release-qualification-logs/node-process-coherent-native-metadata-v1/final-coherent-source-index-v2.json';
const index=JSON.parse(readFileSync(snapshotIndex));const out={at:new Date().toISOString(),repository:repo,head,base,reads:[]};
async function get(path){const data=await client.request('GET',`/repos/${repo}${path}`);out.reads.push({path,data});writeFileSync(root+'actual-source-readback.json',JSON.stringify(out,null,2)+'\n',{mode:0o600});return data;}
const repository=await get('');if(repository.id!==1425297553||repository.private!==false)throw Error('owner changed');
const pr=await get('/pulls/2');if(pr.head.sha!==head||pr.base.ref!=='main'||pr.state!=='open'||!pr.draft)throw Error('draft changed');
const commit=await get('/git/commits/'+head);if(commit.tree.sha!=='993ef058fa8fec8f1ca9f7127cc6dc42772ec6fc'||commit.parents.length!==1||commit.parents[0].sha!==base)throw Error('source ancestry changed');
const current=await get('/git/ref/heads/main');if(current.object.sha!==base)throw Error('main moved; record separately');
const before=await get('/git/trees/3ec1e72a033ae2c404a2481f2a775e7168d3aa75?recursive=1'),after=await get('/git/trees/'+commit.tree.sha+'?recursive=1');if(before.truncated||after.truncated)throw Error('truncated tree');
const leaves=t=>t.tree.filter(x=>x.type!=='tree');const old=leaves(before),next=leaves(after);if(old.length!==23||next.length!==27||next.some(x=>x.type==='commit'))throw Error('unexpected source population');
for(const row of index.sourceRows){const actual=next.find(x=>x.path===row.path);if(!actual||actual.sha!==row.gitBlob||actual.mode!==row.mode||actual.type!=='blob')throw Error('source row changed '+row.path);}
const changed=next.filter(x=>!old.some(y=>y.path===x.path&&y.sha===x.sha&&y.mode===x.mode));if(changed.length!==6||old.some(x=>!next.some(y=>y.path===x.path)))throw Error('unexpected source delta');
for(const row of changed){const blob=await get('/git/blobs/'+row.sha),bytes=Buffer.from(blob.content,'base64'),expected=index.sourceRows.find(x=>x.path===row.path);if(bytes.length!==expected.bytes||createHash('sha256').update(bytes).digest('hex')!==expected.sha256)throw Error('remote blob bytes changed '+row.path);}
const received={type:'IndependentActualDraftSourceReadback',at:new Date().toISOString(),repositoryId:repository.id,url:pr.html_url,head,tree:commit.tree.sha,base,grade:'Draft source only',exactChangedBodies:changed.map(x=>x.path),all27SourceRowsMatch:true,unrelated21LeavesExact:true,mainUnchanged:true,draft:true,nativePackageReleaseHostReceiving:false};writeFileSync(root+'independent-receiving.json',JSON.stringify(received,null,2)+'\n',{flag:'wx',mode:0o600});console.log(JSON.stringify(received));console.log(pr.body);
