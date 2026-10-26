import assert from 'node:assert/strict';
import test from 'node:test';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,rmSync,existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';

const recorder=process.env.NODE_JOB_TEST_RECORDER ?? fileURLToPath(new URL('../scripts/record-node-job-run.mjs',import.meta.url));

function recordOutcome({result,code,status},expectedOk){
 const root=mkdtempSync(join(tmpdir(),'node-job-outcome-'));
 try{
  const bin=join(root,'bin'),receipt=join(root,'receipt.json'),demand=join(root,'demand.json');
  mkdirSync(bin);
  // The real recorder runs. Only its read of the host journal is isolated;
  // this executable never contacts systemd, a live job or a real journal.
  writeFileSync(join(bin,'journalctl'),`#!${process.execPath}\nprocess.stdout.write('fixture job output\\n');\n`,{mode:0o700});
  const asked={pending:2,nextAt:'2026-10-18T18:00:00Z'};
  writeFileSync(demand,JSON.stringify(asked));
  const run=spawnSync(process.execPath,[recorder,receipt],{
   encoding:'utf8',timeout:10000,
   env:{...process.env,PATH:bin+':'+dirname(process.execPath)+':'+process.env.PATH,
    SERVICE_RESULT:result,EXIT_CODE:code,EXIT_STATUS:status,
    NODE_JOB_ID:'fixture-job',NODE_JOB_UNIT:'fixture-job.service',NODE_JOB_RELEASE:'fixture-artifact',
    NODE_JOB_STARTED_AT:'2026-10-18T17:02:45.546Z',NODE_JOB_DEMAND:demand}
  });
  assert.ifError(run.error);assert.equal(run.signal,null);assert.equal(run.status,0,run.stderr);
  const recorded=JSON.parse(readFileSync(receipt,'utf8'));
  assert.equal(recorded.kind,'node-job-run.v1');
  assert.equal(recorded.ok,expectedOk);
  assert.equal(recorded.result,result,'retain the raw service manager result');
  assert.deepEqual(recorded.exit,{code,status},'retain exact termination evidence');
  assert.equal(recorded.job,'fixture-job');
  assert.equal(recorded.unit,'fixture-job.service');
  assert.equal(recorded.release,'fixture-artifact');
  assert.equal(recorded.startedAt,'2026-10-18T17:02:45.546Z');
  assert.ok(Number.isFinite(Date.parse(recorded.endedAt)));
  assert.deepEqual(recorded.tail,['fixture job output']);
  assert.equal(recorded.demandAsked,true);assert.deepEqual(recorded.demand,asked);
  assert.equal(existsSync(receipt+'.part'),false,'receipt keeps its original atomic write');
 }finally{rmSync(root,{recursive:true,force:true});}
}

test('a clean service result after SIGTERM is an interrupted job, not completed success',()=>{
 recordOutcome({result:'success',code:'killed',status:'TERM'},false);
});

test('a normal zero exit with service success remains successful',()=>{
 recordOutcome({result:'success',code:'exited',status:'0'},true);
});

test('an accepted nonzero SuccessExitStatus remains successful',()=>{
 recordOutcome({result:'success',code:'exited',status:'77'},true);
});

test('a failure service result remains unsuccessful after a normal process exit',()=>{
 recordOutcome({result:'exit-code',code:'exited',status:'1'},false);
});
