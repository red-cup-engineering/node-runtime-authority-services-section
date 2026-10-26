import assert from 'node:assert/strict';
import {execFileSync, spawnSync} from 'node:child_process';
import {mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, rmSync, chmodSync, symlinkSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import test from 'node:test';

const cli = fileURLToPath(new URL('../scripts/retire-tracked-legacy-capabilities.mjs', import.meta.url));
const names = ['ordinary.mjs', 'é\nname.mjs', '[ab]*.mjs'];
const rows = text => text.split('\0').filter(Boolean).sort();

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'legacy-retirement-cli-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  const git = (...args) => execFileSync('git', ['-C', root, ...args], {stdio: ['ignore', 'pipe', 'pipe']}).toString();
  git('init'); git('config', 'user.name', 'Test'); git('config', 'user.email', 'test@example.invalid');
  mkdirSync(join(root, 'hooks')); git('config', 'core.hooksPath', join(root, 'hooks'));
  mkdirSync(join(root, 'lib/legacy/batch'), {recursive: true}); mkdirSync(join(root, 'living'));
  writeFileSync(join(root, 'living/tool.mjs'), 'export const capability = true;\n');
  writeFileSync(join(root, 'unrelated.txt'), 'original\n');
  for (const name of [...names, 'a-match.mjs']) writeFileSync(join(root, 'lib/legacy/batch', name), name + '\n');
  git('add', '.'); git('commit', '-m', 'source');
  const revision = git('rev-parse', 'HEAD').trim();
  const paths = names.map(name => 'lib/legacy/batch/' + name);
  const plan = {kind: 'legacy-capability-retirement-plan/v1', repositoryRoot: root, legacyRoot: 'lib/legacy', revision,
    capabilities: [{id: 'covered', disposition: 'covered', reason: 'actual living replacement reviewed',
      sourcePaths: names.map(name => 'batch/' + name), evidence: [{path: 'living/tool.mjs'}]}]};
  const planPath = join(root, 'plan.json'), outputPath = join(root, 'result.json');
  writeFileSync(planPath, JSON.stringify(plan));
  const run = (...options) => {
    const process = spawnSync(globalThis.process.execPath, [cli, planPath, ...options, '--output=' + outputPath], {encoding: 'utf8'});
    return {...process, result: existsSync(outputPath) ? JSON.parse(readFileSync(outputPath, 'utf8')) : undefined};
  };
  return {root, git, run, revision, paths};
}

test('ordinary CLI apply commits only exact reviewed paths and preserves unrelated staged work', t => {
  const {root, git, run, revision, paths} = fixture(t);
  writeFileSync(join(root, 'unrelated.txt'), 'staged unrelated edit\n');
  writeFileSync(join(root, 'unrelated-new.txt'), 'staged unrelated new file\n');
  git('add', 'unrelated.txt', 'unrelated-new.txt');
  const preview = run();
  assert.equal(preview.status, 0, preview.stderr);
  assert.deepEqual(preview.result.counts, {eligible: 3});
  assert.equal(git('rev-parse', 'HEAD').trim(), revision);
  const applied = run('--apply');
  assert.equal(applied.status, 0, applied.stderr);
  assert.deepEqual(applied.result.counts, {removed: 3});
  assert.equal(applied.result.landing.state, 'committed');
  assert.equal(applied.result.landing.retiredFiles, 3);
  assert.deepEqual(rows(git('diff-tree', '--no-commit-id', '--name-only', '-r', '-z', 'HEAD')), [...paths].sort());
  assert.deepEqual(rows(git('diff', '--cached', '--name-only', '-z')), ['unrelated-new.txt', 'unrelated.txt']);
  assert.equal(git('show', 'HEAD:unrelated.txt'), 'original\n');
  assert(existsSync(join(root, 'lib/legacy/batch/a-match.mjs')));
  assert(existsSync(join(root, 'plan.json')));
  const landed = git('rev-parse', 'HEAD').trim();
  const repeated = run('--apply');
  assert.equal(repeated.status, 0, repeated.stderr);
  assert.deepEqual(repeated.result.counts, {absent: 3});
  assert.equal(repeated.result.landing.state, 'already-landed');
  assert.equal(git('rev-parse', 'HEAD').trim(), landed);
  assert.deepEqual(rows(git('diff', '--cached', '--name-only', '-z')), ['unrelated-new.txt', 'unrelated.txt']);
});

test('CLI surfaces commit failure and retries the staged deletion after the cause is repaired', t => {
  const {root, git, run, revision, paths} = fixture(t);
  const hook = join(root, 'hooks/pre-commit');
  writeFileSync(hook, '#!/bin/sh\nexit 7\n'); chmodSync(hook, 0o755);
  const failed = run('--apply');
  assert.equal(failed.status, 1);
  assert.equal(failed.result.landing.state, 'uncommitted');
  assert.match(failed.result.landing.error, /commit/);
  assert.equal(git('rev-parse', 'HEAD').trim(), revision);
  assert.deepEqual(rows(git('diff', '--cached', '--name-only', '-z')), [...paths].sort());
  rmSync(hook);
  const retry = run('--apply');
  assert.equal(retry.status, 0, retry.stderr);
  assert.deepEqual(retry.result.counts, {absent: 3});
  assert.equal(retry.result.landing.state, 'committed');
  assert.notEqual(git('rev-parse', 'HEAD').trim(), revision);
  assert.deepEqual(rows(git('diff-tree', '--no-commit-id', '--name-only', '-r', '-z', 'HEAD')), [...paths].sort());
});

test('CLI lands already-staged selected deletion without including unrelated staged work', t => {
  const {root, git, run, paths} = fixture(t);
  for (const path of paths) rmSync(join(root, path));
  git('add', '-u');
  writeFileSync(join(root, 'unrelated.txt'), 'independent staged change\n'); git('add', 'unrelated.txt');
  const applied = run('--apply');
  assert.equal(applied.status, 0, applied.stderr);
  assert.equal(applied.result.landing.state, 'committed');
  assert.deepEqual(rows(git('diff-tree', '--no-commit-id', '--name-only', '-r', '-z', 'HEAD')), [...paths].sort());
  assert.deepEqual(rows(git('diff', '--cached', '--name-only', '-z')), ['unrelated.txt']);
});

test('CLI detects a source recreated during commit and preserves the new worktree data', t => {
  const {root, git, run, revision} = fixture(t);
  const hook = join(root, 'hooks/pre-commit');
  writeFileSync(hook, "#!/bin/sh\nprintf 'new worktree source\\n' > lib/legacy/batch/ordinary.mjs\n");
  chmodSync(hook, 0o755);
  const applied = run('--apply');
  assert.equal(applied.status, 1);
  assert.equal(applied.result.landing.state, 'committed-with-recreated-files');
  assert.notEqual(applied.result.landing.commit, revision);
  assert.equal(applied.result.landing.commit, git('rev-parse', 'HEAD').trim());
  assert.equal(applied.result.landing.retiredFiles, 3);
  assert.deepEqual(applied.result.landing.recreatedFiles, ['lib/legacy/batch/ordinary.mjs']);
  assert.equal(git('ls-tree', '-r', 'HEAD', '--', 'lib/legacy/batch/ordinary.mjs'), '');
  assert.equal(readFileSync(join(root, 'lib/legacy/batch/ordinary.mjs'), 'utf8'), 'new worktree source\n');
});

for (const defect of ['missing-parent', 'directory-target', 'dangling-symlink']) {
  test(`CLI refuses ${defect} result destination before source or Git mutation`, t => {
    const {root, git, revision, paths} = fixture(t);
    writeFileSync(join(root, 'unrelated.txt'), 'keep staged work\n'); git('add', 'unrelated.txt');
    const output = defect === 'missing-parent' ? join(root, 'missing-records', 'result.json')
      : defect === 'directory-target' ? join(root, 'living') : join(root, 'linked-result.json');
    if (defect === 'dangling-symlink') symlinkSync('missing-records/result.json', output);
    const refused = spawnSync(process.execPath, [cli, join(root, 'plan.json'), '--apply', '--output=' + output], {encoding:'utf8'});
    assert.notEqual(refused.status, 0);
    assert.equal(git('rev-parse', 'HEAD').trim(), revision);
    assert.deepEqual(rows(git('diff', '--cached', '--name-only', '-z')), ['unrelated.txt']);
    assert.equal(git('diff', '--name-only'), '');
    for (const path of paths) assert(existsSync(join(root, path)));
    const resultPath = join(root, 'valid-result.json');
    const applied = spawnSync(process.execPath, [cli, join(root, 'plan.json'), '--apply', '--output=' + resultPath], {encoding:'utf8'});
    assert.equal(applied.status, 0, applied.stderr);
    assert.equal(JSON.parse(readFileSync(resultPath, 'utf8')).landing.state, 'committed');
  });
}
