import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, readFile, access, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { packRegistryCarrier, packSourceRegistryClosure, planSourceRegistryClosure, sourceRegistryManifestPath } from "../src/source-registry-closure.mjs";
import { verifyIsolatedCarrier } from "../src/isolated-carrier-verification.mjs";

test("isolated carrier verification uses the same receiving obligation before accepting an archive", async t => {
  const directory = await mkdtemp(join(tmpdir(), "npm-isolated-receiving-"));
  t.after(() => rm(directory, { recursive: true, force: true }));
  await mkdir(join(directory, "test"));
  await writeFile(join(directory, "index.mjs"), "export const value = true;\n");
  await writeFile(join(directory, "test", "receive.mjs"), "export const received = true;\n");
  const manifest = { name: "isolated-receiving-fixture", version: "1.0.0", type: "module", files: ["index.mjs"], exports: "./index.mjs", receivingTests: ["test/receive.mjs"] };
  await writeFile(join(directory, "package.json"), JSON.stringify(manifest) + "\n");
  const options = { sourceDir: directory, manifest, registry: "http://127.0.0.1:1", npmEnvironment: { npm_config_offline: "true" } };
  await assert.rejects(verifyIsolatedCarrier(options), error => {
    assert.deepEqual(error.evidence.violations, [{ kind: "missing-receiving-test", field: "receivingTests", target: "test/receive.mjs" }]);
    return true;
  });
  manifest.files.push("test");
  await writeFile(join(directory, "package.json"), JSON.stringify(manifest) + "\n");
  const received = await verifyIsolatedCarrier(options);
  await access(received.artifact);
  await received.cleanup();
});

test("native archive qualification refuses omitted or negated receiving files and admits intact files", async t => {
  const root = await mkdtemp(join(tmpdir(), "npm-receiving-carrier-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const directory = join(root, "source"), destination = join(root, "artifacts");
  await mkdir(join(directory, "test"), { recursive: true });
  await writeFile(join(directory, "index.mjs"), "export const ready = true;\n");
  await writeFile(join(directory, "test", "receive.mjs"), "throw Error('packing must not execute receiving tests');\n");
  const base = { name: "@fixture/receiving", version: "1.0.0", exports: "./index.mjs", receivingTests: ["test/receive.mjs"] };
  let rejected;
  for (const files of [["index.mjs"], ["index.mjs", "test", "!test/receive.mjs"]]) {
    const manifest = { ...base, files };
    await writeFile(join(directory, "package.json"), JSON.stringify(manifest) + "\n");
    rejected = await packRegistryCarrier({ directory, manifest, destination, npmEnvironment: { npm_config_offline: "true" } });
    assert.deepEqual(rejected.refusal.surface, [{ kind: "missing-receiving-test", field: "receivingTests", target: "test/receive.mjs" }]);
  }
  const rejectedBytes = await readFile(rejected.artifact);
  const manifest = { ...base, files: ["index.mjs", "test"] };
  await writeFile(join(directory, "package.json"), JSON.stringify(manifest) + "\n");
  const accepted = await packRegistryCarrier({ directory, manifest, destination, npmEnvironment: { npm_config_offline: "true" } });
  assert.equal(accepted.refusal, null);
  assert.ok(accepted.files.includes("test/receive.mjs"));
  assert.notEqual(accepted.artifact, rejected.artifact);
  assert.deepEqual(await readFile(rejected.artifact), rejectedBytes);
  assert.equal(await readFile(join(directory, "test", "receive.mjs"), "utf8"), "throw Error('packing must not execute receiving tests');\n");
  await mkdir(join(directory, "package"));
  await writeFile(join(directory, "package", "receive.mjs"), "export const nested = true;\n");
  const nested = { ...base, files: ["index.mjs", "package"], receivingTests: ["package/receive.mjs"] };
  await writeFile(join(directory, "package.json"), JSON.stringify(nested) + "\n");
  const nestedCarrier = await packRegistryCarrier({ directory, manifest: nested, destination, npmEnvironment: { npm_config_offline: "true" } });
  assert.equal(nestedCarrier.refusal, null);
  assert.ok(nestedCarrier.files.includes("package/receive.mjs"));
  const wrongLevel = { ...nested, receivingTests: ["receive.mjs"] };
  await writeFile(join(directory, "package.json"), JSON.stringify(wrongLevel) + "\n");
  const wrongCarrier = await packRegistryCarrier({ directory, manifest: wrongLevel, destination, npmEnvironment: { npm_config_offline: "true" } });
  assert.deepEqual(wrongCarrier.refusal.surface, [{ kind: "missing-receiving-test", field: "receivingTests", target: "receive.mjs" }]);
});

test("landed carriers and source closures share the real immutable archive maker", async t => {
  const root = await mkdtemp(join(tmpdir(), "npm-carrier-maker-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const directory = join(root, "source"), destination = join(root, "artifacts");
  await mkdir(join(directory, "lib", "semantic", "src"), { recursive: true });
  const manifest = { name: "@fixture/carrier", version: "0.1.0", type: "module",
    files: ["lib/semantic/src"], exports: { ".": "./lib/semantic/src/index.mjs" },
    scripts: { prepack: "node -e \"require('node:fs').writeFileSync('lifecycle-ran','unexpected')\"" } };
  const path = join(directory, "package.json");
  await writeFile(path, JSON.stringify(manifest, null, 2) + "\n");
  await writeFile(join(directory, "lib", "semantic", "src", "index.mjs"), "export const fromPinnedLibrary = true;\n");
  const direct = await packRegistryCarrier({ directory, manifest, destination });
  assert.equal(direct.refusal, null);
  assert.ok(direct.files.includes("lib/semantic/src/index.mjs"));
  await assert.rejects(access(join(directory, "lifecycle-ran")), { code: "ENOENT" });
  const closure = await packSourceRegistryClosure({ complete: true, registry: "https://example.invalid/",
    packages: [{ name: manifest.name, manifest, path, publish: true, missingTargets: [] }] }, { destination });
  assert.deepEqual(closure.refusals, []);
  assert.equal(closure.packages[0].artifact, direct.artifact);
  assert.equal(closure.packages[0].integrity, direct.integrity);
  assert.deepEqual(await readFile(closure.packages[0].artifact), await readFile(direct.artifact));
  await access(path);

  const missing = { ...manifest, exports: { ".": "./lib/semantic/src/absent.mjs" } };
  await writeFile(path, JSON.stringify(missing, null, 2) + "\n");
  const refused = await packRegistryCarrier({ directory, manifest: missing, destination });
  assert.equal(refused.refusal.surface[0].kind, "missing-carrier-target");
});

test("source registry closure receives directory and file selectors identically, preserving real published edges", async t => {
  const root=await mkdtemp(join(tmpdir(),"npm-native-consumer-"));
  t.after(()=>rm(root,{recursive:true,force:true}));
  const consumer=join(root,"consumer"),provider=join(root,"provider");
  await mkdir(consumer);await mkdir(provider);
  await writeFile(join(consumer,"package.json"),JSON.stringify({
    name:"@fixture/customer",version:"1.0.0",
    dependencies:{"@fixture/producer":"workspace:*"}}));
  await writeFile(join(provider,"package.json"),JSON.stringify({
    name:"@fixture/producer",version:"0.1.0",exports:{"." :"./index.mjs"}}));
  await writeFile(join(provider,"index.mjs"),"export const product=true;\n");
  const readRegistry=async(_registry,name)=>{
    assert.equal(name,"@fixture/producer");
    return {reachable:true,packument:{versions:{}}};
  };
  const options={providers:[{path:provider}],readRegistry};
  const byDir=await planSourceRegistryClosure({...options,consumerPaths:[consumer]});
  const byFile=await planSourceRegistryClosure({...options,consumerPaths:[join(consumer,"package.json")]});
  assert.equal(byDir.complete,true);
  assert.deepEqual(byDir.packages,byFile.packages);
  const customer=byDir.packages.find(p=>p.name==="@fixture/customer");
  assert.equal(customer.manifest.dependencies["@fixture/producer"],"0.1.0");
  assert.ok(byDir.packages.some(p=>p.name==="@fixture/producer"&&p.publish));
});

test("missing true supplier refuses without inventing an installed consumer or release",async t=>{
  const root=await mkdtemp(join(tmpdir(),"npm-missing-provider-"));
  t.after(()=>rm(root,{recursive:true,force:true}));
  await writeFile(join(root,"package.json"),JSON.stringify({
    name:"@fixture/customer",version:"1.0.0",
    dependencies:{"@fixture/missing":"workspace:*"}}));
  const result=await planSourceRegistryClosure({consumerPaths:[root],providers:[],
    readRegistry:()=>{throw Error("no registry read permitted");}});
  assert.equal(result.complete,false);
  assert.deepEqual(result.missingProviders,["@fixture/missing"]);
});

test("invalid source locators refuse before source or registry effects",async()=>{
  await assert.rejects(planSourceRegistryClosure({
    consumerPaths:[42],providers:[],readRegistry:()=>{throw Error("registry read");}
  }),/source locator/);
});

// The actual native package receiving operation shares this source-coordinate
// normalizer; a plan selected by directory must remain consumable by its
// installed release receiver without reverting to an unnormalized file read.
test("the one source coordinate normalizes received application directories and exact files",()=>{
  const directory="/opt/561/market";
  assert.equal(sourceRegistryManifestPath(directory),directory+"/package.json");
  assert.equal(sourceRegistryManifestPath(directory+"/package.json"),directory+"/package.json");
  assert.equal(sourceRegistryManifestPath("package.json"),join(process.cwd(),"package.json"));
  assert.throws(()=>sourceRegistryManifestPath(null),/source locator/);
});

test("native source-registry consumer refuses missing frozen lock without creating one",async t=>{
  const root=await mkdtemp(join(tmpdir(),"npm-frozen-closure-"));
  t.after(()=>rm(root,{recursive:true,force:true}));
  const consumer=join(root,"consumer"),logs=join(root,"logs");
  await mkdir(consumer);
  const manifest={name:"@fixture/customer",version:"1.0.0",
    dependencies:{"@fixture/existing":"1.0.0"}};
  await writeFile(join(consumer,"package.json"),JSON.stringify(manifest));
  const {receiveSourceRegistryConsumers}=await import("../src/source-registry-closure.mjs");
  const result=await receiveSourceRegistryConsumers({
    consumerPaths:[consumer],releases:[],logDirectory:logs
  });
  assert.equal(result.packages.length,0);
  assert.equal(result.refusals.length,1);
  assert.equal(result.refusals[0].reason,"native frozen consumer lock is absent");
  await assert.rejects(import("node:fs/promises").then(fs=>fs.readFile(join(consumer,"pnpm-lock.yaml"))),{code:"ENOENT"});
});

test("a later missing consumer lock refuses the whole selected estate before any native install", async t=>{
  const root=await mkdtemp(join(tmpdir(),"npm-estate-receiving-"));
  t.after(()=>rm(root,{recursive:true,force:true}));
  const first=join(root,"first"),second=join(root,"second"),logs=join(root,"logs");
  await mkdir(first);await mkdir(second);
  await writeFile(join(first,"package.json"),JSON.stringify({name:"@fixture/first",version:"1.0.0"}));
  await writeFile(join(first,"pnpm-lock.yaml"),"lockfileVersion: '9.0'\nimporters:\n  .: {}\n");
  await writeFile(join(second,"package.json"),JSON.stringify({name:"@fixture/second",version:"1.0.0"}));
  const {receiveSourceRegistryConsumers}=await import("../src/source-registry-closure.mjs");
  const observations=[];
  const result=await receiveSourceRegistryConsumers({
    consumerPaths:[first,second],releases:[],logDirectory:logs,
    onProgress:async(receipt,name)=>observations.push({name,received:receipt.packages.length})
  });
  assert.equal(result.packages.length,0);
  assert.equal(result.refusals.length,1);
  assert.equal(result.refusals[0].name,"@fixture/second");
  assert.deepEqual(observations,[{name:"@fixture/second",received:0}]);
  assert.equal(await (await import("node:fs/promises")).readFile(join(first,"pnpm-lock.yaml"),"utf8"),
    "lockfileVersion: '9.0'\nimporters:\n  .: {}\n");
});
