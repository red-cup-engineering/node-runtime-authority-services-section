import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {nodeJobProgramEntries} from '../src/node-job.mjs';
function fixture(t,patch={}) {
 const root=mkdtempSync(join(tmpdir(),'node-job-entries-'));
 t.after(()=>rmSync(root,{recursive:true,force:true}));
 mkdirSync(join(root,'jobs'));mkdirSync(join(root,'owner'));
 const job={id:'example',summary:'Example',directory:'owner',node:['main.mjs'],finally:['checkpoint.mjs'],...patch};
 writeFileSync(join(root,'jobs/example.json'),JSON.stringify(job));
 return {root,options:{runtimeRoot:root,jobsDirectory:'jobs'}};
}
test('retain mode resolves missing programmes and finalizers from the validated owner directory',t=>{
 const {root,options}=fixture(t);writeFileSync(join(root,'owner/main.mjs'),'');
 assert.throws(()=>nodeJobProgramEntries(options),/program not installed/);
 assert.deepEqual(nodeJobProgramEntries({...options,missingPrograms:'retain'}),[join(root,'owner/main.mjs'),join(root,'owner/checkpoint.mjs')]);
});
test('absent owner retains every path; preloads, release coordinates and duplicates use one collector',t=>{
 const {root,options}=fixture(t,{directory:'absent',node:['--import','{release}/preload.mjs','main.mjs'],finally:['main.mjs']});
 assert.throws(()=>nodeJobProgramEntries(options),/owning package not installed/);
 assert.deepEqual(nodeJobProgramEntries({...options,missingPrograms:'retain'}),[join(root,'preload.mjs'),join(root,'absent/main.mjs')]);
});
for(const patch of [{directory:'/outside'},{directory:'../outside'},{node:[]},{node:[3]},{finally:[]},{summary:''},{environment:{bad:'value'}},{demand:true,schedule:'* * * * *'}]) {
 test('retain mode still applies canonical declaration validation: '+JSON.stringify(patch),t=>{
  const {options}=fixture(t,patch);assert.throws(()=>nodeJobProgramEntries({...options,missingPrograms:'retain'}),TypeError);
 });
}
test('retain mode refuses programme escapes and unknown policies',t=>{
 const {options}=fixture(t,{node:['../../escape.mjs']});
 assert.throws(()=>nodeJobProgramEntries({...options,missingPrograms:'retain'}),/escapes/);
 assert.throws(()=>nodeJobProgramEntries({...options,missingPrograms:true}),/missingPrograms/);
});
