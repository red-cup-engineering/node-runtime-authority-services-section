import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir, lstat, realpath, open } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { receiveStoragePlan, runStorageStage } from '/gnu/store/4p6h0qhki49lpb47z2ppk44cyazx39rq-bare-cedar-fog-deployment-1/node_modules/@red-cup-engineering/computer-deployment-engine/src/fabrication-storage.mjs';

const R = dirname(fileURLToPath(import.meta.url));
const readJSON = async path => JSON.parse(await readFile(path, 'utf8'));
const hash = async path => createHash('sha256').update(await readFile(path)).digest('hex');
const inputs = await readJSON(join(R, 'full-v2-source-qa-inputs.json'));
const plan = await readJSON(join(R, 'full-v2-source-binding-plan.json'));
const C = inputs.source, L = dirname(C), nativeRequire = createRequire(join(inputs.nativeCode, 'package.json'));
async function absent(path) {
  try { await lstat(path); throw Error('existing task custody: ' + path); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
}
async function sourceGuards() {
  const lock = await readJSON(join(R, 'code-primitive-lock-receipt.json'));
  for (const file of inputs.files) assert.equal(await hash(join(C, file.path)),
    file.path === 'pnpm-lock.yaml' ? lock.lockSHA256 : file.sha256, file.path);
  assert.equal(await hash(join(C, 'package.json')), lock.manifestSHA256);
  assert.equal(await hash(inputs.primitiveReceipt), inputs.primitiveReceiptSHA256);
  const supplier = await readJSON(inputs.primitiveReceipt);
  assert.equal(supplier.artifactDownloaded, true); assert.equal(supplier.version, '0.1.2');
  assert.equal(supplier.gitHead, 'dcbcf09bb834a2dd00480378ca47607803d7a04e');
  for (const provider of plan.packages.slice(1)) {
    assert.equal(await realpath(provider.dir), provider.dir);
    assert.equal(await hash(join(provider.dir, 'package.json')), provider.manifestSHA256);
  }
}
if (process.argv[2] === '--execute') {
  await sourceGuards();
  const manifest = await readJSON(join(C, 'package.json'));
  const { dependencySpecificationViolations } = await import(pathToFileURL(join(inputs.nativeCode, 'src/dependency-policy.mjs')));
  assert.deepEqual(dependencySpecificationViolations(manifest), []);
  assert.equal(manifest.scripts.test, 'node --test test/*.test.mjs');
  const tmp = join(L, 'full-v2-native-test-tmp'); await absent(tmp); await mkdir(tmp, { mode: 0o700 });
  // Untyped original native-tmp semantics preserve both CommonJS fixtures and
  // native syntax detection, despite the operational owner's type:module.
  await writeFile(join(tmp, 'package.json'), '{}\n', { flag: 'wx', mode: 0o600 });
  await mkdir(join(tmp, 'home'), { mode: 0o700 });
  await writeFile(join(tmp, 'npmrc'), '', { flag: 'wx', mode: 0o600 });
  const git = '/gnu/store/niv2n69b6gr947cp1p1k9lyzml7nnhvg-git-minimal-2.54.0/bin/git';
  assert.equal(await hash(git), '24d78a30250537129fc84cbad6bfd4fceb4ffcc69a90981f97cdfb67971fef7b');
  const env = Object.fromEntries(['LANG', 'LC_ALL', 'TZ', 'SystemRoot', 'WINDIR'].filter(key => process.env[key] !== undefined).map(key => [key, process.env[key]]));
  Object.assign(env, { PATH: dirname(process.execPath) + ':' + dirname(git) + ':' + process.env.PATH,
    HOME: join(tmp, 'home'), TMPDIR: tmp, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null',
    GIT_DEFAULT_HASH: 'sha1', npm_config_userconfig: join(tmp, 'npmrc'), npm_config_cache: join(tmp, 'npm-cache'),
    npm_config_update_notifier: 'false', npm_config_audit: 'false', npm_config_fund: 'false' });
  const { withSourceBindings } = await import(pathToFileURL(join(inputs.nativeCode, 'src/source-bindings.mjs')));
  const { parseTestRunSummary } = await import(pathToFileURL(join(inputs.nativeCode, 'src/test-run-summary.mjs')));
  const { executeJavascriptNodeCommand } = await import(pathToFileURL(nativeRequire.resolve('@red-cup-engineering/execute-javascript-node-command-service')));
  for (const dependency of plan.dependencies[manifest.name]) await absent(join(C, 'node_modules', dependency));
  let receipt;
  try {
    receipt = await withSourceBindings(plan, async () => executeJavascriptNodeCommand({
      type: 'JavascriptNodeCommandExecutionRequest', version: 1,
      command: process.execPath, arguments: ['--test', ...inputs.tests], directory: C, environment: env, input: null,
    }, { timeoutMilliseconds: 300000 }));
  } finally {
    for (const dependency of plan.dependencies[manifest.name]) await absent(join(C, 'node_modules', dependency));
    await sourceGuards();
  }
  await writeFile(join(L, 'full-v2-native-qa.stdout'), receipt.result.stdout, { flag: 'wx', mode: 0o600 });
  await writeFile(join(L, 'full-v2-native-qa.stderr'), receipt.result.stderr, { flag: 'wx', mode: 0o600 });
  await writeFile(join(R, 'full-v2-native-command-receipt.json'), JSON.stringify(receipt, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
  const summary = parseTestRunSummary(receipt.result.stdout + receipt.result.stderr);
  await writeFile(join(R, 'full-v2-native-qa-receipt.json'), JSON.stringify({
    kind: 'OriginalPR24FullV2SourceQualification', source: C, sourceCommit: '24bb6cedfe36a847057f9003bde6e88bcc7da00b',
    bindingPlanSHA256: await hash(join(R, 'full-v2-source-binding-plan.json')), inputsSHA256: await hash(join(R, 'full-v2-source-qa-inputs.json')),
    primitive: await readJSON(inputs.primitiveReceipt), node: { path: process.execPath, version: process.version, sha256: await hash(process.execPath) },
    git: { path: git, sha256: await hash(git) }, nativeCommandReceipt: join(R, 'full-v2-native-command-receipt.json'),
    result: { status: receipt.result.status, signal: receipt.result.signal, error: receipt.result.error }, summary,
    bindingsFinallyRestored: true, installationPerformed: false, versionAllocated: false, publicationPerformed: false,
  }, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
  assert.equal(receipt.result.status, 0); assert.equal(receipt.result.signal, null); assert.equal(receipt.result.error, '');
  assert.equal(summary.tests, summary.pass); assert.equal(summary.fail, 0);
  console.log(JSON.stringify({ state: 'source-qualified', ...summary, bindingsFinallyRestored: true }));
 } else {
  const { plan: storage } = receiveStoragePlan(...process.argv.slice(2));
  async function durable(name,value) { const fd=await open(join(R,name),'wx',0o600); try { await fd.writeFile(JSON.stringify(value,null,2)+'\n'); await fd.sync(); } finally { await fd.close(); } }
  let admissionPersisted=false,childStarted=false;
  try {
    const result=await runStorageStage(storage,storage.stages[0].name,{
      requiredPaths:[R,L],
      onAdmission:async admission=>{
        const calculations=(admission.before?.backing?.volumes??[]).map(volume=>{try{const remaining=BigInt(volume.availableBytes)-BigInt(volume.peakBytes)-BigInt(volume.policy.growthBytes)-BigInt(volume.policy.overheadBytes);return{volume:volume.id,availableBytes:volume.availableBytes,peakBytes:volume.peakBytes,growthBytes:volume.policy.growthBytes,overheadBytes:volume.policy.overheadBytes,remainingAfterCharges:remaining.toString(),requiredFloor:'100000000000',accepted:remaining>=100000000000n};}catch(error){return{volume:volume.id,accepted:false,error:{name:error.name,message:error.message}};}});
        await durable('full-v2-native-qa-admission.json',{...admission,taskPhysicalFloor:{requiredBytes:'100000000000',calculations}});admissionPersisted=true;
        assert.ok(calculations.length>0&&calculations.every(row=>row.accepted),'task100GBphysicalfloorunmet');
      },
      execute:async args=>{
        childStarted=true;const env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
        try {const output=await promisify(execFile)(args[0],args.slice(1),{cwd:'/home/emsenn/info',env,timeout:330000,maxBuffer:2097152});process.stdout.write(output.stdout);process.stderr.write(output.stderr);return{code:0,signal:null};}
        catch(error){process.stderr.write(error.stderr||error.message);return{code:typeof error.code==='number'?error.code:null,signal:error.signal??null};}
      },
    });
    await durable('full-v2-native-qa-terminal.json',result);console.log(JSON.stringify({state:result.state,result:result.commandResult,error:result.error}));if(result.state!=='completed')process.exitCode=1;
  }catch(error){await durable('full-v2-native-qa-outer-refusal.json',{kind:'TaskNativeStorageOuterRefusal',plan:process.argv[2],expectedPlanSHA256:process.argv[3],admissionPersisted,childStarted,error:{name:error.name,message:error.message,code:error.code??null},replayAuthorized:false});throw error;}
}
