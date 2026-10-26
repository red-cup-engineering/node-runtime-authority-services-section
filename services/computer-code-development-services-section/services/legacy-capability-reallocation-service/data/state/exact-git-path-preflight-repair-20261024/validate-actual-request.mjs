import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {readGitCommitPathsRequest} from '@red-cup-engineering/git-source-reading-service/git-command-codec';
import {readTrackedLegacySourcePublicationRequest} from 'file:///home/emsenn/info/lib/phezi-ochage/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/services/computer-code-development-services-section/services/legacy-capability-reallocation-service/src/tracked-legacy-source-publication.mjs';
const input=readFileSync(process.argv[2]);
const result=JSON.parse(input), reviewedSource=result.sourcePreparation.reviewedSource;
const paths=reviewedSource.entries.map(row=>row.path);
assert.equal(paths.length,68);
const request={paths,message:'Retire reviewed Git-preserved legacy capabilities',push:true,reviewedSource};
const decoded=readGitCommitPathsRequest(request);
assert.deepEqual(decoded.reviewedSource,reviewedSource);
assert.deepEqual(decoded.paths,[...paths].sort());
assert.ok(paths.some(path=>path.includes('\\360')));
assert.deepEqual(await readTrackedLegacySourcePublicationRequest({paths,reviewedSource}),decoded);
const unsafe=['/absolute',String.raw`\absolute`,'C:/outside',String.raw`C:\outside`,'a/C:outside',
  './a','../a','a/../b','a/./b','a//b','a/','.git','nested/.GIT/config',
  String.raw`a\..\b`,String.raw`a\.\b`,String.raw`a\.GIT\config`,
  String.raw`a\\b`,'a\\','a\rfile','a\nfile','a\tfile','a\u0000file','a\u001bfile','a\u007ffile'];
for(const path of unsafe){
  const cut={revision:reviewedSource.revision,entries:[{path,absent:true}]};
  assert.throws(()=>readGitCommitPathsRequest({paths:[path],message:'Receive',reviewedSource:cut}),TypeError);
  await assert.rejects(readTrackedLegacySourcePublicationRequest({paths:[path],reviewedSource:cut}),TypeError);
}
for(const path of [String.raw`a\b`,'notes/"quoted".md',':(glob)* [literal].mjs']){
  const cut={revision:reviewedSource.revision,entries:[{path,absent:true}]};
  assert.equal(readGitCommitPathsRequest({paths:[path],message:'Receive',reviewedSource:cut}).paths[0],path);
}
for(const cut of [{revision:reviewedSource.revision,entries:[]},
 {revision:reviewedSource.revision,entries:[{path:'foreign',absent:true}]},
 {revision:reviewedSource.revision,entries:[{path:'a',mode:'100644',type:'commit',sha:'b'.repeat(40)}]}]){
 await assert.rejects(readTrackedLegacySourcePublicationRequest({paths:['a'],reviewedSource:cut}),TypeError);
}
const receipt={kind:'exact-git-path-pure-validation/v1',ok:true,selected:paths.length,
 sourceInputSHA256:createHash('sha256').update(input).digest('hex'),unsafeRefusals:unsafe.length,
 literalNamesPreserved:true,serviceCanonicalRequestParity:true,gitProcesses:0,fixtures:0};
writeFileSync(process.argv[3],JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt));
