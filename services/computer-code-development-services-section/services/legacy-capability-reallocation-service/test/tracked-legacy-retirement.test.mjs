import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, symlinkSync, rmSync, chmodSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import test from 'node:test';
import {inventoryTrackedLegacyCapabilities, retireTrackedLegacyCapabilities} from '../src/legacy-capability-reallocation.mjs';

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'legacy-retirement-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  const git = (...args) => execFileSync('git', ['-C', root, ...args], {stdio: ['ignore', 'pipe', 'pipe']}).toString().trim();
  git('init'); git('config', 'user.name', 'Test'); git('config', 'user.email', 'test@example.invalid');
  mkdirSync(join(root, 'lib/legacy/snapshot'), {recursive: true}); mkdirSync(join(root, 'living'));
  writeFileSync(join(root, 'living/tool.mjs'), 'export const capability = true;\n');
  for (const name of ['tool.mts', 'proof.lean', 'unique.md', 'é\nname.mjs', 'edited.mjs']) writeFileSync(join(root, 'lib/legacy/snapshot', name), name + '\n');
  symlinkSync('../../living/tool.mjs', join(root, 'lib/legacy/link'));
  git('add', '.'); git('commit', '-m', 'source');
  const revision = git('rev-parse', 'HEAD');
  const plan = {kind: 'legacy-capability-retirement-plan/v1', repositoryRoot: root, legacyRoot: 'lib/legacy', revision, capabilities: [
    {id: 'tools', disposition: 'covered', reason: 'living replacement independently reviewed', sourcePaths: ['snapshot/tool.mts', 'snapshot/é\nname.mjs', 'snapshot/edited.mjs'], evidence: [{path: 'living/tool.mjs'}]},
    {id: 'lean', disposition: 'deprecated', reason: 'deprecated proof system', authorization: 'explicit Leader instruction', sourcePaths: ['snapshot/proof.lean']}
  ]};
  return {root, git, plan};
}

test('native Git paths, light inventory, preview and selective retirement preserve edits, unknowns and untracked data', t => {
  const {root, plan} = fixture(t);
  const inventory = inventoryTrackedLegacyCapabilities(plan);
  assert.equal(inventory.entries.length, 6);
  assert(inventory.entries.some(x => x.path === 'snapshot/é\nname.mjs'));
  writeFileSync(join(root, 'lib/legacy/snapshot/edited.mjs'), 'local edit');
  writeFileSync(join(root, 'lib/legacy/snapshot/untracked.md'), 'unique');
  const preview = retireTrackedLegacyCapabilities({plan});
  assert.deepEqual(preview.counts, {eligible: 3, held: 1});
  assert(existsSync(join(root, 'lib/legacy/snapshot/tool.mts')));
  const applied = retireTrackedLegacyCapabilities({plan, apply: true});
  assert.deepEqual(applied.counts, {removed: 3, held: 1});
  for (const name of ['unique.md', 'untracked.md', 'edited.mjs']) assert(existsSync(join(root, 'lib/legacy/snapshot', name)));
  assert.equal(readFileSync(join(root, 'lib/legacy/snapshot/edited.mjs'), 'utf8'), 'local edit');
  assert.deepEqual(retireTrackedLegacyCapabilities({plan, apply: true}).counts, {absent: 3, held: 1});
});

test('declarations reject unknown and duplicate source before any deletion', t => {
  const {root, plan} = fixture(t);
  plan.capabilities[1].sourcePaths.push('snapshot/unknown.mjs');
  assert.throws(() => retireTrackedLegacyCapabilities({plan, apply: true}), /unknown/);
  assert(existsSync(join(root, 'lib/legacy/snapshot/tool.mts')));
  plan.capabilities[1].sourcePaths = ['snapshot/tool.mts'];
  assert.throws(() => retireTrackedLegacyCapabilities({plan, apply: true}), /repeated/);
});

test('missing/revised evidence and staged source changes hold their capability without losing other work', t => {
  const {root, git, plan} = fixture(t);
  writeFileSync(join(root, 'lib/legacy/snapshot/tool.mts'), 'staged change'); git('add', 'lib/legacy/snapshot/tool.mts');
  assert.match(retireTrackedLegacyCapabilities({plan}).outcomes[0].reason, /index differs/);
  plan.capabilities[0].evidence[0].sha256 = '0'.repeat(64);
  assert.deepEqual(retireTrackedLegacyCapabilities({plan, apply: true}).counts, {held: 3, removed: 1});
  assert(existsSync(join(root, 'lib/legacy/snapshot/tool.mts')));
});

test('symlink ancestor cannot redirect removal into living code', t => {
  const {root, plan} = fixture(t);
  rmSync(join(root, 'lib/legacy/snapshot'), {recursive: true});
  symlinkSync('../../living', join(root, 'lib/legacy/snapshot'));
  writeFileSync(join(root, 'living/tool.mts'), 'tool.mts\n');
  assert.deepEqual(retireTrackedLegacyCapabilities({plan, apply: true}).counts, {held: 4});
  assert(existsSync(join(root, 'living/tool.mts')));
});

test('root enumeration, mutable revisions and legacy evidence refuse', t => {
  const {plan} = fixture(t);
  assert.throws(() => inventoryTrackedLegacyCapabilities({...plan, legacyRoot: '.'}), /path/);
  assert.throws(() => retireTrackedLegacyCapabilities({plan: {...plan, revision: 'HEAD'}}), /immutable/);
  plan.capabilities[0].evidence = [{path: 'lib/legacy/snapshot/unique.md'}];
  assert.deepEqual(retireTrackedLegacyCapabilities({plan}).counts, {held: 3, eligible: 1});
});

test('native owner execute bit preserves locally edited executable modes', t => {
  const {root, git, plan} = fixture(t);
  const path = join(root, 'lib/legacy/snapshot/tool.mts');
  chmodSync(path, 0o755); git('add', 'lib/legacy/snapshot/tool.mts'); git('commit', '-m', 'executable source');
  plan.revision = git('rev-parse', 'HEAD');
  chmodSync(path, 0o654);
  assert.match(git('diff', '--summary'), /100755 => 100644/);
  assert.match(retireTrackedLegacyCapabilities({plan, apply: true}).outcomes[0].reason, /mode differ/);
  assert(existsSync(path));
});

test('landed deletion remains idempotent while recreated untracked source survives', t => {
  const {root, git, plan} = fixture(t);
  assert.deepEqual(retireTrackedLegacyCapabilities({plan, apply: true}).counts, {removed: 4});
  git('add', '-u'); git('commit', '-m', 'land reviewed retirement');
  assert.deepEqual(retireTrackedLegacyCapabilities({plan, apply: true}).counts, {absent: 4});
  writeFileSync(join(root, 'lib/legacy/snapshot/tool.mts'), 'new untracked source');
  const received = retireTrackedLegacyCapabilities({plan, apply: true});
  assert.deepEqual(received.counts, {held: 1, absent: 3});
  assert.match(received.outcomes[0].reason, /untracked/);
  assert.equal(readFileSync(join(root, 'lib/legacy/snapshot/tool.mts'), 'utf8'), 'new untracked source');
});

function separateLivingOwner(t) {
  const root = mkdtempSync(join(tmpdir(), 'legacy-evidence-owner-'));
  t.after(() => rmSync(root, {recursive:true, force:true}));
  const git = (...args) => execFileSync('git', ['-C', root, ...args], {stdio:['ignore','pipe','pipe']}).toString().trim();
  git('init'); git('config','user.name','Living owner'); git('config','user.email','owner@example.invalid');
  mkdirSync(join(root,'src'));
  const body = 'export function receiveCapability(value) { return {received: value}; }\n';
  writeFileSync(join(root,'src/receiver.mjs'),body);
  git('add','.'); git('commit','-m','Living ordinary receiver');
  return {root, git, body, sha256:createHash('sha256').update(body).digest('hex')};
}

test('separate actual repository evidence receives an exact legacy cut without changing living code or neighboring sources', t => {
  const {root, git, plan} = fixture(t), owner = separateLivingOwner(t);
  plan.capabilities = [{...plan.capabilities[0], sourcePaths:['snapshot/tool.mts'],
    evidence:[{repositoryRoot:owner.root, path:'src/receiver.mjs', sha256:owner.sha256}]}];
  const ownerHead = owner.git('rev-parse','HEAD'), ownerIndex = readFileSync(join(owner.root,'.git/index'));
  const sourceHead = git('rev-parse','HEAD');
  const preview = retireTrackedLegacyCapabilities({plan});
  assert.deepEqual(preview.counts,{eligible:1});
  assert(existsSync(join(root,'lib/legacy/snapshot/tool.mts')));
  assert.deepEqual(preview.capabilities[0].witnesses,[{repositoryRoot:owner.root,path:'src/receiver.mjs',sha256:owner.sha256}]);
  const applied = retireTrackedLegacyCapabilities({plan,apply:true});
  assert.deepEqual(applied.counts,{removed:1});
  assert.equal(existsSync(join(root,'lib/legacy/snapshot/tool.mts')),false);
  for(const name of ['proof.lean','unique.md','é\nname.mjs','edited.mjs']) assert(existsSync(join(root,'lib/legacy/snapshot',name)));
  assert.equal(git('rev-parse','HEAD'),sourceHead);
  assert.equal(readFileSync(join(owner.root,'src/receiver.mjs'),'utf8'),owner.body);
  assert.equal(owner.git('rev-parse','HEAD'),ownerHead);
  assert.deepEqual(readFileSync(join(owner.root,'.git/index')),ownerIndex);
  assert.equal(owner.git('diff','--name-only'),'');
});

for(const defect of ['wrong-root','relative-escape','symlink-file','symlink-parent','wrong-hash','legacy-evidence']) {
  test(`separate repository ${defect} evidence holds the reviewed sources without altering either owner`, t => {
    const {root, git, plan} = fixture(t), owner = separateLivingOwner(t);
    const evidence = {repositoryRoot:owner.root,path:'src/receiver.mjs',sha256:owner.sha256};
    let reason;
    if(defect==='wrong-root') {
      evidence.repositoryRoot=join(owner.root,'src'); evidence.path='receiver.mjs'; reason=/actual Git root/;
    } else if(defect==='relative-escape') {
      evidence.path='../'+owner.root.split('/').at(-1)+'/src/receiver.mjs'; reason=/repository-relative path/;
    } else if(defect==='symlink-file') {
      symlinkSync('receiver.mjs',join(owner.root,'src/alias.mjs'));
      evidence.path='src/alias.mjs'; reason=/actual living file/;
    } else if(defect==='symlink-parent') {
      symlinkSync('src',join(owner.root,'linked-source'));
      evidence.path='linked-source/receiver.mjs'; reason=/symbolic-link ancestor/;
    } else if(defect==='wrong-hash') {
      evidence.sha256='0'.repeat(64); reason=/living evidence changed/;
    } else {
      mkdirSync(join(owner.root,'legacy')); writeFileSync(join(owner.root,'legacy/receiver.mjs'),owner.body);
      evidence.path='legacy/receiver.mjs'; reason=/evidence points into legacy/;
    }
    plan.capabilities=[{...plan.capabilities[0],sourcePaths:['snapshot/tool.mts','snapshot/edited.mjs'],evidence:[evidence]}];
    const sourceHead=git('rev-parse','HEAD'), sourceIndex=readFileSync(join(root,'.git/index'));
    const ownerHead=owner.git('rev-parse','HEAD'), ownerIndex=readFileSync(join(owner.root,'.git/index'));
    const applied=retireTrackedLegacyCapabilities({plan,apply:true});
    assert.deepEqual(applied.counts,{held:2});
    for(const outcome of applied.outcomes) assert.match(outcome.reason,reason);
    assert.match(applied.capabilities[0].failure,reason);
    for(const name of ['tool.mts','edited.mjs']) assert.equal(readFileSync(join(root,'lib/legacy/snapshot',name),'utf8'),name+'\n');
    assert.equal(git('rev-parse','HEAD'),sourceHead); assert.deepEqual(readFileSync(join(root,'.git/index')),sourceIndex);
    assert.equal(readFileSync(join(owner.root,'src/receiver.mjs'),'utf8'),owner.body);
    assert.equal(owner.git('rev-parse','HEAD'),ownerHead); assert.deepEqual(readFileSync(join(owner.root,'.git/index')),ownerIndex);
  });
}
