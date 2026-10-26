import vm from 'node:vm';
import {isBuiltin,stripTypeScriptTypes} from 'node:module';
import {readFile,realpath,stat} from 'node:fs/promises';
import {dirname,extname,isAbsolute,join,relative,resolve,sep} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

const within=(root,file)=>{const p=relative(root,file);return !isAbsolute(p)&&p!=='..'&&!p.startsWith('..'+sep);};

/** Read the declared program's static ESM links using Node's own import
 * resolver. Never import or evaluate application code. The temporary native
 * installation link is supplied by the owning producer, before transfer. */
export async function readNativeRegistryImports({root,entrances,maxModules=10000}){
 if(typeof vm.SourceTextModule!=='function'||!process.execArgv.includes('--experimental-import-meta-resolve'))
  throw new Error('native import reading requires VM modules and import.meta.resolve parentURL support');
 if(!Array.isArray(entrances)||!entrances.length||entrances.length>64||new Set(entrances).size!==entrances.length)
  throw new TypeError('one through 64 distinct declared Node entrances required');
 if(!Number.isSafeInteger(maxModules)||maxModules<1||maxModules>10000)throw new TypeError('bounded native module population required');
 root=await realpath(resolve(root));
 const installation=await realpath(join(root,'node_modules'));
 const pending=entrances.map(path=>{
  if(typeof path!=='string'||isAbsolute(path)||path.includes('\0')||!within(root,resolve(root,path)))throw new TypeError('Node entrance must stay within its carrier');
  return {file:resolve(root,path)};
 });
 const seen=new Set(),packageTypes=new Map();
 const reading={kind:'npm.native-registry-static-imports',entrances:[...entrances],modules:0,bytesRead:0,opaqueCommonJs:0,dynamicImports:'not-inspected',findings:[]};
 async function moduleType(file){
  for(let dir=dirname(file);;dir=dirname(dir)){
   if(packageTypes.has(dir))return packageTypes.get(dir);
   try{const p=JSON.parse(await readFile(join(dir,'package.json'),'utf8'));packageTypes.set(dir,p.type);return p.type;}
   catch(error){if(error.code!=='ENOENT')throw error;}
   if(dir===root||dir===installation||dirname(dir)===dir)return undefined;
  }
 }
 while(pending.length){
  const request=pending.pop();let file;
  try{
   file=await realpath(request.file);
   if(!within(root,file)&&!within(installation,file))throw new Error('module leaves its received carrier and installation');
   if(seen.has(file))continue;
   if(seen.size>=maxModules){pending.length=0;throw new Error('declared native module population exceeds its bound');}
   seen.add(file);
   const info=await stat(file);if(!info.isFile()||info.size>16*1024*1024)throw new Error('module must be a bounded regular file');
   const extension=extname(file);
   const type=extension==='.js'?await moduleType(file):undefined;
   if(extension==='.node'||extension==='.cjs'||(extension==='.js'&&type==='commonjs')){reading.opaqueCommonJs++;continue;}
   if(!['.mjs','.js','.ts','.mts','.json'].includes(extension))throw new Error('unsupported static Node module format');
   const text=await readFile(file,'utf8');reading.bytesRead+=Buffer.byteLength(text);
   if(reading.bytesRead>256*1024*1024){pending.length=0;throw new Error('declared native source bytes exceed their bound');}
   if(extension==='.json'){JSON.parse(text);continue;}
   if(extension==='.js'&&type!=='module'){
    try{
     // Compile only: Node's wrapper bindings distinguish ambiguous ESM syntax
     // without evaluating application code or treating real CommonJS as ESM.
     vm.compileFunction(text,['exports','require','module','__filename','__dirname'],{filename:file});
     reading.opaqueCommonJs++;continue;
    }catch(error){if(!(error instanceof SyntaxError))throw error;}
   }
   const source=['.ts','.mts'].includes(extension)?stripTypeScriptTypes(text,{mode:'strip',sourceUrl:file}):text;
   const module=new vm.SourceTextModule(source,{identifier:file});reading.modules++;
   for(const specifier of module.dependencySpecifiers){
    if(isBuiltin(specifier))continue;
    try{
     const target=new URL(import.meta.resolve(specifier,pathToFileURL(file).href));
     if(target.protocol!=='file:')throw new Error('static module URL is outside the received filesystem');
     pending.push({file:fileURLToPath(target),from:file,specifier});
    }catch(error){reading.findings.push({file,source:specifier,code:error.code??'MODULE_RESOLUTION_REFUSED',message:error.message});}
   }
  }catch(error){reading.findings.push({file:request.from??request.file,source:request.specifier??request.file,code:error.code??'MODULE_SOURCE_REFUSED',message:error.message});}
 }
 return reading;
}
