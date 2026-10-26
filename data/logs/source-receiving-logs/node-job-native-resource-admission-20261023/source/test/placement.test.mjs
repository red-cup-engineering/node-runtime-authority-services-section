import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, statSync, symlinkSync, utimesSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { backoffMs, costOf, fresh, roundedCostOf, refusals, servability, windowOf, windowReadingOf } from "../src/placement.mjs";
import { claimWindow, firstBidder, publish, recordRun } from "../src/fleet.mjs";
import { detectCapabilities, heldCredentials, maskedJobs, observeNode, observedResourceUnits } from "../src/observe.mjs";

const now = new Date("2026-10-22T18:00:00Z");
const node = (id, over = {}) => ({ id, observedAt: "2026-10-22T17:58:00Z", capabilities: ["systemd-user"], cores: 4, memoryGb: 16, memoryAvailableGb: 8, load1: 1, freeDiskGb: 50, credentials: ["koios-news"], jobs: ["editorial-drafting"], ...over });
const drafting = { id: "editorial-drafting", credentials: ["koios-news"], requires: { capabilities: ["systemd-user"], memoryGb: 1 } };

test("only static facts refuse; load and memory are prices, so a lone contended carrier still runs", () => {
  const crg = node("cold-red-gate", { cores: 1, load1: 20.68, memoryAvailableGb: 0.42 });
  assert.deepEqual(refusals(drafting, crg), []);
  assert.ok(costOf(drafting, crg) > 20 && backoffMs(costOf(drafting, crg)) === 60_000);
  assert.ok(costOf(drafting, node("bare-cedar-fog")) < 1);
  assert.deepEqual(refusals(drafting, node("x", { credentials: [], jobs: [], capabilities: [] })),
    ["lacks-capability:systemd-user", "lacks-credential:koios-news", "lacks-declaration"]);
  assert.deepEqual(refusals({ ...drafting, placement: { pinned: ["studio"], why: "session" } }, node("x")), ["not-pinned-here"]);
  assert.deepEqual(refusals(drafting, node("x", { masked: ["editorial-drafting"] })), ["masked-here"]);
});

test("a hand mask on a job unit is observed, so it surfaces as a refusal instead of a silent stall", () => {
  const runtime = mkdtempSync(join(tmpdir(), "runtime-")), home = mkdtempSync(join(tmpdir(), "home-"));
  mkdirSync(join(runtime, "systemd/user"), { recursive: true });
  mkdirSync(join(home, ".config/systemd/user"), { recursive: true });
  symlinkSync("/dev/null", join(runtime, "systemd/user/koios-news-561-group-job-editorial-drafting.service"));
  symlinkSync("/dev/null", join(home, ".config/systemd/user/a-job-b.service.wants"));
  writeFileSync(join(home, ".config/systemd/user/a-job-newsroom-cycle.service"), "[Service]\n");
  assert.deepEqual(maskedJobs({ env: { XDG_RUNTIME_DIR: runtime }, home }), ["editorial-drafting"]);
});

test("interval windows follow original firstDueAt and never invent a cron due", () => {
  // A 15-minute job starting at :02:30 is NOT an epoch-aligned :00/:15 job.
  const interval = { id: "j", trigger: { everySeconds: 900, firstDueAt: "2026-10-22T18:02:30Z" } };
  assert.equal(windowOf(interval, new Date("2026-10-22T18:17:29Z")), "20261022T180230Z");
  assert.equal(windowOf(interval, new Date("2026-10-22T18:17:30Z")), "20261022T181730Z");
  assert.equal(windowReadingOf(interval, new Date("2026-10-22T18:17:30Z")).lastDueAt, "2026-10-22T18:17:30.000Z");
  const fine = { id: "j", trigger: { everySeconds: 900, firstDueAt: "2026-10-22T18:02:30.125Z" } };
  const laterFine = { id: "j", trigger: { everySeconds: 900, firstDueAt: "2026-10-22T18:02:30.875Z" } };
  const sameInstantWithOffset = { id: "j",
    trigger: { everySeconds: 900, firstDueAt: "2026-10-22T13:02:30.125-05:00" } };
  assert.equal(windowOf(fine, new Date("2026-10-22T18:03:00Z")), "20261022T180230.125Z");
  assert.equal(windowOf(laterFine, new Date("2026-10-22T18:03:00Z")), "20261022T180230.875Z");
  assert.notEqual(windowOf(fine, new Date("2026-10-22T18:03:00Z")),
    windowOf(laterFine, new Date("2026-10-22T18:03:00Z")), "separate real instants need separate replay keys");
  assert.equal(windowOf(fine, new Date("2026-10-22T18:03:00Z")),
    windowOf(sameInstantWithOffset, new Date("2026-10-22T18:03:00Z")),
    "two authored UTC offset representations of one instant share one original replay key");
  assert.equal(windowReadingOf({ id: "cron", schedule: "0 9 * * *", timeZone: "America/Chicago" },
    new Date("2026-10-22T18:04:59Z")).basis, "coarse-correlation-bucket-not-cron-due");
  assert.equal(windowOf({ id: "legacy" }, new Date("2026-10-22T18:04:59Z")), "20261022T180000Z");
});

test("two different original UTC due instants survive the fall DST repeated hour", () => {
  const repeat = { id: "j", trigger: { everySeconds: 3600, firstDueAt: "2026-11-01T00:30:00-05:00" } };
  assert.equal(windowOf(repeat, new Date("2026-11-01T01:31:00-05:00")), "20261101T063000Z");
  assert.equal(windowOf(repeat, new Date("2026-11-01T01:31:00-06:00")), "20261101T073000Z");
  assert.notEqual(windowOf(repeat, new Date("2026-11-01T01:31:00-05:00")),
    windowOf(repeat, new Date("2026-11-01T01:31:00-06:00")));
  const spring = { id: "j", trigger: { everySeconds: 3600, firstDueAt: "2026-03-08T00:30:00-06:00" } };
  assert.equal(windowOf(spring, new Date("2026-03-08T01:31:00-06:00")), "20260308T073000Z");
  assert.equal(windowOf(spring, new Date("2026-03-08T03:31:00-05:00")), "20260308T083000Z");
});

test("unqualified, premature or missed interval start cannot bid or wait", async () => {
  const base = { ...drafting, trigger: { everySeconds: 900, firstDueAt: "2026-10-22T18:02:30Z" } };
  const cases = [
    ["not-yet-due", base, "2026-10-22T18:02:29Z"],
    ["invalid-interval-source", { ...base, trigger: { ...base.trigger, firstDueAt: "2026-10-22" } }, "2026-10-22T18:02:30Z"],
    ["invalid-interval-source", { ...base, trigger: { ...base.trigger, firstDueAt: "2026-10-22T18:02:30" } }, "2026-10-22T18:02:30Z"],
    ["invalid-interval-source", { ...base, trigger: { ...base.trigger, firstDueAt: "2026-02-30T18:02:30Z" } }, "2026-10-22T18:02:30Z"],
    ["invalid-interval-source", { ...base, trigger: { everySeconds: 900 } }, "2026-10-22T18:02:30Z"],
    ["starting-deadline-expired", { ...base, trigger: { ...base.trigger, startingDeadlineSeconds: 60 } }, "2026-10-22T18:03:31Z"],
    ["invalid-starting-deadline", { ...base, trigger: { ...base.trigger, startingDeadlineSeconds: 0 } }, "2026-10-22T18:02:30Z"],
  ];
  for (const [state, job, at] of cases) {
    const outcome = await claimWindow({ clone: "/no-fleet-I-O-on-invalid-due", job,
      observation: node("n"), now: new Date(at),
      wait: async () => { throw Error("premature or invalid due must never wait"); } });
    assert.deepEqual({ run: outcome.run, state: outcome.state }, { run: false, state });
    assert.equal(outcome.window, null);
  }
  assert.equal(windowOf({ ...base, trigger: { ...base.trigger, startingDeadlineSeconds: 60 } },
    new Date("2026-10-22T18:03:30Z")), "20261022T180230Z",
  "exact contractual starting-deadline edge is still admitted as a due candidate, not execution");
  assert.equal(windowReadingOf(base, new Date(NaN)).reason, "invalid-observed-clock");
});

test("actual backoff clock cannot carry an expired or newer due into a stale fleet bid", async () => {
  const input = { ...drafting, trigger: {
    everySeconds: 60, firstDueAt: "2026-10-22T18:02:30Z",
  } };
  let waits = 0;
  const laterWindow = await claimWindow({
    clone: "/nonexistent-no-substrate-due-test", job: input,
    observation: node("n"), now: new Date("2026-10-22T18:02:59Z"),
    wait: async (milliseconds) => { assert.ok(milliseconds > 0); waits++; },
    clock: () => new Date("2026-10-22T18:03:31Z"),
  });
  assert.deepEqual({ run: laterWindow.run, state: laterWindow.state, window: laterWindow.window },
    { run: false, state: "window-changed-before-bid", window: "20261022T180230Z" });
  const expiredDeadline = await claimWindow({
    clone: "/nonexistent-no-substrate-due-test",
    job: { ...drafting, trigger: { everySeconds: 900,
      firstDueAt: "2026-10-22T18:02:30Z", startingDeadlineSeconds: 60 } },
    observation: node("n"), now: new Date("2026-10-22T18:03:29Z"),
    wait: async () => { waits++; },
    clock: () => new Date("2026-10-22T18:03:31Z"),
  });
  assert.equal(expiredDeadline.run, false);
  assert.equal(expiredDeadline.state, "window-changed-before-bid");
  assert.equal(waits, 2, "each legitimate wait is observed once; no bid was consumed");
});

test("servability reads what nodes published about themselves", () => {
  const status = servability([drafting, { id: "orphan" }], [
    node("cold-red-gate", { costs: { "editorial-drafting": 22.1 } }),
    node("bare-cedar-fog", { refuses: { "editorial-drafting": ["lacks-credential:koios-news"] } }),
    node("gone", { observedAt: "2026-10-20T00:00:00Z" }),
  ], now);
  assert.deepEqual(status["editorial-drafting"].able, ["cold-red-gate"]);
  assert.equal(status["editorial-drafting"].cheapest, 22.1);
  assert.deepEqual(status["editorial-drafting"].refused, { "bare-cedar-fog": ["lacks-credential:koios-news"], gone: ["observation-stale"] });
  assert.deepEqual(status.orphan.able, []);
});

test("two able nodes bid for one window over a real git substrate; the first bid in history runs it", async () => {
  const root = mkdtempSync(join(tmpdir(), "fleet-"));
  const git = (cwd, ...args) => execFileSync("git", ["-C", cwd, ...args], { stdio: "pipe" });
  git(root, "init", "--quiet", "--bare", "-b", "fleet-facts", "origin.git");
  for (const name of ["a", "b"]) {
    git(root, "clone", "--quiet", join(root, "origin.git"), name);
    git(join(root, name), "config", "user.email", `${name}@fleet`); git(join(root, name), "config", "user.name", name);
  }
  writeFileSync(join(root, "a", "README"), "fleet\n"); git(join(root, "a"), "add", "README"); git(join(root, "a"), "commit", "--quiet", "-m", "seed"); git(join(root, "a"), "push", "--quiet", "-u", "origin", "fleet-facts");
  git(join(root, "b"), "pull", "--quiet", "origin", "fleet-facts"); git(join(root, "b"), "branch", "--quiet", "-u", "origin/fleet-facts");
  const wait = async () => {};
  const cheap = await claimWindow({ clone: join(root, "a"), job: drafting, observation: node("a", { jobs: ["editorial-drafting"] }), now, wait });
  const firstHead = git(join(root, "a"), "rev-parse", "HEAD").toString("utf8");
  const replay = await claimWindow({ clone: join(root, "a"), job: drafting, observation: node("a"), now, wait });
  const dear = await claimWindow({ clone: join(root, "b"), job: drafting, observation: node("b", { load1: 30, jobs: ["editorial-drafting"] }), now, wait });
  assert.equal(cheap.state, "won"); assert.equal(cheap.run, true);
  assert.deepEqual({ run: replay.run, state: replay.state }, { run: false, state: "already-bid-here" });
  assert.equal(git(join(root, "a"), "rev-parse", "HEAD").toString("utf8"), firstHead, "replay must not publish another bid or Git commit");
  assert.deepEqual({ run: dear.run, state: dear.state, by: dear.by }, { run: false, state: "claimed-elsewhere", by: "a" });
  assert.equal(firstBidder(join(root, "b"), drafting.id, cheap.window), "a");
  assert.equal(recordRun(join(root, "a"), { job: drafting.id, window: cheap.window, node: "a", unit: "u", release: "r" }), true);
  const runHead = git(join(root, "a"), "rev-parse", "HEAD").toString("utf8");
  const afterReceipt = await claimWindow({ clone: join(root, "a"), job: { ...drafting, exclusive: true }, observation: node("a"), now, wait });
  assert.deepEqual({ run: afterReceipt.run, state: afterReceipt.state }, { run: false, state: "already-run-here" });
  assert.equal(git(join(root, "a"), "rev-parse", "HEAD").toString("utf8"), runHead, "recorded exclusive work must not replay");
  // A disconnected or historical run may have a receipt but no bid. The receipt alone
  // still prevents an identical window from being launched a second time.
  const witnessOnlyJob = { ...drafting, id: "run-record-only" };
  const witnessOnlyWindow = windowOf(witnessOnlyJob, now);
  assert.equal(recordRun(join(root, "a"), { job: witnessOnlyJob.id, window: witnessOnlyWindow, node: "a", unit: "u2", release: "r2" }), true);
  const witnessed = await claimWindow({ clone: join(root, "a"), job: witnessOnlyJob, observation: node("a", { jobs: [witnessOnlyJob.id] }), now, wait });
  assert.deepEqual({ run: witnessed.run, state: witnessed.state }, { run: false, state: "already-run-here" });
});

test("an unreachable substrate runs a tolerant job uncoordinated and holds an exclusive one", async () => {
  const lonely = mkdtempSync(join(tmpdir(), "fleet-offline-"));
  execFileSync("git", ["-C", lonely, "init", "--quiet"]);
  const wait = async () => {};
  assert.equal((await claimWindow({ clone: lonely, job: drafting, observation: node("a"), now, wait })).state, "uncoordinated");
  assert.equal((await claimWindow({ clone: lonely, job: { ...drafting, exclusive: true }, observation: node("a"), now, wait })).state, "fleet-unreachable");
});

test("a node observes itself, including the credential services it holds", () => {
  const directory = mkdtempSync(join(tmpdir(), "credentials-"));
  for (const name of ["youtube.env", "koios-news.env", "key.pem"]) writeFileSync(join(directory, name), "");
  assert.deepEqual(heldCredentials(directory), ["koios-news", "youtube"]);
  const observation = observeNode({ id: "n", capabilities: ["guix", "guix"], credentialsDirectory: directory, diskPath: directory, jobs: ["b", "a"], now });
  assert.equal(observation.id, "n");
  assert.equal(observation.capabilities.filter((name) => name === "guix").length, 1);
  assert.deepEqual(observation.jobs, ["a", "b"]);
  assert.ok(observation.cores >= 1 && observation.memoryAvailableGb > 0 && observation.freeDiskGb > 0);
});

test("credential observations exclude unrendered, directory, and broken-link pseudo-files", () => {
  const root = mkdtempSync(join(tmpdir(), "credential-observer-"));
  try {
    writeFileSync(join(root, "seller.env"), "");
    mkdirSync(join(root, "phantom.env"));
    symlinkSync(join(root, "missing-file"), join(root, "dangling.env"));
    writeFileSync(join(root, "not-credential.txt"), "");
    assert.deepEqual(heldCredentials(root), ["seller"], "only a readable regular host file is advertised");
    const observation = observeNode({ id: "host", jobs: ["seller-job"], credentialsDirectory: root, diskPath: root, now });
    assert.deepEqual(observation.credentials, ["seller"]);
    assert.deepEqual(refusals({ id: "seller-job", credentials: ["seller"] }, observation), []);
    assert.deepEqual(refusals({ id: "seller-job", credentials: ["phantom"] }, observation), ["lacks-credential:phantom"]);
    assert.deepEqual(refusals({ id: "seller-job", credentials: ["dangling"] }, observation), ["lacks-credential:dangling"]);
    writeFileSync(join(root, "target"), "");
    symlinkSync(join(root, "target"), join(root, "linked.env"));
    assert.deepEqual(heldCredentials(root), ["linked", "seller"], "a resolved regular-file link remains compatible with host access");
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test("capabilities come from the OS, not from flags", () => {
  assert.deepEqual(detectCapabilities({ exists: (path) => path === "/gnu/store" || path === "/run/user/7/systemd", env: { XDG_RUNTIME_DIR: "/run/user/7" } }), ["systemd-user", "guix"]);
  assert.deepEqual(detectCapabilities({ exists: () => false, env: {} }), []);
});

test("source resource measurements preserve tiny positive use, scarce bytes and unknown values", () => {
  const GB = 1024 ** 3;
  for (const [load1, memBytes, diskBytes, expected] of [
    [0.004, 0.005 * GB, 0.004 * GB, { load1: 0.004, memoryAvailableGb: 0.005, freeDiskGb: 0.004 }],
    [0, 0, 0, { load1: 0, memoryAvailableGb: 0, freeDiskGb: 0 }],
    [NaN, NaN, Infinity, { load1: null, memoryAvailableGb: null, freeDiskGb: null }],
    [-1, -1, -1, { load1: null, memoryAvailableGb: null, freeDiskGb: null }],
  ]) {
    const measured = observedResourceUnits({ load1, memoryAvailableBytes: memBytes, diskAvailableBytes: diskBytes });
    assert.deepEqual(JSON.parse(JSON.stringify(measured)), expected);
  }
  const tiny = observedResourceUnits({ load1: 0.004, memoryAvailableBytes: 0.005 * GB, diskAvailableBytes: 0.004 * GB });
  const observed = node("n", { ...tiny, cores: 1 });
  assert.equal(roundedCostOf({ id: "zero", requires: { memoryGb: 0, freeDiskGb: 0 } }, observed), 0.01,
    "tiny positive observed CPU load may not appear as zero cost");
  assert.equal(costOf({ id: "mem", requires: { memoryGb: 0.005, freeDiskGb: 0 } }, observed), 1.004,
    "scarce free memory cannot be inflated by display rounding");
  assert.equal(costOf({ id: "disk", requires: { memoryGb: 0, freeDiskGb: 0.004 } }, observed), 1.004,
    "scarce disk may not be inflated by display rounding");
  assert.equal(costOf(drafting, node("n", { ...observedResourceUnits({ load1: NaN, memoryAvailableBytes: 1e9, diskAvailableBytes: 1e9 }) })), null);
});

test("unknown resource readings are not free capacity and cannot bid", async () => {
  const invalid = [
    { load1: undefined }, { load1: NaN }, { load1: -1 }, { cores: 0 },
    { cores: undefined }, { memoryAvailableGb: 0 }, { memoryAvailableGb: undefined },
    { memoryAvailableGb: Infinity }, { load1: Infinity },
  ];
  for (const bad of invalid) assert.equal(costOf(drafting, node("n", bad)), null);
  assert.equal(costOf({ ...drafting, requires: { memoryGb: -1 } }, node("n")), null);
  assert.equal(costOf({ ...drafting, requires: { memoryGb: 0.5, freeDiskGb: 2 } }, node("n", { freeDiskGb: 0 })), null);
  assert.equal(costOf({ ...drafting, requires: { memoryGb: 0, freeDiskGb: 0 } }, node("n", { memoryAvailableGb: 0, freeDiskGb: 0 })), 0.25);
  for (const bad of [null, undefined, NaN, Infinity, -1, "0"]) assert.throws(() => backoffMs(bad), RangeError);
  const absentClone = join(tmpdir(), "no-fleet-may-be-created-here");
  const outcome = await claimWindow({ clone: absentClone, job: drafting, observation: node("n", { load1: NaN }), now,
    wait: async () => { throw Error("invalid bid must never wait"); } });
  assert.deepEqual({ run: outcome.run, state: outcome.state }, { run: false, state: "unpriced-here" });
});

test("future timestamps do not keep a stale or fabricated node alive", async () => {
  assert.equal(fresh(node("past"), now), true);
  assert.equal(fresh(node("slightly-ahead", { observedAt: "2026-10-22T18:00:30Z" }), now), true);
  assert.equal(fresh(node("future", { observedAt: "2026-10-22T18:01:01Z" }), now), false);
  assert.equal(fresh(node("invalid", { observedAt: "invalid" }), now), false);
  const outcome = await claimWindow({ clone: "not-accessed", job: drafting,
    observation: node("future", { observedAt: "2026-10-22T18:01:01Z" }), now,
    wait: async () => { throw Error("untrusted timestamp must not wait"); } });
  assert.deepEqual({ run: outcome.run, state: outcome.state }, { run: false, state: "untrusted-observation" });
});

test("published prices must be measured, finite and nonnegative", () => {
  const invalidNodes = [
    node("negative", { costs: { "editorial-drafting": -2 } }),
    node("missing", { costs: {} }),
    node("null", { costs: { "editorial-drafting": null } }),
    node("nonfinite", { costs: { "editorial-drafting": Infinity } }),
  ];
  const status = servability([drafting], invalidNodes, now)["editorial-drafting"];
  assert.equal(status.cheapest, null);
  assert.deepEqual(status.costs, { negative: null, missing: null, null: null, nonfinite: null });
  assert.equal(status.able.length, 4); // Static carriage != known numeric cost.
});

test("dated Cold Red Gate and Bare Cedar Fog facts preserve installation and cost distinctions", () => {
  // Source observations 2026-10-23T08:48:13Z and 08:51:27Z; not a host or cash assay.
  const check = new Date("2026-10-23T08:52:00Z");
  const crg = node("cold-red-gate", { observedAt: "2026-10-23T08:48:13.313Z",
    cores: 1, load1: 1.59, memoryAvailableGb: 0.6, jobs: ["editorial-drafting"] });
  const bcf = node("bare-cedar-fog", { observedAt: "2026-10-23T08:51:27.247Z",
    cores: 16, load1: 2.76, memoryAvailableGb: 7.05, jobs: [] });
  assert.ok(costOf(drafting, crg) > 2);
  assert.equal(costOf(drafting, bcf), 2.76 / 16 + 1 / 7.05);
  assert.ok(refusals(drafting, bcf).includes("lacks-declaration"));
  const status = servability([drafting], [crg, bcf], check)["editorial-drafting"];
  assert.deepEqual(status.able, ["cold-red-gate"]);
  assert.equal(status.cheapest, null); // No published cost has been fabricated.
});

test("node-owned fleet publication preserves null when observed capacity cannot be priced", () => {
  const healthy = node("n");
  assert.equal(roundedCostOf(drafting, healthy), 0.38);
  assert.equal(roundedCostOf(drafting, { ...healthy, load1: 0 }), 0.13);
  assert.equal(roundedCostOf(drafting, { ...healthy, load1: undefined }), null);
  assert.equal(roundedCostOf(drafting, { ...healthy, memoryAvailableGb: 0 }), null);
  // A null from source and a real zero must not collapse in JSON or through the reader.
  const zeroFootprint = { id: "zero-footprint", requires: { memoryGb: 0, freeDiskGb: 0 } };
  const zero = roundedCostOf(zeroFootprint, { ...healthy, load1: 0 });
  assert.equal(zero, 0);
  const transmitted = JSON.parse(JSON.stringify({ missing: roundedCostOf(drafting, { ...healthy, load1: NaN }), measuredIdle: zero }));
  assert.deepEqual(transmitted, { missing: null, measuredIdle: 0 });
  const status = servability([{ id: drafting.id }], [
    { ...healthy, id: "unknown", costs: { [drafting.id]: transmitted.missing } },
    { ...healthy, id: "idle", costs: { [drafting.id]: transmitted.measuredIdle } },
  ], now)[drafting.id];
  assert.deepEqual(status.costs, { unknown: null, idle: 0 });
  assert.equal(status.cheapest, 0);
});

test("centi-unit fleet publication never presents a positive price as measured zero", () => {
  const zeroFootprint = { id: "zero-footprint", requires: { memoryGb: 0, freeDiskGb: 0 } };
  const observed = node("n", { cores: 1, memoryAvailableGb: 0, freeDiskGb: 0 });
  for (const [load1, wanted] of [
    [0, 0], [0.00001, 0.01], [0.0049, 0.01], [0.0051, 0.01],
    [0.01, 0.01], [0.011, 0.02], [0.125, 0.13], [0.375, 0.38], [1.0001, 1.01],
  ]) {
    const cost = roundedCostOf(zeroFootprint, { ...observed, load1 });
    assert.equal(cost, wanted, `load ${load1}`);
    assert.ok(cost >= costOf(zeroFootprint, { ...observed, load1 }), `load ${load1}`);
  }
  assert.equal(roundedCostOf(zeroFootprint, { ...observed, load1: undefined }), null);
  const prices = { zero: roundedCostOf(zeroFootprint, { ...observed, load1: 0 }),
    tiny: roundedCostOf(zeroFootprint, { ...observed, load1: 0.00001 }),
    absent: roundedCostOf(zeroFootprint, { ...observed, load1: undefined }) };
  assert.deepEqual(JSON.parse(JSON.stringify(prices)), { zero: 0, tiny: 0.01, absent: null });
});

test("publishing a fleet heartbeat reuses twenty unchanged declarations, while changed facts still replicate", () => {
  const root = mkdtempSync(join(tmpdir(), "fleet-cache-"));
  const git = (cwd, ...args) => execFileSync("git", ["-C", cwd, ...args], { stdio: "pipe" });
  const clone = join(root, "writer"), remote = join(root, "origin.git");
  try {
    git(root, "init", "--quiet", "--bare", "-b", "fleet-facts", "origin.git");
    git(root, "clone", "--quiet", remote, "writer");
    git(clone, "config", "user.email", "writer@fleet");
    git(clone, "config", "user.name", "writer");
    writeFileSync(join(clone, "README"), "facts\\n");
    git(clone, "add", "README");
    git(clone, "commit", "--quiet", "-m", "seed");
    git(clone, "push", "--quiet", "-u", "origin", "fleet-facts");

    const jobs = Array.from({ length: 20 }, (_, n) => ({ path: `jobs/job-${n}.json`,
      value: { id: `job-${n}`, summary: `carried ${n}` } }));
    const observation = (at) => ({ path: "nodes/writer.json",
      value: { id: "writer", observedAt: at, jobs: jobs.map(({ value }) => value.id) } });
    const firstMetrics = {};
    assert.equal(publish(clone, [observation("2026-10-23T10:00:00Z"), ...jobs], "First measured heartbeat", firstMetrics), true);
    assert.deepEqual([firstMetrics.attempts, firstMetrics.writes, firstMetrics.addCalls, firstMetrics.commits, firstMetrics.pushAttempts],
      [1, 21, 1, 1, 1]);
    assert.ok(firstMetrics.writtenBytes > 0);
    // A replay of the exact same heartbeat is already on the remote. No second
    // empty Git commit or push is an independently useful event.
    const publishedHead = git(clone, "rev-parse", "HEAD").toString("utf8");
    const repeatedMetrics = {};
    assert.equal(publish(clone, [observation("2026-10-23T10:00:00Z"), ...jobs], "Exact duplicate heartbeat", repeatedMetrics), true);
    assert.deepEqual([repeatedMetrics.attempts, repeatedMetrics.pullSuccesses, repeatedMetrics.writes,
      repeatedMetrics.stagedDiffChecks, repeatedMetrics.unchangedPublishes, repeatedMetrics.commits, repeatedMetrics.pushAttempts],
      [1, 1, 0, 1, 1, 0, 0], "an acknowledged no-op must not invent a remote write");
    assert.equal(git(clone, "rev-parse", "HEAD").toString("utf8"), publishedHead);
    const unchanged = join(clone, jobs[10].path);
    const frozenTime = new Date("2020-01-01T00:00:00Z");
    utimesSync(unchanged, frozenTime, frozenTime);

    const secondMetrics = {};
    assert.equal(publish(clone, [observation("2026-10-23T10:05:00Z"), ...jobs], "Fresh heartbeat", secondMetrics), true);
    assert.deepEqual([secondMetrics.attempts, secondMetrics.writes, secondMetrics.addCalls, secondMetrics.commits, secondMetrics.pushAttempts],
      [1, 1, 1, 1, 1], "fresh observation, unchanged declarations; no invented saved Git push");
    assert.equal(statSync(unchanged).mtimeMs, frozenTime.getTime(),
      "unchanged declaration must not be rewritten on the next heartbeat");
    assert.equal(JSON.parse(readFileSync(join(clone, "nodes/writer.json"), "utf8")).observedAt,
      "2026-10-23T10:05:00Z", "changed observation must still be published");

    const revisedJobs = jobs.map((fact, n) => n === 7 ? { ...fact,
      value: { ...fact.value, summary: "revised" } } : fact);
    const thirdMetrics = {};
    assert.equal(publish(clone, [observation("2026-10-23T10:10:00Z"), ...revisedJobs], "Updated one declaration", thirdMetrics), true);
    assert.deepEqual([thirdMetrics.attempts, thirdMetrics.writes, thirdMetrics.addCalls, thirdMetrics.commits, thirdMetrics.pushAttempts],
      [1, 2, 1, 1, 1]);
    assert.equal(statSync(unchanged).mtimeMs, frozenTime.getTime(),
      "a third round does not rewrite unrelated declarations");
    git(root, "clone", "--quiet", remote, "reader");
    const reader = join(root, "reader");
    for (const fact of revisedJobs) {
      assert.deepEqual(JSON.parse(readFileSync(join(reader, fact.path), "utf8")), fact.value);
    }
    assert.equal(JSON.parse(readFileSync(join(reader, "nodes/writer.json"), "utf8")).observedAt,
      "2026-10-23T10:10:00Z", "reader receives the newest node observation");
    // An already staged declaration must not be mistaken for a clean no-op,
    // even if the publisher would not rewrite a byte this time.
    const staged = { path: "jobs/job-3.json", value: { id: "job-3", summary: "pre-staged revision" } };
    writeFileSync(join(clone, staged.path), `${JSON.stringify(staged.value, null, 2)}\n`);
    git(clone, "add", "--", staged.path);
    const stagedMetrics = {};
    assert.equal(publish(clone, [staged], "Publish pending staged revision", stagedMetrics), true);
    assert.deepEqual([stagedMetrics.writes, stagedMetrics.stagedDiffChecks, stagedMetrics.unchangedPublishes,
      stagedMetrics.commits, stagedMetrics.pushAttempts], [0, 1, 0, 1, 1]);
    git(reader, "pull", "--quiet", "--ff-only");
    assert.deepEqual(JSON.parse(readFileSync(join(reader, staged.path), "utf8")), staged.value);

    // An inaccessible remote cannot become an acknowledged no-op merely
    // because an identical local file is present.
    renameSync(remote, `${remote}.offline`);
    const offlineMetrics = {};
    assert.equal(publish(clone, [staged], "Disconnected identical snapshot", offlineMetrics), false);
    assert.equal(offlineMetrics.pullSuccesses, 0);
    assert.equal(offlineMetrics.unchangedPublishes, 0);
    assert.equal(offlineMetrics.pulls, 4, "bounded read retries remain available");
    assert.equal(offlineMetrics.addCalls, 0, "unreachable unchanged facts do not need repeated Git staging");
    assert.equal(offlineMetrics.pushAttempts, 0, "never push a speculative empty commit");
    assert.equal(offlineMetrics.commits, 0, "remote outage creates no empty local Git history");
  } finally { rmSync(root, { recursive: true, force: true }); }
});
