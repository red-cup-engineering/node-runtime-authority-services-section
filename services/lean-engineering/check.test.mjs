import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, symlinkSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { checkLean } from './check.mjs';

const root = mkdtempSync(join(tmpdir(), 'lean-adapter-'));
writeFileSync(join(root, 'Good.lean'), 'example : 2 + 2 = 4 := by decide');
writeFileSync(join(root, 'Bad.lean'), 'example : False := by trivial');
const fake = join(root, 'fake-lake');
writeFileSync(fake, '#!/bin/sh\ncase "$3" in Good.lean) exit 0;; Bad.lean) echo "unsolved goals" >&2; exit 1;; esac\n', {mode: 0o755});

test('compiler wrapper distinguishes positive and negative results (mock, not kernel)', () => {
  const good = checkLean({workspace: root, file: 'Good.lean', lake: fake});
  const bad = checkLean({workspace: root, file: 'Bad.lean', lake: fake});
  assert.equal(good.exitCode, 0);
  assert.equal(bad.exitCode, 1);
  assert.equal(good.kernelVerified, false);
  assert.match(good.sourceSha256, /^[a-f0-9]{64}$/);
});
test('workspace escape via symlink is rejected', () => {
  const outside = mkdtempSync(join(tmpdir(), 'lean-outside-'));
  writeFileSync(join(outside, 'Other.lean'), '');
  symlinkSync(join(outside, 'Other.lean'), join(root, 'Link.lean'));
  assert.throws(() => checkLean({workspace: root, file: 'Link.lean', lake: fake}), /outside workspace/);
});
test('timeout has a strict upper bound', () => {
  assert.throws(() => checkLean({workspace: root, file: 'Good.lean', timeoutMs: 90000}), /timeout/);
});
