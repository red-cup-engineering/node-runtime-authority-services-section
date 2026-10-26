import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir, lstat, realpath, access } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { join } from 'node:path';
import { withSourceBindings } from '/gnu/store/4p6h0qhki49lpb47z2ppk44cyazx39rq-bare-cedar-fog-deployment-1/node_modules/@red-cup-engineering/npm-workspace-publication-service/src/source-bindings.mjs';
import { receiveRegistryTarball } from '/gnu/store/4p6h0qhki49lpb47z2ppk44cyazx39rq-bare-cedar-fog-deployment-1/node_modules/@red-cup-engineering/npm-workspace-publication-service/src/registry.mjs';
import { receiveStoragePlan, runStorageStage } from '/gnu/store/4p6h0qhki49lpb47z2ppk44cyazx39rq-bare-cedar-fog-deployment-1/node_modules/@red-cup-engineering/computer-deployment-engine/src/fabrication-storage.mjs';
const R="/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/services/javascript-engineering-services-section/services/javascript-node-services-section/services/jsnode-packaging-services-section/services/npm-services-section/services/npm-registry-services-section/data/records/npm-artifact-receiving-records/20261020-code22", L="/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/services/javascript-engineering-services-section/services/javascript-node-services-section/services/jsnode-packaging-services-section/services/npm-services-section/services/npm-registry-services-section/data/logs/npm-artifact-receiving-logs/20261020-code22", S="/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/services/javascript-engineering-services-section/services/javascript-node-services-section/services/jsnode-packaging-services-section/services/npm-services-section/services/npm-registry-services-section/data/state/npm-artifact-receiving-state/20261020-code22-semver", C="/var/tmp/engineering-abandoned-prs-20261020/packaging-github-intake/code23-source-bc494ee673f59fcdccc939a6102ae089fac1658b";
const pnpm='/home/emsenn/.cache/561-group/lagoon-promote/runtimes/f3e4672231d2b37284388677d176e9b2cd899744/node_modules/.pnpm/pnpm@11.28.5/node_modules/pnpm/bin/pnpm.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
const fileSha=async p=>sha(await readFile(p));
async function absent(p){try{await lstat(p);throw Error('custody already exists: '+p)}catch(e){if(e.code!=='ENOENT')throw e}}
const run=promisify(execFile);
async function guards(){const g=JSON.parse(await readFile(join(R,'native-installed-source-guards.json')));for(const e of g)assert.equal(await fileSha(e.path),e.sha256);}
if(process.argv[2]==='--execute'){
 await guards(); await absent(S); await mkdir(S,{mode:0o700});
 const home=join(S,'home');await mkdir(home,{mode:0o700});
 for(const f of ['npmrc','global-npmrc'])await writeFile(join(home,f),'',{flag:'wx',mode:0o600});
 let receive;
 await withSourceBindings(JSON.parse(await readFile(join(R,'code-0.14.24-source-binding-plan.json'))),async()=>{({receiveSourceRegistryConsumers:receive}=await import(C+'/src/source-registry-closure.mjs'));});
 // Native installation begins only after every source binding is restored.
 const m=JSON.parse(await readFile(join(R,'semver-7.7.2-registry-metadata.json')));assert.ok(m.found&&m.reachable);assert.equal(m.manifest.version,'7.7.2');assert.equal(m.manifest.dist.fileCount,52);assert.equal(m.manifest.dist.unpackedSize,97420);
 const artifact=join(S,'semver-7.7.2.tgz');await receiveRegistryTarball({registry:'https://registry.npmjs.org/',tarball:m.manifest.dist.tarball,integrity:m.manifest.dist.integrity,destination:artifact});
 assert.ok((await lstat(artifact)).size<1024*1024);
 const release={name:'semver',version:'7.7.2',integrity:m.manifest.dist.integrity,artifactDownloaded:true};
 await writeFile(join(R,'semver-7.7.2-native-artifact-receiving.json'),JSON.stringify({receiver:'original Code receiveRegistryTarball',...release,path:artifact,sha256:await fileSha(artifact)},null,2)+'\n',{flag:'wx',mode:0o600});
 const consumer=join(S,'consumer');await mkdir(consumer,{mode:0o700});
 const manifest={name:'native-code-member-receiving-fixture',version:'0.0.0',private:true,dependencies:{semver:'7.7.2'}};
 await writeFile(join(consumer,'package.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});
 await writeFile(join(consumer,'.npmrc'),'registry=https://registry.npmjs.org/\n',{flag:'wx'});
 const args=[pnpm,'--store-dir',join(S,'cache/store'),'--cache-dir',join(S,'cache/metadata')];
 const lock=await run(process.execPath,[...args,'--dir',consumer,'install','--lockfile-only','--ignore-scripts','--ignore-workspace','--reporter=append-only'],{cwd:consumer,env:process.env,timeout:60000,maxBuffer:1048576});
 await writeFile(join(L,'semver-native-lock-only.stdout'),lock.stdout+lock.stderr,{flag:'wx',mode:0o600});
 await absent(join(consumer,'node_modules'));
 const limits={members:100,bytes:1048576,archiveBytes:1048576,tarBytes:2097152,metadataBytes:65536,sourcePaths:1000,sourceRepositories:1};
 const selected={consumer:manifest.name,...release,registry:'https://registry.npmjs.org/',archive:{path:artifact,integrity:release.integrity},limits};delete selected.artifactDownloaded;delete selected.integrity;
 const first=await receive({consumerPaths:[consumer],releases:[release],artifactReceiving:[selected],artifactReceiptDirectory:R,logDirectory:join(L,'semver-native-success'),pnpm:process.execPath,pnpmArguments:args,installationTimeout:60000});
 await writeFile(join(R,'semver-native-installed-receipt.json'),JSON.stringify(first,null,2)+'\n',{flag:'wx',mode:0o600});
 assert.equal(first.refusals.length,0);assert.equal(first.packages.length,1);const received=first.packages[0].artifactReceiving[0];assert.equal(received.ok,true);assert.equal(received.installationClaimed,true);assert.equal(received.comparison.value.archive.length,52);assert.equal(received.installation.registrations.length,1);
 const modules=await lstat(join(consumer,'node_modules'));
 const ordinary=await run(join(consumer,'node_modules/.bin/semver'),['1.2.3'],{cwd:consumer,timeout:10000,maxBuffer:65536,env:process.env});assert.equal(ordinary.stdout.trim(),'1.2.3');
 const second=await receive({consumerPaths:[consumer],releases:[release],artifactReceiving:[{...selected,limits:{...limits,archiveBytes:1}}],artifactReceiptDirectory:R,logDirectory:join(L,'semver-native-preflight-refusal'),pnpm:process.execPath,pnpmArguments:args,installationTimeout:60000});
 assert.equal(second.packages.length,0);assert.equal(second.refusals.length,1);assert.equal((await lstat(join(consumer,'node_modules'))).ino,modules.ino);
 await writeFile(join(R,'semver-native-preflight-refusal.json'),JSON.stringify(second,null,2)+'\n',{flag:'wx',mode:0o600});
 await guards();
 await writeFile(join(R,'semver-native-installed-assay.json'),JSON.stringify({kind:'CodeSourceNativeInstalledMemberAssay',source:C,sourceVersion:'0.14.24',canonicalProviderContext:join(R,'code-0.14.24-source-binding-plan.json'),originalNativeFunction:'receiveSourceRegistryConsumers',nativeOperationReceipt:first.packages[0].artifactReceiving[0].installation.receipt,archiveMembers:52,registeredBins:1,ordinaryBin:{arguments:['1.2.3'],stdout:ordinary.stdout,stderr:ordinary.stderr},negative:'bounded archive preflight refusal preserved exact prior node_modules inode',bindingsRestoredBeforeInstallation:true,workspacePresent:false,sourceGuards:join(R,'native-installed-source-guards.json'),scope:'actual source-owner native operation; published Code canonical graph remains separate'},null,2)+'\n',{flag:'wx',mode:0o600});
 console.log(JSON.stringify({state:'received',archiveMembers:52,registeredBins:1,ordinaryBin:ordinary.stdout.trim(),refusalPreservedPrior:true}));
}else{
 const[path,digest]=process.argv.slice(2);const{plan}=receiveStoragePlan(path,digest);await absent(S);await guards();
 const result=await runStorageStage(plan,plan.stages[0].name,{requiredPaths:[R,L,"/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/services/javascript-engineering-services-section/services/javascript-node-services-section/services/jsnode-packaging-services-section/services/npm-services-section/services/npm-registry-services-section/data/state/npm-artifact-receiving-state"],onAdmission:async a=>{for(const v of a.before.backing.volumes)assert.ok(BigInt(v.availableBytes)-BigInt(v.peakBytes)-BigInt(v.policy.growthBytes)-BigInt(v.policy.overheadBytes)>=100000000000n);await writeFile(join(R,'semver-native-install-admission.json'),JSON.stringify(a,null,2)+'\n',{flag:'wx',mode:0o600});},execute:argv=>new Promise((resolve,reject)=>{const env=Object.fromEntries(['PATH','LANG','LC_ALL','TZ','SystemRoot','WINDIR'].filter(k=>process.env[k]!==undefined).map(k=>[k,process.env[k]]));Object.assign(env,{HOME:join(S,'home'),npm_config_userconfig:join(S,'home/npmrc'),npm_config_globalconfig:join(S,'home/global-npmrc'),npm_config_cache:join(S,'cache/npm'),npm_config_ignore_scripts:'true',npm_config_update_notifier:'false',npm_config_audit:'false',npm_config_fund:'false'});const p=spawn(argv[0],argv.slice(1),{stdio:'inherit',env});p.once('error',reject);p.once('close',(code,signal)=>resolve({code,signal}));})});
 await writeFile(join(R,'semver-native-install-terminal.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx',mode:0o600});console.log(JSON.stringify({state:result.state,result:result.commandResult,error:result.error}));if(result.state!=='completed')process.exitCode=1;
}
