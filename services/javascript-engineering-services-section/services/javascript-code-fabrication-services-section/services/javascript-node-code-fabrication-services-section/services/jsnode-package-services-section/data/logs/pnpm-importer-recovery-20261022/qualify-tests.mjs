import fs from "node:fs";
import path from "node:path";
import {spawnSync} from "node:child_process";
import {pathToFileURL} from "node:url";
const root=path.dirname(new URL(import.meta.url).pathname);
const consumer="/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-systems-engineering-services-section/services/agent-computer-system-engineering-services-section/apps/agent-organization-engine/data/logs/pace-s-baseline-main-20261022/lib/organizing";
const results=[];
function run(name,args,cwd){
 const result=spawnSync(process.execPath,args,{cwd,encoding:"utf8"});
 const log=path.join(root,name+".log");fs.writeFileSync(log,result.stdout+result.stderr);
 results.push({name,command:[process.execPath,...args],cwd,exitCode:result.status,log});
 console.log(name+": "+result.status+"\n"+(result.stdout+result.stderr).slice(-1300));
}
for(const version of ["0.2.5-dev.615","0.3.0","0.5.0"]){
 run("native-"+version,["--test",path.join(root,version,"package/test/pnpm-lockfile-importers.test.mjs")],root);
}
for(const version of ["0.2.4","0.5.0"]){
 const parser=pathToFileURL(path.join(root,version,"package/src/workspace/pnpm-lockfile.mjs")).href;
 const preload=path.join(root,"preload-"+version+".mjs");
 fs.writeFileSync(preload,'import { registerHooks } from "node:module";\nregisterHooks({resolve(specifier,context,nextResolve){return nextResolve(specifier==="@red-cup-engineering/jsnode-package-services-section/workspace/pnpm-lockfile"?'+JSON.stringify(parser)+':specifier,context);}});\n');
 run("organizing-baseline-"+version,["--import",preload,"--test","test/workspace-coordination.test.mjs"],consumer);
}
fs.writeFileSync(path.join(root,"test-results.json"),JSON.stringify(results,null,2)+"\n");

