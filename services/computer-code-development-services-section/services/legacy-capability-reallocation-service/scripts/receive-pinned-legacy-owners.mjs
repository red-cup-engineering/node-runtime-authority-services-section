#!/usr/bin/env node
import { accessSync, closeSync, constants, fstatSync, lstatSync, openSync, readSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { receivePinnedLegacyOwnerEvidence } from '../src/pinned-legacy-owner-evidence.mjs';

const [request, output, ...extra] = process.argv.slice(2);
if (!request || !output || extra.length) throw new TypeError('usage: receive-pinned-legacy-owners REQUEST.json NEW-OUTPUT.json');
accessSync(dirname(resolve(output)), constants.W_OK);
try {
  lstatSync(output);
  throw new TypeError('owner evidence output already exists');
} catch (error) { if (error.code !== 'ENOENT') throw error; }
const fd = openSync(request, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
let bytes;
try {
  const before = fstatSync(fd);
  if (!before.isFile() || before.size > 262144) throw new TypeError('request must be a regular file bounded by 256 KiB');
  const buffer = Buffer.alloc(262145);
  let length = 0;
  while (length < buffer.length) {
    const read = readSync(fd, buffer, length, buffer.length - length, null);
    if (!read) break;
    length += read;
  }
  bytes = buffer.subarray(0, length);
  const after = fstatSync(fd);
  if (bytes.length > 262144 || before.size !== after.size || before.mtimeMs !== after.mtimeMs || before.ctimeMs !== after.ctimeMs)
    throw new TypeError('owner request changed while being read');
} finally { closeSync(fd); }
const result = await receivePinnedLegacyOwnerEvidence(JSON.parse(bytes.toString('utf8')));
writeFileSync(output, JSON.stringify(result, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
process.stdout.write(JSON.stringify({ kind: result.kind, owners: result.owners.length, files: result.owners.reduce((n, owner) => n + owner.files.length, 0), totalBytes: result.totalBytes, retirementAuthorized: false, output }) + '\n');
