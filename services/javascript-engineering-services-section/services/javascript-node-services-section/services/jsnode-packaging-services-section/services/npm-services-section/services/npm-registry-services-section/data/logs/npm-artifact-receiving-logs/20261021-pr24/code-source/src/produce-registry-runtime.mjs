import {readFile,mkdir,mkdtemp,readdir,lstat,realpath,rm,rename,symlink,unlink,writeFile} from 'node:fs/promises';
import {cpSync} from 'node:fs';
import {resolve,dirname,join,relative,isAbsolute,sep} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {prepareSourceRegistryCarriers,packSourceRegistryClosure,nativeRegistryWorkspacePolicy} from './source-registry-closure.mjs';

const run=promisify(execFile);
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const inside=(root,file)=>{const p=relative(root,file);return !isAbsolute(p)&&p!=='..'&&!p.startsWith('..'+sep);};

/** Produce the portable tree from this owner's received frozen registry consumer.
 * No resolver, source-provider substitution, generation or application execution.
 * LAGOON receives this completed tree and owns its immutable machine realization.
 */
export async function produceRegistryRuntime({consumerPath,receiving,destination,transferInstallation=false}){
  if(typeof transferInstallation!=="boolean")throw new TypeError("installation transfer must be explicit boolean custody");
  const started=performance.now();
  const source=resolve(consumerPath),output=resolve(destination),manifestPath=join(source,'package.json');
  if(inside(source,output)||inside(output,source))throw new TypeError('source and runtime must be independent directories');
  if(receiving?.kind!=='npm.source-registry-closure.consumers'||receiving.refusals?.length)
    throw new TypeError('successful native frozen consumer receiving required');
  const matches=receiving.packages.filter(row=>row.path===manifestPath&&row.frozenInstall===true);
  if(matches.length!==1)throw new TypeError('one exact received consumer required');
  const [manifestBytes,lockBytes]=await Promise.all([readFile(manifestPath),readFile(join(source,'pnpm-lock.yaml'))]);
  const [held]=matches,manifest=JSON.parse(manifestBytes);
  const workspacePolicy=await nativeRegistryWorkspacePolicy(source);
  const workspacePolicyDigest=workspacePolicy===null?null:digest(workspacePolicy);
  if(digest(manifestBytes)!==held.manifestDigest||digest(lockBytes)!==held.lockDigest
    ||manifest.name!==held.name||manifest.version!==held.version)
    throw new Error('received consumer declarations changed');
  if(held.workspacePolicyDigest!==undefined&&held.workspacePolicyDigest!==workspacePolicyDigest)
    throw new Error('received consumer workspace policy changed');
  const modules=join(source,'node_modules');
  if(!(await lstat(modules)).isDirectory()||await realpath(modules)!==modules)
    throw new Error('received native installation is absent or redirected');
  const scratch=await mkdtemp(join(tmpdir(),'registry-runtime-'));
  let outputCreated=false,transferred=false,staticImports;
  try{
    // Reserve the caller's exact destination exclusively. A failed reservation
    // must neither damage a preexisting runtime nor leak the temporary pack.
    await mkdir(dirname(output),{recursive:true});
    await mkdir(output,{mode:0o700});
    outputCreated=true;
    // Reuse Code's bounded carrier staging. npm/Arborist scans the installed
    // dependency tree when invoked on the consumer itself, even when none of
    // those files belong in its package. Packing must not rediscover that tree.
    const plan={complete:true,registry:manifest.publishConfig?.registry??'https://registry.561.group/',packages:[{
      name:manifest.name,path:manifestPath,from:manifest.version,manifest,
      publish:true,rewrites:[],missingTargets:[],violations:[]}]};
    await prepareSourceRegistryCarriers(plan);
    const packing=await packSourceRegistryClosure(plan,{destination:scratch});
    if(packing.refusals.length||packing.packages.length!==1)throw new Error('consumer carrier packing refused');
    const [packed]=packing.packages,artifact=packed.artifact;
    if(!packed||packed.name!==manifest.name||packed.version!==manifest.version
      ||'sha512-'+createHash('sha512').update(await readFile(artifact)).digest('base64')!==packed.integrity)
      throw new Error('native consumer pack does not match its declarations');
    await run('tar',['-xzf',artifact,'-C',output,'--strip-components=1'],{timeout:60_000,maxBuffer:1024*1024});
    if(held.workspacePolicyDigest!==undefined&&await nativeRegistryWorkspacePolicy(output)!==workspacePolicy)
      throw new Error('packed consumer omits or changes its received workspace policy');
    const entrances=manifest.registryConsumption?.nodeEntrances;
    if(entrances!==undefined){
      const link=join(output,'node_modules');
      await symlink(modules,link,'dir');
      try{
        const {stdout}=await run(process.execPath,['--experimental-vm-modules','--experimental-import-meta-resolve',fileURLToPath(new URL('../scripts/read-native-registry-imports.mjs',import.meta.url)),output,JSON.stringify(entrances)],{timeout:60000,maxBuffer:16*1024*1024});
        staticImports=JSON.parse(stdout);
        if(staticImports.findings.length){
          throw new Error('declared Node composition has unresolved static imports: '+JSON.stringify(staticImports.findings));
        }
      }finally{await unlink(link);}
    }
    // Node's native recursive copier avoids a promise/syscall chain per file
    // in large PNPM trees. This dedicated fabrication process retains the same
    // carrier modes, timestamps and literal links, followed by confinement.
    if(transferInstallation){
      // An owned disposable installation already has the exact native graph.
      // Transfer it atomically on this filesystem instead of copying every
      // immutable dependency file. Cross-filesystem transfers refuse.
      await rename(modules,join(output,'node_modules'));transferred=true;
    }else cpSync(modules,join(output,'node_modules'),{recursive:true,verbatimSymlinks:true,preserveTimestamps:true});
    // Audit real link topology once; never copy a link to an authoring checkout
    // or shared install outside this completed portable runtime.
    const pending=[output];let files=0;
    while(pending.length){
      const dir=pending.pop();
      for(const entry of await readdir(dir,{withFileTypes:true})){
        const file=join(dir,entry.name);files++;
        if(entry.isSymbolicLink()){
          if(!inside(output,await realpath(file)))throw new Error('portable runtime link leaves its received closure');
        }else if(entry.isDirectory())pending.push(file);
        else if(!entry.isFile())throw new Error('portable runtime contains a nonregular carrier');
      }
    }
    if(digest(await readFile(manifestPath))!==held.manifestDigest||digest(await readFile(join(source,'pnpm-lock.yaml')))!==held.lockDigest)
      throw new Error('consumer changed during portable construction');
    if(await nativeRegistryWorkspacePolicy(source)!==workspacePolicy)
      throw new Error('consumer workspace policy changed during portable construction');
    return {kind:'npm.registry-runtime.produced',source,output,name:held.name,version:held.version,
      manifestDigest:held.manifestDigest,lockDigest:held.lockDigest,workspacePolicyDigest,rootIntegrity:packed.integrity,files,...(staticImports?{staticImports}:{}),durationMs:Math.ceil(performance.now()-started),...(transferred?{installationTransferred:true}:{})};
  }catch(error){
    if(transferred){
      try{
        try{await lstat(modules);throw new Error('source installation reappeared during transfer');}
        catch(cause){if(cause.code!=='ENOENT')throw cause;}
        await rename(join(output,'node_modules'),modules);
      }catch(rollback){throw new AggregateError([error,rollback],'runtime transfer failed; installation rollback requires attention');}
    }
    // Only remove a destination this invocation successfully created. After
    // an installation transfer rollback failure, execution exits above and
    // retains the received bytes for the real operator to recover.
    if(outputCreated){
      try{await rm(output,{recursive:true,force:true});}
      catch(cleanupError){throw new AggregateError([error,cleanupError],'portable runtime output cleanup failed');}
    }
    throw error;
  }finally{await rm(scratch,{recursive:true,force:true});}
}
