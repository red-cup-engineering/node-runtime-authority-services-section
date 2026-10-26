import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { nodeJobsAt, runNodeJob } from "../src/node-job.mjs";
import { availableMemoryBytes } from "../src/resources.mjs";

const limits = { memoryMaxBytes: 64 * 1024 * 1024, memoryHighBytes: 48 * 1024 * 1024,
  memorySwapMaxBytes: 0, tasksMax: 12, cpuQuotaPercent: 50, memoryReserveBytes: 32 * 1024 * 1024 };
function fixture(extra = {}) {
  const root = mkdtempSync(join(tmpdir(), "node-job-resources-"));
  for (const directory of ["jobs", "state/jobs", "bin"]) mkdirSync(join(root, directory), { recursive: true });
  const configuration = { runtimeRoot: root, jobsDirectory: "jobs", stateRoot: join(root, "state"), unitPrefix: "fixture", artifact: root };
  const job = { id: "inert", summary: "fixture inert job", directory: ".", node: ["inert.mjs"],
    demand: true, maxSeconds: 10, resources: limits, ...extra };
  writeFileSync(join(root, "jobs/inert.json"), JSON.stringify(job));
  const receipt = join(root, "state/jobs/inert.json"), demand = join(root, "state/jobs/inert.demand.json");
  const receiptBytes = '{"original":"authoritative","demand":{"pending":7}}\n', demandBytes = '{"pending":7}\n';
  writeFileSync(receipt, receiptBytes); writeFileSync(demand, demandBytes);
  const path = process.env.PATH, asked = join(root, "asked.json");
  writeFileSync(join(root, "bin/package.json"), JSON.stringify({ type: "commonjs" }));
  writeFileSync(join(root, "bin/systemctl"), `#!${process.execPath}\nprocess.stdout.write("inactive\\n");\n`, { mode: 0o700 });
  writeFileSync(join(root, "bin/systemd-run"), `#!${process.execPath}\nrequire("node:fs").writeFileSync(${JSON.stringify(asked)},JSON.stringify(process.argv.slice(2)));\n`, { mode: 0o700 });
  process.env.PATH = join(root, "bin") + ":" + path;
  return { root, configuration, asked, receipt, demand,
    unchanged() { assert.equal(readFileSync(receipt, "utf8"), receiptBytes); assert.equal(readFileSync(demand, "utf8"), demandBytes); },
    close() { process.env.PATH = path; rmSync(root, { recursive: true }); } };
}
const invoke = (f, options = {}) => runNodeJob({ configuration: f.configuration, job: "inert", fleet: null, ...options });

test("finite authored resources reach the original native runner with exact byte units", async () => {
  const f = fixture();
  try {
    const result = await invoke(f, { readAvailableMemory: () => limits.memoryMaxBytes + limits.memoryReserveBytes });
    assert.equal(result.state, "started");
    const argv = JSON.parse(readFileSync(f.asked, "utf8"));
    for (const expected of ["MemoryMax=67108864", "MemoryHigh=50331648", "MemorySwapMax=0", "TasksMax=12", "CPUQuota=50%", "RuntimeMaxSec=10"]) assert.ok(argv.includes("--property=" + expected), expected);
    assert.equal(readFileSync(f.receipt, "utf8"), '{"original":"authoritative","demand":{"pending":7}}\n');
  } finally { f.close(); }
});

for (const [name, change] of [
  ["infinite memory", { memoryMaxBytes: Infinity }],
  ["missing swap ceiling", { memorySwapMaxBytes: undefined }],
  ["negative reserve", { memoryReserveBytes: -1 }],
  ["zero task ceiling", { tasksMax: 0 }],
  ["zero CPU", { cpuQuotaPercent: 0 }],
  ["high above maximum", { memoryHighBytes: limits.memoryMaxBytes + 1 }],
  ["unknown field", { inventedReservation: true }],
]) test(name + " refuses at the original declaration entrance", async () => {
  const f = fixture({ resources: { ...limits, ...change } });
  try { assert.throws(() => nodeJobsAt(f.configuration), /invalid resources/); f.unchanged(); }
  finally { f.close(); }
});

test("a resource bounded job must also author its finite original runtime deadline", () => {
  const f = fixture({ maxSeconds: undefined });
  try { assert.throws(() => nodeJobsAt(f.configuration), /invalid resources/); f.unchanged(); }
  finally { f.close(); }
});

for (const available of [undefined, NaN, Infinity, -1, limits.memoryMaxBytes + limits.memoryReserveBytes - 1]) {
  test("unknown or insufficient current capacity refuses before a fleet bid and demand mutation: " + available, async () => {
    const f = fixture(); let bids = 0;
    try {
      await assert.rejects(() => invoke(f, { fleet: f.root, readAvailableMemory: () => available,
        claim: async () => { bids++; throw Error("must not bid"); } }), { code: "NODE_JOB_RESOURCE_ADMISSION" });
      assert.equal(bids, 0); f.unchanged();
    } finally { f.close(); }
  });
}

test("capacity is read again after fleet waiting, before demand mutation or native start", async () => {
  const f = fixture(); let reads = 0, bids = 0;
  try {
    await assert.rejects(() => invoke(f, { fleet: f.root, observe: () => ({ id: "fixture" }),
      readAvailableMemory: () => ++reads === 1 ? limits.memoryMaxBytes + limits.memoryReserveBytes : 0,
      claim: async () => { bids++; return { run: true, state: "won", window: "fixture" }; } }),
    { code: "NODE_JOB_RESOURCE_ADMISSION" });
    assert.equal(bids, 1); assert.equal(reads, 2); f.unchanged();
  } finally { f.close(); }
});

test("an unavailable native capacity reader refuses without exposing its diagnostic", async () => {
  const f = fixture(); let bids = 0;
  try {
    await assert.rejects(() => invoke(f, { fleet: f.root,
      readAvailableMemory: () => { throw Error("PRIVATE_NATIVE_DIAGNOSTIC"); },
      claim: async () => { bids++; throw Error("must not bid"); } }), error =>
      error.code === "NODE_JOB_RESOURCE_ADMISSION" && !error.message.includes("PRIVATE_NATIVE_DIAGNOSTIC"));
    assert.equal(bids, 0); f.unchanged();
  } finally { f.close(); }
});

test("an existing active cohort remains untouched without a new admission or bid", async () => {
  const f = fixture();
  writeFileSync(join(f.root, "bin/systemctl"), `#!${process.execPath}\nprocess.stdout.write("active\\n");\n`, { mode: 0o700 });
  try {
    const result = await invoke(f, { readAvailableMemory: () => { throw Error("must not read"); } });
    assert.equal(result.state, "running"); f.unchanged();
  } finally { f.close(); }
});

test("legacy declarations preserve their original behavior without fabricated resource budgets", async () => {
  const f = fixture({ resources: undefined });
  try {
    const result = await invoke(f, { readAvailableMemory: () => { throw Error("no authored budget"); } });
    assert.equal(result.state, "started");
    const argv = JSON.parse(readFileSync(f.asked, "utf8"));
    assert.ok(!argv.some(value => value.startsWith("--property=Memory")));
  } finally { f.close(); }
});

test("the original Linux physical observation returns finite byte units", () => {
  assert.ok(Number.isSafeInteger(availableMemoryBytes()));
  assert.ok(availableMemoryBytes() > 0);
});
