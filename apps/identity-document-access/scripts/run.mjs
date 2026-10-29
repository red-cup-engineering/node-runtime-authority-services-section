#!/usr/bin/env node
// Local source operation through the existing publication service's binding owner.
// Registry-installed consumers can invoke bin/identity-access.mjs directly.
import { readFile, readdir, realpath } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { resolve, dirname } from 'node:path';
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';

const app = await realpath(fileURLToPath(new URL('..', import.meta.url)));
const appManifest = JSON.parse(await readFile(resolve(app, 'package.json'), 'utf8'));
const [command, ...args] = process.argv.slice(2);
const target = command === 'test' ? ['--test', ...(await readdir(resolve(app, 'test'))).filter(name => name.endsWith('.test.mjs')).sort().map(name => resolve(app, 'test', name))] : [resolve(app, 'bin/identity-access.mjs'), command, ...args];
const run = () => new Promise((done, reject) => {
  const child = spawn(process.execPath, target, { stdio: 'inherit', cwd: app });
  child.once('error', reject); child.once('exit', (code, signal) => signal ? reject(new Error('Child terminated by ' + signal)) : done(code));
});
// Installed consumers already have the declared providers. Prefer that real
// composition to reconstructing an older source-tree relationship.
const installed = await Promise.all(Object.entries(appManifest.dependencies).map(async ([name, version]) => {
  try { return JSON.parse(await readFile(resolve(app, 'node_modules', name, 'package.json'), 'utf8')).version === version; }
  catch (error) { if (error.code === 'ENOENT') return false; throw error; }
}));
if (installed.every(Boolean)) {
  process.exitCode = await run();
} else {
const codeOwner = resolve(app, '../..');
const dataOwner = resolve(codeOwner, '../computer-data-engineering-services-section');
const { withSourceBindings } = await import(pathToFileURL(resolve(codeOwner, '../../../npm-workspace-publication-service/src/source-bindings.mjs')));
const signcell = await realpath(resolve(dataOwner, 'node_modules/@red-cup-engineering/signcell'));
const requireFromSigncell = createRequire(resolve(signcell, 'package.json'));
const providers = [
  signcell,
  await realpath(resolve(dataOwner, 'node_modules/@red-cup-engineering/json-schema-services-section')),
  await realpath(dirname(dirname(requireFromSigncell.resolve('@red-cup-engineering/computer-data-engineering-services-section/four'))))
];
const packages = await Promise.all([app, ...providers].map(async dir => {
  const manifest = JSON.parse(await readFile(resolve(dir, 'package.json'), 'utf8'));
  return { dir, name: manifest.name, version: manifest.version, lifecycle: [] };
}));
for (const provider of packages.slice(1)) if (appManifest.dependencies[provider.name] !== provider.version) throw new TypeError('Source dependency version mismatch: ' + provider.name);
process.exitCode = await withSourceBindings({ packages, dependencies: { [packages[0].name]: packages.slice(1).map(p => p.name) } }, run);
}
