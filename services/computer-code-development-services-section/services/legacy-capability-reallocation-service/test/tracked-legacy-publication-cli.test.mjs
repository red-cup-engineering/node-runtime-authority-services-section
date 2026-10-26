import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync, spawnSync} from 'node:child_process';
import {mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, rmSync, symlinkSync, linkSync, renameSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const cli = fileURLToPath(new URL('../scripts/retire-tracked-legacy-capabilities.mjs', import.meta.url));
const computer = fileURLToPath(new URL('../../../../../../../', import.meta.url));
const fabrication = path.join(computer, 'services/computer-systems-engineering-services-section/services/computer-code-development-system-services-section/apps/computer-code-development-engine');
const resolver = path.join(computer, 'services/computer-code-engineering-services-section/services/javascript-engineering-services-section/services/javascript-node-services-section/scripts/register-house-resolver.mjs');

// The service is the consumer under test. All source effects use native local
// Git and Fabrication's existing provider fixtures through its public export.
function fixture(t, {withRecords = false, localReview = false, remoteChange} = {}) {
  const root = mkdtempSync(path.join(tmpdir(), 'legacy-publication-cli-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  const repository = path.join(root, 'work'), remote = path.join(root, 'source.git');
  const raw = (cwd, args) => String(execFileSync('git', args, {cwd, encoding:'utf8', stdio:['ignore','pipe','pipe']})).trim();
  const git = (...args) => raw(repository, args);
  raw(root, ['init', '--bare', '-q', remote]);
  raw(root, ['--git-dir', remote, 'config', 'uploadpack.allowFilter', 'true']);
  raw(root, ['init', '-q', '-b', 'main', repository]);
  git('config', 'user.name', 'Retirement consumer fixture');
  git('config', 'user.email', 'fixture@example.invalid');
  mkdirSync(path.join(repository, 'lib/legacy/batch'), {recursive:true});
  mkdirSync(path.join(repository, 'living'));
  for (const [name, body] of Object.entries({
    'lib/legacy/batch/first.md':'old first capability\n',
    'lib/legacy/batch/second.md':'old second capability\n',
    'lib/legacy/batch/unreceived.md':'separate unreceived source\n',
    'lib/legacy/batch/held.md':'held authored information\n',
    'living/receiver.mjs':'export const received = true;\n',
    'neighbor.txt':'upstream baseline\n',
    'other-writer.txt':'original unrelated source\n'
  })) writeFileSync(path.join(repository, name), body);
  git('add', '.'); git('commit', '-qm', 'Original capability source');
  const originalRevision = git('rev-parse', 'HEAD');
  git('remote', 'add', 'origin', remote); git('push', '-q', 'origin', 'main');
  // This already-committed absence is outside the reviewed cut. Pushing local
  // HEAD would lose it upstream, so source publication must preserve it.
  git('rm', '-q', 'lib/legacy/batch/unreceived.md');
  git('commit', '-qm', 'Separate unreceived native absence');
  const localParent = git('rev-parse', 'HEAD');
  const revision = localReview ? localParent : originalRevision;
  writeFileSync(path.join(repository, 'other-writer.txt'), 'another writer staged this\n');
  git('add', 'other-writer.txt');
  const staged = git('diff', '--cached', '--raw', '-z');
  const plan = {kind:'legacy-capability-retirement-plan/v1', repositoryRoot:repository, legacyRoot:'lib/legacy', revision,
    capabilities:[{id:'reviewed-two', disposition:'covered', reason:'Actual ordinary receiving implementation independently reviewed',
      sourcePaths:['batch/first.md','batch/second.md'], evidence:[{path:'living/receiver.mjs'}]}]};
  const recordsRepository = path.join(root, 'records-work'), recordsRemote = path.join(root, 'records.git');
  const recordsGit = (...args) => raw(recordsRepository, args);
  let recordsRevision, recordsHead, recordsStaged;
  if (withRecords) {
    raw(root, ['init', '--bare', '-q', recordsRemote]);
    raw(root, ['--git-dir', recordsRemote, 'config', 'uploadpack.allowFilter', 'true']);
    raw(root, ['init', '-q', '-b', 'main', recordsRepository]);
    recordsGit('config', 'user.name', 'Actual records owner fixture');
    recordsGit('config', 'user.email', 'records@example.invalid');
    mkdirSync(path.join(recordsRepository, 'data'));
    for (const [name, body] of Object.entries({
      'neighbor.txt':'records upstream baseline\n',
      'records-unreceived.txt':'separate records native absence\n',
      'other-writer.txt':'original records source\n'
    })) writeFileSync(path.join(recordsRepository, name), body);
    recordsGit('add', '.'); recordsGit('commit', '-qm', 'Original proper records owner');
    recordsRevision = recordsGit('rev-parse', 'HEAD');
    recordsGit('remote', 'add', 'origin', recordsRemote); recordsGit('push', '-q', 'origin', 'main');
    recordsGit('rm', '-q', 'records-unreceived.txt'); recordsGit('commit', '-qm', 'Separate records native absence');
    recordsHead = recordsGit('rev-parse', 'HEAD');
    writeFileSync(path.join(recordsRepository, 'other-writer.txt'), 'unrelated records staging\n');
    recordsGit('add', 'other-writer.txt'); recordsStaged = recordsGit('diff', '--cached', '--raw', '-z');
  }
  const planPath = withRecords ? path.join(recordsRepository, 'data/plan.json') : path.join(root, 'plan.json');
  const output = withRecords ? path.join(recordsRepository, 'data/result.json') : path.join(root, 'result.json');
  writeFileSync(planPath, JSON.stringify(plan));
  const bin = path.join(root, 'bin'); mkdirSync(bin);
  writeFileSync(path.join(bin, 'git'), `#!/bin/sh
set -eu
records_owner=0
if [ -n "\${RETIREMENT_TEST_RECORDS_ROOT:-}" ]; then
 case "$PWD $*" in *"$RETIREMENT_TEST_RECORDS_ROOT"*|*"$RETIREMENT_TEST_RECORDS_PHYSICAL_ROOT"*|*fixture/records*)
  records_owner=1
  export SOURCE_CANDIDATE_PROVIDER_FIXTURE="$RETIREMENT_TEST_RECORDS_PROVIDER"
  export SOURCE_CANDIDATE_FIXTURE_ORIGIN='https://github.com/fixture/records.git'
  export SOURCE_CANDIDATE_FIXTURE_REMOTE="$RETIREMENT_TEST_RECORDS_REMOTE"
 esac
fi
if [ "$RETIREMENT_TEST_OUTAGE" = 1 ] || { [ "$RETIREMENT_TEST_OUTAGE" = records ] && [ "$records_owner" = 1 ]; }; then
 case "$PWD" in *source-receiving-*)
  for argument in "$@"; do
   if [ "$argument" = fetch ] && "$RETIREMENT_TEST_NODE" --input-type=module -e 'import {existsSync,readFileSync} from "node:fs"; const f=JSON.parse(process.env.SOURCE_CANDIDATE_PROVIDER_FIXTURE); process.exit(existsSync(f.reviews)&&JSON.parse(readFileSync(f.reviews,"utf8")).reviews.some(row=>row.state==="MERGED")?0:1);'; then
    echo 'original native source readback transport unavailable' >&2; exit 71
   fi
  done
 esac
fi
exec /bin/sh "$RETIREMENT_TEST_GIT_PORT" "$@"
`, {mode:0o700});
  writeFileSync(path.join(bin, 'gh'), `#!/usr/bin/env node
import {execFileSync} from 'node:child_process';
import {appendFileSync} from 'node:fs';
const args=process.argv.slice(2);
if(args[0]==='api'&&args[1]?.includes('/git/commits/'))throw Error('merge receiving must not issue REST commit reads');
const recordsOwner = process.env.RETIREMENT_TEST_RECORDS_ROOT &&
  (process.cwd().startsWith(process.env.RETIREMENT_TEST_RECORDS_ROOT) || process.cwd().startsWith(process.env.RETIREMENT_TEST_RECORDS_PHYSICAL_ROOT) || args.some(arg=>arg.includes('fixture/records')));
const env = {...process.env, ...(recordsOwner ? {SOURCE_CANDIDATE_PROVIDER_FIXTURE:process.env.RETIREMENT_TEST_RECORDS_PROVIDER,
  SOURCE_CANDIDATE_FIXTURE_ORIGIN:'https://github.com/fixture/records.git', SOURCE_CANDIDATE_FIXTURE_REMOTE:process.env.RETIREMENT_TEST_RECORDS_REMOTE} : {})};
const output=String(execFileSync(process.execPath,[process.env.RETIREMENT_TEST_PROVIDER,...args],{encoding:'utf8',env}));
if (!recordsOwner && args[0]==='pr' && args[1]==='merge' && process.env.RETIREMENT_TEST_MUTATE_RECORD) appendFileSync(process.env.RETIREMENT_TEST_MUTATE_RECORD,'\\n');
process.stdout.write(output);
`, {mode:0o700});
  // Keep an explicitly selected canonical Fabrication artifact. Otherwise use
  // the native maker; no counterfeit decoder or node_modules edits.
  assert.ok(process.env.HOUSE_PACKAGE_BINDINGS, 'run with qualified house supplier bindings');
  const bindings = JSON.parse(readFileSync(process.env.HOUSE_PACKAGE_BINDINGS, 'utf8'));
  const maker = JSON.parse(readFileSync(path.join(fabrication, 'package.json'), 'utf8'));
  if(!bindings.packages.some(row => row.name === maker.name))
    bindings.packages.push({name:maker.name, version:maker.version, directory:fabrication});
  const bindingPath = path.join(root, 'house-bindings.json');
  writeFileSync(bindingPath, JSON.stringify(bindings));
  git('remote', 'set-url', 'origin', 'https://github.com/fixture/source.git');
  git('config', `url.${remote}.insteadOf`, 'https://github.com/fixture/source.git');
  const reviewsPath = path.join(root, 'reviews.json');
  const env = {...process.env, PATH:`${bin}:${path.dirname(process.execPath)}:${process.env.PATH}`,
    HOUSE_PACKAGE_BINDINGS:bindingPath,
    NODE_OPTIONS:`--import ${resolver} --max-old-space-size=192`,
    RETIREMENT_TEST_PROVIDER:path.join(fabrication, 'test/fixtures/github-candidate-provider.mjs'),
    RETIREMENT_TEST_NODE:process.execPath,
    RETIREMENT_TEST_OUTAGE:'0',
    RETIREMENT_TEST_GIT_PORT:path.join(fabrication, 'test/fixtures/source-candidate-git-port.sh'),
    SOURCE_CANDIDATE_PROVIDER_FIXTURE:JSON.stringify({selection:{repository:'fixture/source'}, remote, reviews:reviewsPath}),
    SOURCE_CANDIDATE_FIXTURE_ORIGIN:'https://github.com/fixture/source.git', SOURCE_CANDIDATE_FIXTURE_REMOTE:remote,
    GIT_TRACE2_EVENT:path.join(root, 'git-events.jsonl')};
  const recordsRequestPath = path.join(root, 'records-request.json'), recordsOutput = path.join(root, 'records-publication.json');
  const recordPaths = ['data/plan.json', 'data/result.json', 'data/review.json'];
  let recordsRequest;
  if (withRecords) {
    recordsGit('remote', 'set-url', 'origin', 'https://github.com/fixture/records.git');
    recordsGit('config', `url.${recordsRemote}.insteadOf`, 'https://github.com/fixture/records.git');
    writeFileSync(path.join(recordsRepository, 'data/review.json'), JSON.stringify({verdict:'accepted', scope:'reviewed-two'})+'\n', {mode:0o755});
    recordsRequest = {repositoryRoot:recordsRepository, paths:recordPaths, message:'Receive the actual retirement and supporting review', push:true,
      reviewedSource:{revision:recordsRevision, entries:recordPaths.map(path=>({path,absent:true}))}};
    writeFileSync(recordsRequestPath, JSON.stringify(recordsRequest));
    env.RETIREMENT_TEST_RECORDS_ROOT = recordsRepository;
    env.RETIREMENT_TEST_RECORDS_REMOTE = recordsRemote;
    env.RETIREMENT_TEST_RECORDS_PROVIDER = JSON.stringify({selection:{repository:'fixture/records'}, remote:recordsRemote, reviews:path.join(root, 'records-reviews.json')});
    const concurrent = path.join(root, 'records-concurrent');
    raw(root, ['clone', '-q', '--branch', 'main', recordsRemote, concurrent]);
    raw(concurrent, ['config', 'user.name', 'Independent records writer']);
    raw(concurrent, ['config', 'user.email', 'other-records@example.invalid']);
    writeFileSync(path.join(concurrent, 'neighbor.txt'), 'independent records upstream advance\n');
    writeFileSync(path.join(concurrent, 'upstream-only.txt'), 'independent records source\n');
    raw(concurrent, ['add', '.']); raw(concurrent, ['commit', '-qm', 'Concurrent unselected records source']); raw(concurrent, ['push', '-q', 'origin', 'main']);
  }
  const run = ({outage=false, extraArgs=[], recordsReceipt=recordsOutput, mutateRecord, physicalRecordsRoot=recordsRepository, cwd=repository}={}) => {
    const execution = spawnSync(process.execPath, [cli, planPath, '--apply', '--publish', '--output='+output, ...(withRecords ? ['--publish-records='+recordsRequestPath, '--records-output='+recordsReceipt] : []), ...extraArgs],
      {cwd, env:{...env, RETIREMENT_TEST_RECORDS_PHYSICAL_ROOT:physicalRecordsRoot, RETIREMENT_TEST_OUTAGE:outage===true?'1':outage||'0', ...(mutateRecord?{RETIREMENT_TEST_MUTATE_RECORD:path.join(recordsRepository,mutateRecord)}:{})}, encoding:'utf8', timeout:60000, maxBuffer:2*1024*1024});
    return {...execution, result:existsSync(output)?JSON.parse(readFileSync(output,'utf8')):undefined, records:existsSync(recordsOutput)?JSON.parse(readFileSync(recordsOutput,'utf8')):undefined};
  };
  const upstream = (...args) => raw(root, ['--git-dir', remote, ...args]);
  const refs = () => upstream('for-each-ref', '--format=%(refname) %(objectname)');
  const pushes = () => existsSync(env.GIT_TRACE2_EVENT) ? readFileSync(env.GIT_TRACE2_EVENT,'utf8').trim().split('\n').filter(Boolean)
    .map(row=>JSON.parse(row)).filter(row=>row.event==='start'&&row.argv?.includes('push')).length : 0;
  const reviews = () => JSON.parse(readFileSync(reviewsPath,'utf8'));
  const advance = path.join(root,'concurrent');
  raw(root,['clone','-q','--branch','main',remote,advance]);
  raw(advance,['config','user.name','Independent source writer']); raw(advance,['config','user.email','other@example.invalid']);
  writeFileSync(path.join(advance,'neighbor.txt'),'independent upstream advance\n');
  writeFileSync(path.join(advance,'upstream-only.txt'),'independent new source\n');
  if(remoteChange==='blob')writeFileSync(path.join(advance,'lib/legacy/batch/first.md'),'changed original source\n');
  if(remoteChange==='absent')rmSync(path.join(advance,'lib/legacy/batch/first.md'));
  if(remoteChange?.startsWith('relocated')) {
    if(remoteChange==='relocated-edited') writeFileSync(path.join(advance,'lib/legacy/batch/first.md'),'edited after relocation\n');
    mkdirSync(path.join(advance,'moved'));
    renameSync(path.join(advance,'lib/legacy'),path.join(advance,'moved/legacy'));
  }
  raw(advance,['add','.']);
  if(remoteChange==='mode')raw(advance,['update-index','--chmod=+x','lib/legacy/batch/first.md']);
  raw(advance,['commit','-qm','Concurrent unselected source']); raw(advance,['push','-q','origin','main']);
  return {root, repository, remote, env, git, upstream, refs, pushes, reviews, reviewsPath, run, revision, originalRevision, localParent, staged, output, planPath,
    recordsRepository, recordsRemote, recordsGit, recordsHead, recordsStaged, recordsRequest, recordsRequestPath, recordsOutput, recordPaths,
    recordsReviewsPath:path.join(root, 'records-reviews.json'),
    recordsUpstream:(...args)=>raw(root, ['--git-dir', recordsRemote, ...args]),
    recordsBytes:file=>execFileSync('git', ['--git-dir', recordsRemote, 'show', 'main:'+file]),
    recordsRefs:()=>raw(root, ['--git-dir', recordsRemote, 'for-each-ref', '--format=%(refname) %(objectname)'])};
}

function assertLocalCut(f, result) {
  assert.equal(result.landing.state, 'committed');
  assert.equal(f.git('rev-parse','HEAD'), result.landing.commit);
  assert.equal(f.git('show','-s','--format=%P','HEAD'),f.localParent);
  assert.equal(f.git('diff-tree','--no-commit-id','--name-status','-r','HEAD'),
    'D\tlib/legacy/batch/first.md\nD\tlib/legacy/batch/second.md');
  assert.equal(f.git('diff','--cached','--raw','-z'),f.staged);
  assert.equal(readFileSync(path.join(f.repository,'other-writer.txt'),'utf8'),'another writer staged this\n');
  assert.equal(existsSync(path.join(f.repository,'lib/legacy/batch/unreceived.md')),false);
  for(const name of ['first.md','second.md']) assert.equal(existsSync(path.join(f.repository,'lib/legacy/batch',name)),false);
  assert.equal(existsSync(path.join(f.repository,'.git/shallow')),false);
}

function assertReceivedCut(f, result) {
  const publication=result.publication, candidate=publication.candidate;
  assert.equal(publication.ok,true); assert.equal(publication.phase,'landed');
  assert.equal(candidate.receiving.state,'received');
  assert.equal(candidate.receiving.allUnselectedPreserved,true);
  assert.deepEqual(candidate.receiving.entries.map(row=>row.path).sort(),['lib/legacy/batch/first.md','lib/legacy/batch/second.md']);
  assert.ok(candidate.receiving.entries.every(row=>row.after===null));
  assert.equal(f.upstream('show',`${candidate.mergeCommit}:lib/legacy/batch/unreceived.md`),'separate unreceived source');
  assert.equal(f.upstream('show',`${candidate.mergeCommit}:lib/legacy/batch/held.md`),'held authored information');
  assert.equal(f.upstream('show',`${candidate.mergeCommit}:neighbor.txt`),'independent upstream advance');
  assert.equal(f.upstream('show',`${candidate.mergeCommit}:upstream-only.txt`),'independent new source');
  assert.equal(f.upstream('show',`${candidate.mergeCommit}:other-writer.txt`),'original unrelated source');
  assert.equal(f.reviews().reviews.length,1);
}

test('retirement CLI commits and publishes only its reviewed cut through the real maker, then replays without source effects',t=>{
  const f=fixture(t), first=f.run();
  assert.equal(first.status,0,first.stderr||first.stdout);
  assert.deepEqual(first.result.counts,{removed:2});
  assertLocalCut(f,first.result); assertReceivedCut(f,first.result);
  const head=f.git('rev-parse','HEAD'), refs=f.refs(), reviews=readFileSync(f.reviewsPath), pushes=f.pushes();
  const replay=f.run(); assert.equal(replay.status,0,replay.stderr||replay.stdout);
  assert.equal(replay.result.landing.state,'already-landed');
  assert.equal(replay.result.publication.candidate.mergeCommit,first.result.publication.candidate.mergeCommit);
  assert.equal(f.git('rev-parse','HEAD'),head); assert.equal(f.refs(),refs); assert.equal(f.pushes(),pushes);
  assert.deepEqual(readFileSync(f.reviewsPath),reviews); assert.equal(f.git('diff','--cached','--raw','-z'),f.staged);
  assertReceivedCut(f,replay.result);
});

test('retirement CLI retains its completed real merge when receiving fails and honest replay completes the same receipt',t=>{
  const f=fixture(t), failed=f.run({outage:true});
  assert.equal(failed.status,1,failed.stderr||failed.stdout);
  assertLocalCut(f,failed.result);
  const publication=failed.result.publication;
  assert.equal(publication.ok,false); assert.equal(publication.phase,'receiving');
  assert.equal(publication.candidate.landed,true); assert.match(publication.candidate.mergeCommit,/^[0-9a-f]{40}$/u);
  assert.equal(publication.candidate.receiving,undefined);
  assert.equal(f.reviews().reviews[0].mergeCommit,publication.candidate.mergeCommit);
  const head=f.git('rev-parse','HEAD'), refs=f.refs(), reviews=readFileSync(f.reviewsPath), pushes=f.pushes();
  const replay=f.run(); assert.equal(replay.status,0,replay.stderr||replay.stdout);
  assert.equal(replay.result.publication.candidate.mergeCommit,publication.candidate.mergeCommit);
  assert.equal(f.git('rev-parse','HEAD'),head); assert.equal(f.refs(),refs); assert.equal(f.pushes(),pushes);
  assert.deepEqual(readFileSync(f.reviewsPath),reviews); assert.equal(f.git('diff','--cached','--raw','-z'),f.staged);
  assertReceivedCut(f,replay.result);
});

test('a reviewed local commit absent at origin is qualified against actual remote preimages before retirement',t=>{
  const f=fixture(t,{localReview:true}), remoteBefore=f.upstream('rev-parse','main');
  assert.throws(()=>f.upstream('cat-file','-e',f.revision+'^{commit}'),'the reviewed native commit really is absent upstream');
  const first=f.run({cwd:f.root}); assert.equal(first.status,0,first.stderr||JSON.stringify(first.result)||first.stdout);
  assertLocalCut(f,first.result); assertReceivedCut(f,first.result);
  const prepared=first.result.sourcePreparation;
  assert.equal(prepared.planRevision,f.revision);
  assert.equal(prepared.reviewedSource.revision,remoteBefore);
  assert.notEqual(prepared.reviewedSource.revision,f.revision);
  assert.deepEqual(prepared.reviewedSource.entries.map(row=>row.path).sort(),['lib/legacy/batch/first.md','lib/legacy/batch/second.md']);
  assert.equal(prepared.origin,'https://github.com/fixture/source.git');
  const before={head:f.git('rev-parse','HEAD'),refs:f.refs(),pushes:f.pushes(),reviews:readFileSync(f.reviewsPath)};
  const replay=f.run(); assert.equal(replay.status,0,replay.stderr||replay.stdout);
  assert.deepEqual(replay.result.sourcePreparation,prepared);
  assert.equal(replay.result.publication.candidate.mergeCommit,first.result.publication.candidate.mergeCommit);
  assert.deepEqual({head:f.git('rev-parse','HEAD'),refs:f.refs(),pushes:f.pushes(),reviews:readFileSync(f.reviewsPath)},before);
});

for(const remoteChange of ['blob','mode','absent'])test(`remote selected ${remoteChange} mismatch refuses before local deletion or commit`,t=>{
  const f=fixture(t,{localReview:true,remoteChange});
  const before={head:f.git('rev-parse','HEAD'),index:f.git('diff','--cached','--raw','-z'),refs:f.refs(),pushes:f.pushes(),bytes:readFileSync(path.join(f.repository,'lib/legacy/batch/first.md'))};
  const refused=f.run(); assert.notEqual(refused.status,0);
  assert.match(refused.stderr,/source preimage differs/u);
  assert.equal(refused.result,undefined); assert.equal(existsSync(f.reviewsPath),false);
  assert.equal(existsSync(path.join(f.repository,'lib/legacy/batch/second.md')),true);
  assert.deepEqual({head:f.git('rev-parse','HEAD'),index:f.git('diff','--cached','--raw','-z'),refs:f.refs(),pushes:f.pushes(),bytes:readFileSync(path.join(f.repository,'lib/legacy/batch/first.md'))},before);
});

test('unavailable original source refuses publication before retirement while local-only apply stays usable',t=>{
  const f=fixture(t,{localReview:true});
  f.git('remote','remove','origin');
  const head=f.git('rev-parse','HEAD'),index=f.git('diff','--cached','--raw','-z');
  const refused=f.run(); assert.notEqual(refused.status,0); assert.equal(refused.result,undefined);
  assert.equal(f.git('rev-parse','HEAD'),head); assert.equal(f.git('diff','--cached','--raw','-z'),index);
  assert.equal(existsSync(path.join(f.repository,'lib/legacy/batch/first.md')),true);
  const local=spawnSync(process.execPath,[cli,f.planPath,'--apply','--output='+f.output],{encoding:'utf8'});
  assert.equal(local.status,0,local.stderr||local.stdout);
  const result=JSON.parse(readFileSync(f.output,'utf8'));assert.equal(result.landing.state,'committed');
  assert.equal(result.publication,undefined);
});

test('public root consumers prepare before apply, retain both identities and publish through the existing maker',t=>{
  const f=fixture(t,{localReview:true});
  const packageRoot=new URL('../',import.meta.url);
  const declared=JSON.parse(readFileSync(new URL('package.json',packageRoot),'utf8')).exports['.'];
  const entry=new URL(declared,packageRoot).href;
  const code=`
    import assert from 'node:assert/strict';
    import {readFileSync,writeFileSync} from 'node:fs';
    const api=await import(${JSON.stringify(entry)});
    const plan=JSON.parse(readFileSync(${JSON.stringify(f.planPath)},'utf8'));
    const preview=api.retireTrackedLegacyCapabilities({plan});
    const sourcePreparation=await api.prepareTrackedLegacySourcePublication({result:preview});
    for(const name of ['first.md','second.md'])assert.ok(readFileSync(plan.repositoryRoot+'/lib/legacy/batch/'+name).length);
    const result=api.retireTrackedLegacyCapabilities({plan,apply:true});
    result.landing=api.commitTrackedLegacyRetirement({result});
    await assert.rejects(api.publishTrackedLegacyRetirement({result}),/qualified remote source preparation required/);
    result.sourcePreparation=sourcePreparation;
    writeFileSync(${JSON.stringify(f.output)},JSON.stringify(result));
    result.publication=await api.publishTrackedLegacyRetirement({result});
    writeFileSync(${JSON.stringify(f.output)},JSON.stringify(result));
    assert.equal(result.publication.ok,true);
  `;
  const run=spawnSync(process.execPath,['--input-type=module','-e',code],{cwd:f.root,env:f.env,encoding:'utf8',timeout:60000,maxBuffer:2*1024*1024});
  assert.equal(run.status,0,run.stderr||run.stdout);
  const result=JSON.parse(readFileSync(f.output,'utf8'));
  assert.equal(result.sourcePreparation.planRevision,f.revision);
  assert.notEqual(result.sourcePreparation.reviewedSource.revision,f.revision);
  assertLocalCut(f,result);assertReceivedCut(f,result);
});

test('explicit upstream relocation preserves native review and staging and receives only the mapped source cut',t=>{
  const f=fixture(t,{remoteChange:'relocated'});
  const before={head:f.git('rev-parse','HEAD'),staging:f.git('diff','--cached','--raw','-z'),refs:f.refs(),pushes:f.pushes()};
  const unmapped=f.run(); assert.notEqual(unmapped.status,0);
  assert.match(unmapped.stderr,/source preimage differs/u);
  assert.equal(existsSync(f.output),false);
  assert.deepEqual({head:f.git('rev-parse','HEAD'),staging:f.git('diff','--cached','--raw','-z'),refs:f.refs(),pushes:f.pushes()},before);
  const plan=JSON.parse(readFileSync(f.planPath,'utf8')); plan.sourceLegacyRoot='moved/legacy';
  writeFileSync(f.planPath,JSON.stringify(plan));
  const applied=f.run(); assert.equal(applied.status,0,applied.stderr||applied.stdout);
  assertLocalCut(f,applied.result);
  assert.equal(applied.result.legacyRoot,'lib/legacy');
  assert.equal(applied.result.sourceLegacyRoot,'moved/legacy');
  assert.equal(applied.result.sourcePreparation.sourceLegacyRoot,'moved/legacy');
  const candidate=applied.result.publication.candidate;
  assert.equal(candidate.receiving.allUnselectedPreserved,true);
  assert.deepEqual(candidate.receiving.entries.map(x=>x.path).sort(),['moved/legacy/batch/first.md','moved/legacy/batch/second.md']);
  assert(candidate.receiving.entries.every(x=>x.after===null));
  assert.equal(f.upstream('show','main:moved/legacy/batch/unreceived.md'),'separate unreceived source');
  assert.equal(f.upstream('show','main:moved/legacy/batch/held.md'),'held authored information');
  const landed={head:f.git('rev-parse','HEAD'),refs:f.refs(),pushes:f.pushes()};
  const replay=f.run(); assert.equal(replay.status,0,replay.stderr||replay.stdout);
  assert.equal(replay.result.publication.candidate.mergeCommit,candidate.mergeCommit);
  assert.deepEqual({head:f.git('rev-parse','HEAD'),refs:f.refs(),pushes:f.pushes()},landed);
  plan.sourceLegacyRoot='another/legacy'; writeFileSync(f.planPath,JSON.stringify(plan));
  const changed=f.run(); assert.notEqual(changed.status,0);
  assert.match(changed.stderr,/retained receipt belongs to another retirement/u);
  assert.deepEqual({head:f.git('rev-parse','HEAD'),refs:f.refs(),pushes:f.pushes()},landed);
});

test('a mapped upstream edit refuses before any local retirement effect',t=>{
  const f=fixture(t,{remoteChange:'relocated-edited'}),plan=JSON.parse(readFileSync(f.planPath,'utf8'));
  plan.sourceLegacyRoot='moved/legacy'; writeFileSync(f.planPath,JSON.stringify(plan));
  const before={head:f.git('rev-parse','HEAD'),staging:f.git('diff','--cached','--raw','-z'),refs:f.refs(),pushes:f.pushes()};
  const refused=f.run(); assert.notEqual(refused.status,0);
  assert.match(refused.stderr,/source preimage differs/u);
  assert.equal(existsSync(f.output),false);
  assert.deepEqual({head:f.git('rev-parse','HEAD'),staging:f.git('diff','--cached','--raw','-z'),refs:f.refs(),pushes:f.pushes()},before);
  for(const p of ['first.md','second.md']) assert(existsSync(path.join(f.repository,'lib/legacy/batch',p)));
});

function assertRecordsReceived(f, received) {
  assert.equal(received.ok, true);
  assert.equal(received.phase, 'landed');
  assert.equal(received.candidate.receiving.state, 'received');
  assert.equal(received.candidate.receiving.allUnselectedPreserved, true);
  assert.deepEqual(received.candidate.receiving.entries.map(row=>row.path).sort(), [...f.recordPaths].sort());
  assert.equal(received.recordFiles.length, f.recordPaths.length);
  for (const name of f.recordPaths) {
    assert.deepEqual(f.recordsBytes(name), readFileSync(path.join(f.recordsRepository, name)));
    const snapshot = received.recordFiles.find(row=>row.path===name);
    const entry = received.candidate.receiving.entries.find(row=>row.path===name);
    assert.equal(entry.after.mode, snapshot.mode);
    assert.equal(entry.after.object, snapshot.blob);
  }
  assert.equal(f.recordsUpstream('show', 'main:records-unreceived.txt'), 'separate records native absence');
  assert.equal(f.recordsUpstream('show', 'main:neighbor.txt'), 'independent records upstream advance');
  assert.equal(f.recordsUpstream('show', 'main:upstream-only.txt'), 'independent records source');
  assert.equal(f.recordsUpstream('show', 'main:other-writer.txt'), 'original records source');
  assert.equal(f.recordsGit('rev-parse', 'HEAD'), f.recordsHead);
  assert.equal(f.recordsGit('diff', '--cached', '--raw', '-z'), f.recordsStaged);
  assert.equal(readFileSync(path.join(f.recordsRepository, 'other-writer.txt'), 'utf8'), 'unrelated records staging\n');
  assert.equal(existsSync(path.join(f.recordsRepository, 'records-unreceived.txt')), false);
  assert.equal(existsSync(path.join(f.recordsRepository, '.git/shallow')), false);
  assert.equal(JSON.parse(readFileSync(f.recordsReviewsPath, 'utf8')).reviews.length, 1);
}

function effectsSnapshot(f) {
  return {head:f.git('rev-parse','HEAD'), recordsHead:f.recordsGit('rev-parse','HEAD'),
    refs:f.refs(), recordsRefs:f.recordsRefs(), pushes:f.pushes(),
    reviews:existsSync(f.reviewsPath)?readFileSync(f.reviewsPath):null,
    recordsReviews:existsSync(f.recordsReviewsPath)?readFileSync(f.recordsReviewsPath):null,
    staging:f.git('diff','--cached','--raw','-z'), recordsStaging:f.recordsGit('diff','--cached','--raw','-z')};
}

function automaticBatch(f) {
  const outputs={plan:'data/compiled-plan.json',receiving:'data/batch-receiving.json',result:'data/result.json',
    publicationRequest:'data/automatic-request.json',publicationReceipt:'data/automatic-receipt.json'};
  const batch={kind:'legacy-capability-retirement-batch/v1',id:'automatic-record-lease',repositoryRoot:f.recordsRepository,
    plans:['data/plan.json'],supportingRecords:[],outputs,publication:{message:'Receive automatically prepared retirement records'}};
  const file=path.join(f.recordsRepository,'data/batch.json');
  writeFileSync(file,JSON.stringify(batch));
  const run=(apply=false)=>spawnSync(process.execPath,[cli,file,...(apply?['--apply','--publish']:[])],
    {cwd:f.root,env:{...f.env,RETIREMENT_TEST_RECORDS_PHYSICAL_ROOT:f.recordsRepository,RETIREMENT_TEST_OUTAGE:'0'},
      encoding:'utf8',timeout:60000,maxBuffer:2*1024*1024});
  return {batch,file,run,at:key=>path.join(f.recordsRepository,outputs[key])};
}

test('batch captures the actual remote lease, resumes partial preparation, publishes and replays without new effects',t=>{
  const f=fixture(t,{withRecords:true}), b=automaticBatch(f);
  const source=f.recordsUpstream('rev-parse','main'), before=effectsSnapshot(f);
  assert.notEqual(source,f.recordsGit('rev-parse','HEAD'));
  const prepared=b.run(); assert.equal(prepared.status,0,prepared.stderr||prepared.stdout);
  const request=readFileSync(b.at('publicationRequest'));
  assert.equal(JSON.parse(request).reviewedSource.revision,source);
  assert.deepEqual(JSON.parse(request).reviewedSource.entries,
    [b.batch.outputs.plan,b.batch.outputs.receiving,b.batch.outputs.result].map(path=>({path,absent:true})));
  assert.deepEqual(effectsSnapshot(f),before);
  assert.equal(existsSync(b.at('result')),true,'preview owns the ordinary result');
  rmSync(b.at('plan'));
  const partial=b.run(); assert.equal(partial.status,0,partial.stderr||partial.stdout);
  assert.deepEqual(readFileSync(b.at('publicationRequest')),request);
  const applied=b.run(true); assert.equal(applied.status,0,applied.stderr||applied.stdout);
  const result=JSON.parse(readFileSync(b.at('result'))), receipt=JSON.parse(readFileSync(b.at('publicationReceipt')));
  assertLocalCut(f,result); assertReceivedCut(f,result);
  assert.equal(receipt.ok,true);
  assert.equal(receipt.candidate.receiving.allUnselectedPreserved,true);
  for(const key of ['plan','receiving','result']) assert.deepEqual(f.recordsBytes(b.batch.outputs[key]),readFileSync(b.at(key)));
  const fixed=Object.fromEntries(Object.keys(b.batch.outputs).map(key=>[key,readFileSync(b.at(key))]));
  const landed=effectsSnapshot(f);
  assert.notEqual(f.recordsUpstream('rev-parse','main'),source);
  const replay=b.run(true); assert.equal(replay.status,0,replay.stderr||replay.stdout);
  assert.deepEqual(effectsSnapshot(f),landed);
  for(const key of Object.keys(fixed)) assert.deepEqual(readFileSync(b.at(key)),fixed[key]);
  writeFileSync(b.file,JSON.stringify({...b.batch,publication:{message:'A different operation'}}));
  const changed=b.run(true); assert.notEqual(changed.status,0);
  assert.match(changed.stderr,/existing prepared bytes changed/u);
  assert.deepEqual(effectsSnapshot(f),landed);
});

test('automatic batch lease refuses occupied source outputs and unavailable origin before preparation or retirement',async t=>{
  for(const defect of ['occupied','unavailable']) await t.test(defect,t=>{
    const f=fixture(t,{withRecords:true}), b=automaticBatch(f);
    if(defect==='occupied') {
      const writer=path.join(f.root,'occupied-record-writer');
      execFileSync('git',['clone','-q','--branch','main',f.recordsRemote,writer]);
      mkdirSync(path.join(writer,'data'));
      writeFileSync(path.join(writer,b.batch.outputs.plan),'another operation owns this record\n');
      execFileSync('git',['-C',writer,'add','data/compiled-plan.json']);
      execFileSync('git',['-C',writer,'-c','user.name=Other writer','-c','user.email=other@example.invalid','commit','-qm','Occupied destination']);
      execFileSync('git',['-C',writer,'push','-q','origin','main']);
    } else f.recordsGit('remote','set-url','origin',path.join(f.root,'missing-source.git'));
    const before=effectsSnapshot(f), refused=b.run(true);
    assert.notEqual(refused.status,0,refused.stderr||refused.stdout);
    if(defect==='occupied') assert.match(refused.stderr,/fresh batch record already exists at source/u);
    assert.deepEqual(effectsSnapshot(f),before);
    for(const key of Object.keys(b.batch.outputs)) assert.equal(existsSync(b.at(key)),false);
    for(const file of ['first.md','second.md']) assert.equal(existsSync(path.join(f.repository,'lib/legacy/batch',file)),true);
  });
});

test('completed record publication survives a physical owner move without effects or receipt rewrites',t=>{
  const f=fixture(t,{withRecords:true}), first=f.run();
  assert.equal(first.status,0,first.stderr||first.stdout);
  const fixed=readFileSync(f.output), receipt=readFileSync(f.recordsOutput), effects=effectsSnapshot(f);
  const physicalRecordsRoot=f.recordsRepository+'-physical';
  renameSync(f.recordsRepository,physicalRecordsRoot); symlinkSync(physicalRecordsRoot,f.recordsRepository,'dir');
  assert.equal(f.recordsGit('rev-parse','--show-toplevel'),physicalRecordsRoot);
  const outage=f.run({physicalRecordsRoot,outage:'records'});
  assert.equal(outage.status,1,outage.stderr||outage.stdout);
  assert.equal(JSON.parse(outage.stdout).recordsPublication.ok,false);
  assert.equal(JSON.parse(outage.stdout).recordsPublication.phase,'receiving');
  assert.deepEqual(readFileSync(f.output),fixed);
  assert.deepEqual(readFileSync(f.recordsOutput),receipt);
  assert.deepEqual(effectsSnapshot(f),effects);
  const replay=f.run({physicalRecordsRoot});
  assert.equal(replay.status,0,replay.stderr||replay.stdout);
  assert.deepEqual(readFileSync(f.output),fixed);
  assert.deepEqual(readFileSync(f.recordsOutput),receipt);
  assert.deepEqual(effectsSnapshot(f),effects);
  assertRecordsReceived(f,replay.records);
  const newReceipt=path.join(f.root,'not-yet-published-records.json');
  const fresh=f.run({physicalRecordsRoot,recordsReceipt:newReceipt});
  assert.notEqual(fresh.status,0);
  assert.match(fresh.stderr,/record repositoryRoot must be its actual Git root/u);
  assert.equal(existsSync(newReceipt),false);
  assert.deepEqual(readFileSync(f.output),fixed);
  assert.deepEqual(readFileSync(f.recordsOutput),receipt);
  assert.deepEqual(effectsSnapshot(f),effects);
});

// Two genuine source owners are routed through the unchanged provider/Git
// fixtures. Neither source receives the other owner's unrelated local state.
test('one CLI retires and receives records at their own source owner, then replays the byte-identical completed result',t=>{
  const f=fixture(t,{withRecords:true}), first=f.run();
  assert.equal(first.status,0,first.stderr||first.stdout);
  assertLocalCut(f,first.result); assertReceivedCut(f,first.result); assertRecordsReceived(f,first.records);
  assert.deepEqual(first.result.counts,{removed:2});
  assert.equal(first.result.recordsPublication,undefined,'published result must not refer to its own record-publication receipt');
  const summary=JSON.parse(first.stdout);
  assert.equal(summary.recordsPublication.ok,true);
  assert.equal(summary.recordsPublication.output,f.recordsOutput);
  const fixed=readFileSync(f.output), effects=effectsSnapshot(f);
  const replay=f.run(); assert.equal(replay.status,0,replay.stderr||replay.stdout);
  assert.deepEqual(readFileSync(f.output),fixed);
  assert.deepEqual(effectsSnapshot(f),effects);
  assert.equal(replay.result.landing.state,'committed','record replay must reuse the completed retirement rather than recalculate it');
  assert.equal(replay.records.candidate.mergeCommit,first.records.candidate.mergeCommit);
  assertRecordsReceived(f,replay.records);

  // A retained receipt binds the exact published record bytes, owner and cut.
  // Refuse changed support/result material or a changed path set before replay.
  for (const name of ['data/plan.json','data/review.json','data/result.json']) {
    const file=path.join(f.recordsRepository,name), original=readFileSync(file);
    writeFileSync(file,Buffer.concat([original,Buffer.from('\n')]));
    const before=effectsSnapshot(f), refused=f.run();
    assert.notEqual(refused.status,0,'mutated retained record must refuse replay');
    assert.match(refused.stderr,/retained record publication owner, paths or bytes differ/u);
    assert.deepEqual(effectsSnapshot(f),before);
    writeFileSync(file,original);
  }
  writeFileSync(f.recordsRequestPath,JSON.stringify({...f.recordsRequest,paths:f.recordPaths.slice(0,2),
    reviewedSource:{...f.recordsRequest.reviewedSource,entries:f.recordsRequest.reviewedSource.entries.slice(0,2)}}));
  const refused=f.run(); assert.notEqual(refused.status,0);
  assert.match(refused.stderr,/retained record publication owner, paths or bytes differ/u);
  assert.deepEqual(effectsSnapshot(f),effects);
  assert.deepEqual(readFileSync(f.output),fixed);
});

test('record merge readback outage retains both actual merges and replay receives only the original record candidate',t=>{
  const f=fixture(t,{withRecords:true}), failed=f.run({outage:'records'});
  assert.equal(failed.status,1,failed.stderr||failed.stdout);
  assertLocalCut(f,failed.result); assertReceivedCut(f,failed.result);
  assert.equal(failed.records.ok,false); assert.equal(failed.records.phase,'receiving');
  assert.equal(failed.records.candidate.landed,true);
  assert.match(failed.records.candidate.mergeCommit,/^[0-9a-f]{40}$/u);
  assert.equal(failed.records.candidate.receiving,undefined);
  assert.equal(JSON.parse(readFileSync(f.recordsReviewsPath,'utf8')).reviews[0].mergeCommit,failed.records.candidate.mergeCommit);
  const fixed=readFileSync(f.output), effects=effectsSnapshot(f);
  assert.deepEqual(f.recordsBytes('data/result.json'),fixed,'actual records merge contains the fixed successful retirement');
  const replay=f.run(); assert.equal(replay.status,0,replay.stderr||replay.stdout);
  assert.deepEqual(effectsSnapshot(f),effects);
  assert.deepEqual(readFileSync(f.output),fixed);
  assert.equal(replay.result.publication.candidate.mergeCommit,failed.result.publication.candidate.mergeCommit);
  assert.equal(replay.records.candidate.commit,failed.records.candidate.commit);
  assert.equal(replay.records.candidate.mergeCommit,failed.records.candidate.mergeCommit);
  assertRecordsReceived(f,replay.records);
});

test('supporting record changed after preflight is refused before record-source publication',t=>{
  const f=fixture(t,{withRecords:true}), recordsRefs=f.recordsRefs();
  const failed=f.run({mutateRecord:'data/review.json'});
  assert.equal(failed.status,1,failed.stderr||failed.stdout);
  assert.match(failed.stderr,/retirement input records changed before publication/u);
  assertLocalCut(f,failed.result); assertReceivedCut(f,failed.result);
  assert.deepEqual(failed.result.counts,{removed:2});
  assert.equal(f.recordsRefs(),recordsRefs);
  assert.equal(existsSync(f.recordsReviewsPath),false);
  assert.equal(existsSync(f.recordsOutput),false);
  assert.equal(f.recordsGit('rev-parse','HEAD'),f.recordsHead);
  assert.equal(f.recordsGit('diff','--cached','--raw','-z'),f.recordsStaged);
});

test('record destination, owner, exact cut and canonical request are checked before any retirement effects',async t=>{
  const cases = [
    ['unusable receipt destination',f=>({recordsReceipt:path.join(f.root,'missing','receipt.json')})],
    ['non-owner repository root',f=>{writeFileSync(f.recordsRequestPath,JSON.stringify({...f.recordsRequest,repositoryRoot:path.join(f.recordsRepository,'data')}));return [];}],
    ['missing exact result',f=>{const request={...f.recordsRequest,paths:['data/plan.json','data/review.json'],
      reviewedSource:{...f.recordsRequest.reviewedSource,entries:f.recordsRequest.reviewedSource.entries.filter(row=>row.path!=='data/result.json')}};
      writeFileSync(f.recordsRequestPath,JSON.stringify(request));return [];}],
    ['receipt inside publication cut',f=>({recordsReceipt:path.join(f.recordsRepository,'data/result.json')})],
    ['malformed reviewed preimage',f=>{writeFileSync(f.recordsRequestPath,JSON.stringify({...f.recordsRequest,
      reviewedSource:{revision:f.recordsRequest.reviewedSource.revision,entries:[{path:'data/plan.json',absent:true}]}}));return [];}],
    ['result hardlinked to plan',f=>{linkSync(f.planPath,f.output);return [];}],
    ['linked record body',f=>{const file=path.join(f.recordsRepository,'data/review.json');
      rmSync(file); symlinkSync(f.planPath,file); return [];}],
    ['receipt alias of published result',f=>{const alias=path.join(f.root,'receipt-alias');
      symlinkSync(path.join(f.recordsRepository,'data'),alias,'dir'); return {recordsReceipt:path.join(alias,'result.json')};}],
    ['escaping record path',f=>{writeFileSync(f.recordsRequestPath,JSON.stringify({...f.recordsRequest,paths:[...f.recordPaths,'../outside.json']}));return [];}]
  ];
  for (const [name,change] of cases) await t.test(name,t=>{
    const f=fixture(t,{withRecords:true}), before=effectsSnapshot(f), changed=change(f), existingResult=existsSync(f.output)?readFileSync(f.output):null, refused=f.run(Array.isArray(changed)?{extraArgs:changed}:changed);
    assert.notEqual(refused.status,0,refused.stderr||refused.stdout);
    assert.deepEqual(effectsSnapshot(f),before);
    for(const file of ['first.md','second.md']) assert.equal(existsSync(path.join(f.repository,'lib/legacy/batch',file)),true);
    if(existingResult) assert.deepEqual(readFileSync(f.output),existingResult);
    else assert.equal(existsSync(f.output),false);
    assert.equal(existsSync(f.recordsOutput),false);
  });
});
