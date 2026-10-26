import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {mkdir,mkdtemp,readFile,rm,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {promisify} from 'node:util';
import {test} from 'node:test';

const execute=promisify(execFile);
const reader=new URL('../src/native-registry-imports.mjs',import.meta.url).href;
async function fixture(t,source,manifest={}){
 const root=await mkdtemp(join(tmpdir(),'native-import-syntax-'));
 t.after(()=>rm(root,{recursive:true,force:true}));
 await mkdir(join(root,'node_modules'));
 await writeFile(join(root,'package.json'),JSON.stringify(manifest));
 await writeFile(join(root,'main.js'),source);
 return root;
}
async function inspect(root){
 const program=`import {readNativeRegistryImports} from ${JSON.stringify(reader)};
 console.log(JSON.stringify(await readNativeRegistryImports({root:process.argv[1],entrances:['main.js']})));`;
 const result=await execute(process.execPath,['--experimental-vm-modules',
  '--experimental-import-meta-resolve','--input-type=module','-e',program,root]);
 return JSON.parse(result.stdout);
}

test('untyped static ESM follows missing imports as native Node does',async t=>{
 const root=await fixture(t,"import './missing.mjs';\nthrow new Error('must not evaluate');\n");
 const reading=await inspect(root);
 assert.equal(reading.modules,1);
 assert.equal(reading.opaqueCommonJs,0);
 assert.equal(reading.findings.length,1);
 assert.equal(reading.findings[0].source,'./missing.mjs');
 // The oracle executes only this controlled fixture. Missing linkage prevents
 // evaluation, and distinguishes native ESM detection from CommonJS rejection.
 await assert.rejects(execute(process.execPath,[join(root,'main.js')]),error=>
  error.stderr.includes('ERR_MODULE_NOT_FOUND')&&!error.stderr.includes('must not evaluate'));
});

test('untyped ESM re-exports traverse actual files without evaluation',async t=>{
 const root=await fixture(t,"export * from './child.js';\nthrow new Error('must not evaluate');\n");
 await writeFile(join(root,'child.js'),"import './absent.mjs';\n");
 const reading=await inspect(root);
 assert.equal(reading.modules,2);
 assert.equal(reading.findings.length,1);
 assert.equal(reading.findings[0].source,'./absent.mjs');
});

test('all native ambiguous ESM syntax is parsed without running it',async t=>{
 for(const source of ['export const value=1;', 'void import.meta.url;',
  'await Promise.resolve();', 'const require=1;', 'const module=1;',
  'const exports=1;', 'const __dirname=1;', 'const __filename=1;']){
  const root=await fixture(t,source+"\nthrow new Error('must not evaluate');\n");
  const reading=await inspect(root);
  assert.equal(reading.modules,1,source);
  assert.equal(reading.opaqueCommonJs,0,source);
  assert.deepEqual(reading.findings,[],source);
 }
});

test('real CommonJS, wrapper return and hashbangs stay opaque',async t=>{
 for(const source of ["module.exports=require('./uninspected.cjs');",
  "return; module.exports=1;", "#!/usr/bin/env node\nmodule.exports=1;",
  "void import('./dynamic.mjs');"]){
  const root=await fixture(t,source+"\nthrow new Error('must not evaluate');\n");
  const reading=await inspect(root);
  assert.equal(reading.modules,0,source);
  assert.equal(reading.opaqueCommonJs,1,source);
  assert.deepEqual(reading.findings,[],source);
 }
});

test('explicit CommonJS remains opaque and invalid ambiguous source refuses',async t=>{
 const explicit=await fixture(t,"import './not-inspected.mjs';",{type:'commonjs'});
 const common=await inspect(explicit);
 assert.equal(common.opaqueCommonJs,1);
 assert.deepEqual(common.findings,[]);
 const invalid=await fixture(t,'export const = ;');
 const refused=await inspect(invalid);
 assert.equal(refused.findings.length,1);
 assert.equal(refused.findings[0].code,'MODULE_SOURCE_REFUSED');
});

test('nearest explicit package type remains authoritative',async t=>{
 const root=await fixture(t,"import './nested/main.js';",{type:'module'});
 await mkdir(join(root,'nested'));
 await writeFile(join(root,'nested','package.json'),JSON.stringify({type:'commonjs'}));
 await writeFile(join(root,'nested','main.js'),"require('./opaque.cjs');");
 const reading=await inspect(root);
 assert.equal(reading.modules,1);
 assert.equal(reading.opaqueCommonJs,1);
 assert.deepEqual(reading.findings,[]);
 assert.equal(await readFile(join(root,'nested','main.js'),'utf8'),"require('./opaque.cjs');");
});
