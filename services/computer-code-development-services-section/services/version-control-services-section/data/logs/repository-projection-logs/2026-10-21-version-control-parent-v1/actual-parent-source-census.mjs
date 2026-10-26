import {execFileSync} from 'node:child_process';
import {writeFileSync} from 'node:fs';
import {createClient} from '/gnu/store/5kiif6v7m6zw0kyplrf4drnmaw057vi7-original-publisher-ghs-0.2.4/src/github-rest-client.mjs';
const token=execFileSync('/usr/bin/gh',['auth','token'],{encoding:'utf8',maxBuffer:65536,env:{...process.env,GH_CONFIG_DIR:'/home/emsenn/.config/gh'}}).trim();
const calls=[];const c=createClient({token,budgetFloor:200,secondaryRetries:0,fetchImpl:async(url,opts)=>{if(opts.method!=='GET'||calls.length>=16)throw Error('readonly bound');const r=await fetch(url,opts);calls.push({path:new URL(url).pathname,status:r.status});return r;}});
const repo='red-cup-engineering/computer-code-engineering-services-section';
const info=await c.request('GET','/repos/'+repo),branch=await c.request('GET','/repos/'+repo+'/branches/'+encodeURIComponent(info.default_branch));
const commit=await c.request('GET','/repos/'+repo+'/git/commits/'+branch.commit.sha);
const trees=[];let oid=commit.tree.sha;
for(const component of [null,'services','computer-code-development-services-section','services','version-control-services-section']){
 if(component!==null){const last=trees.at(-1).tree.find(x=>x.path===component);if(!last){trees.push({missing:component});break}if(last.type!=='tree'){trees.push({terminal:last});break}oid=last.sha;}
 const t=await c.request('GET','/repos/'+repo+'/git/trees/'+oid);if(t.truncated!==false||!Array.isArray(t.tree))throw Error('incomplete tree');trees.push({component,oid,tree:t.tree});
}
const result={at:new Date().toISOString(),repository:repo,repositoryId:info.id,visibility:info.visibility,defaultBranch:info.default_branch,commit:branch.commit.sha,rootTree:commit.tree.sha,trees,calls};
writeFileSync(new URL('./actual-parent-source-census.json',import.meta.url),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
