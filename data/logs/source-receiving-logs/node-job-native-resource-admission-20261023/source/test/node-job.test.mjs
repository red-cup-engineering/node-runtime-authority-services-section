import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { nodeJobsOf, readNodeJobDeclarations, runNodeJob } from "../src/node-job.mjs";

const job = (id, extra = {}) => ({ id, summary: `the ${id} job`, directory: "lib", node: ["run.mjs"], maxSeconds: 60, ...extra });

async function deployment(files) {
  const root = await mkdtemp(join(tmpdir(), "node-job-"));
  await mkdir(join(root, "deploy/jobs"), { recursive: true });
  await writeFile(join(root, "deploy/release.json"), JSON.stringify({ host: "local", releaseRoot: ".local/state/x", unit: { name: "x.service" } }));
  for (const [name, value] of Object.entries(files)) await writeFile(join(root, "deploy/jobs", name), JSON.stringify(value));
  return root;
}

const localConfiguration = (root) => ({
  runtimeRoot: root, jobsDirectory: "deploy/jobs", stateRoot: join(root, "state"),
  unitPrefix: "x", artifact: root,
});

async function fakeSystemctl(root, status = "inactive") {
  const bin = join(root, "fake-bin"), before = process.env.PATH;
  await mkdir(bin, { recursive: true });
  const statement = status === "error"
    ? 'process.stderr.write("unavailable\\n"); process.exit(5);'
    : `process.stdout.write(${JSON.stringify(status + "\n")});`;
  await writeFile(join(bin, "systemctl"), `#!${process.execPath}\n${statement}\n`, { mode: 0o700 });
  process.env.PATH = `${bin}:${before}`;
  return () => { process.env.PATH = before; };
}

test("a directory of well-named files reads as one array sorted by id", async () => {
  const root = await deployment({ "b-job.json": job("b-job"), "a-job.json": job("a-job", { everySeconds: 3600, firstDueAt: "2026-10-03T00:00:00Z" }) });
  try {
    assert.deepEqual(readNodeJobDeclarations(join(root, "deploy/jobs")).map(({ id }) => id), ["a-job", "b-job"]);
    const declared = nodeJobsOf(root);
    assert.deepEqual([...declared.jobs.keys()], ["a-job", "b-job"]);
    assert.equal(declared.jobs.get("a-job").trigger.everySeconds, 3600);
  } finally { await rm(root, { recursive: true }); }
});

test("original interval and cron declarations refuse timezone-naive or nonexistent due instants", async () => {
  const valid = await deployment({ "interval.json": job("interval", {
    everySeconds: 3600, firstDueAt: "2026-10-23T09:48:00-05:00",
  }) });
  try {
    assert.equal(nodeJobsOf(valid).jobs.get("interval").trigger.firstDueAt,
      "2026-10-23T09:48:00-05:00", "absolute offset source bytes survive unchanged");
  } finally { await rm(valid, { recursive: true }); }
  for (const firstDueAt of [
    "2026-10-23", "2026-10-23T09:48:00",
    "2026-02-30T09:48:00-05:00", "not-a-date",
  ]) {
    const root = await deployment({ "interval.json": job("interval", {
      everySeconds: 3600, firstDueAt,
    }) });
    try {
      assert.throws(() => nodeJobsOf(root),
        /absolute firstDueAt instant/u, "interval admission must refuse " + firstDueAt);
    } finally { await rm(root, { recursive: true }); }
  }
  const cron = await deployment({ "calendar.json": job("calendar", {
    schedule: "0 9 * * *", timeZone: "America/Chicago", firstDueAt: "2026-10-23T09:00:00",
  }) });
  try {
    assert.throws(() => nodeJobsOf(cron),
      /non-absolute or invalid firstDueAt/u,
      "the original cron scheduler must not inherit a machine-local naive boundary");
  } finally { await rm(cron, { recursive: true }); }
});

test("a file whose name and id differ is refused", async () => {
  const root = await deployment({ "a-job.json": job("other") });
  try { assert.throws(() => readNodeJobDeclarations(join(root, "deploy/jobs")), /differs from its file name/); } finally { await rm(root, { recursive: true }); }
});

test("a second file declaring an id already declared is refused", async () => {
  const root = await deployment({ "a-job.json": job("a-job"), "b-job.json": job("a-job") });
  try { assert.throws(() => readNodeJobDeclarations(join(root, "deploy/jobs")), /duplicate job "a-job"/); } finally { await rm(root, { recursive: true }); }
});

test("a deployment with no jobs directory declares none", async () => {
  const root = await mkdtemp(join(tmpdir(), "node-job-"));
  try { assert.equal(nodeJobsOf(root), undefined); } finally { await rm(root, { recursive: true }); }
});

test("a job whose window another fleet node won does not start here", async () => {
  const root = await deployment({ "drafting.json": job("drafting") });
  const restore = await fakeSystemctl(root);
  try {
    let claims = 0;
    const claim = async ({ job: claimed, observation }) => {
      claims++;
      return { run: false, state: "claimed-elsewhere", window: "20261022T180000Z", by: `not-${observation.id}-for-${claimed.id}` };
    };
    const result = await runNodeJob({ configuration: localConfiguration(root), job: "drafting",
      fleet: root, nodeId: "cold-red-gate", observe: ({ id }) => ({ id }), claim });
    assert.deepEqual({ ...result }, { kind: "node-job-run.v1", job: "drafting", run: false, state: "claimed-elsewhere",
      window: "20261022T180000Z", by: "not-cold-red-gate-for-drafting" });
    assert.equal(claims, 1, "a qualified idle host reaches one fleet bid");
  } finally { restore(); await rm(root, { recursive: true }); }
});

test("an already-running service consumes no fleet bid or duplicate start", async () => {
  const root = await deployment({ "running.json": job("running") });
  const restore = await fakeSystemctl(root, "active");
  let claims = 0;
  try {
    const result = await runNodeJob({ configuration: localConfiguration(root), job: "running",
      fleet: root, nodeId: "cold-red-gate", claim: async () => { claims++; throw Error("should not claim"); } });
    assert.equal(result.state, "running");
    assert.equal(claims, 0, "an active unit is already serving its turn");
  } finally { restore(); await rm(root, { recursive: true }); }
});

test("missing credential custody never consumes a fleet scheduling window", async () => {
  const root = await deployment({ "credential-job.json": job("credential-job", { credentials: ["seller-api"] }) });
  let claims = 0;
  try {
    await assert.rejects(() => runNodeJob({ configuration: localConfiguration(root), job: "credential-job",
      credentialsDirectory: null, fleet: root, nodeId: "cold-red-gate",
      claim: async () => { claims++; throw Error("should not claim"); } }), /no credentials directory/);
    assert.equal(claims, 0);
  } finally { await rm(root, { recursive: true }); }
});

test("an absent installed release never consumes a fleet scheduling window", async () => {
  const root = await deployment({ "missing-release.json": job("missing-release") });
  const restore = await fakeSystemctl(root);
  let claims = 0;
  try {
    await assert.rejects(() => runNodeJob({ configuration: {
      ...localConfiguration(root), runtimeRoot: join(root, "not-installed") },
      job: "missing-release", fleet: root, nodeId: "cold-red-gate",
      claim: async () => { claims++; throw Error("should not claim"); } }), /ENOENT/);
    assert.equal(claims, 0);
  } finally { restore(); await rm(root, { recursive: true }); }
});

test("an unavailable local unit manager never consumes a fleet scheduling window", async () => {
  const root = await deployment({ "no-systemd.json": job("no-systemd") });
  const restore = await fakeSystemctl(root, "error");
  let claims = 0;
  try {
    await assert.rejects(() => runNodeJob({ configuration: localConfiguration(root), job: "no-systemd",
      fleet: root, nodeId: "cold-red-gate",
      claim: async () => { claims++; throw Error("should not claim"); } }), /systemctl could not read/);
    assert.equal(claims, 0);
  } finally { restore(); await rm(root, { recursive: true }); }
});

test("a run is given the node's data root, and a job's declared environment still wins", async () => {
  const root = await deployment({ "admit.json": job("admit"), "elsewhere.json": job("elsewhere", { environment: { METROPLAT_DATA_ROOT: "/declared" } }) });
  const bin = join(root, "bin"), asked = join(root, "asked.json"), path = process.env.PATH;
  await mkdir(bin);
  await writeFile(join(bin, "package.json"), JSON.stringify({ type: "commonjs" }));
  // Stand-ins for the user service manager: systemctl reports the unit inactive, systemd-run records its arguments.
  await writeFile(join(bin, "systemctl"), `#!${process.execPath}\nprocess.stdout.write("inactive\\n");\n`, { mode: 0o700 });
  await writeFile(join(bin, "systemd-run"), `#!${process.execPath}\nrequire("node:fs").writeFileSync(${JSON.stringify(asked)}, JSON.stringify(process.argv.slice(2)));\n`, { mode: 0o700 });
  process.env.PATH = `${bin}:${path}`;
  const setenv = async (id) => {
    await runNodeJob({ configuration: { runtimeRoot: root, jobsDirectory: "deploy/jobs", stateRoot: join(root, "state"), unitPrefix: "x", artifact: root }, job: id, dataRoot: "/node/data", home: root });
    return JSON.parse(await readFile(asked, "utf8")).filter((argument) => argument.startsWith("--setenv=METROPLAT_DATA_ROOT="));
  };
  try {
    assert.deepEqual(await setenv("admit"), ["--setenv=METROPLAT_DATA_ROOT=/node/data"]);
    assert.deepEqual(await setenv("elsewhere"), ["--setenv=METROPLAT_DATA_ROOT=/declared"]);
  } finally { process.env.PATH = path; await rm(root, { recursive: true }); }
});

test("missing rendered credential files never reserve a fleet window", async () => {
  const root = await deployment({ "secure.json": job("secure", { credentials: ["seller-api", "billing-api"] }) });
  const rendered = join(root, "rendered");
  await mkdir(rendered);
  let claims = 0;
  const invoke = (directory = rendered) => runNodeJob({
    configuration: localConfiguration(root), job: "secure", credentialsDirectory: directory,
    fleet: root, nodeId: "cold-red-gate",
    claim: async () => { claims++; throw new Error("must not claim before rendered credential readiness"); },
  });
  try {
    await assert.rejects(invoke, /no readable rendered credentials for seller-api/);
    await assert.rejects(() => invoke(join(root, "missing-rendered")), /no readable rendered credentials for seller-api/);
    await mkdir(join(rendered, "seller-api.env"));
    await assert.rejects(invoke, /no readable rendered credentials for seller-api/);
    await rm(join(rendered, "seller-api.env"), { recursive: true });
    await writeFile(join(rendered, "seller-api.env"), "");
    await assert.rejects(invoke, /no readable rendered credentials for billing-api/);
    assert.equal(claims, 0, "unavailable EnvironmentFiles must not consume a bid");
  } finally { await rm(root, { recursive: true }); }
});

test("readable rendered credentials preserve the qualified claim path", async () => {
  const root = await deployment({ "secure.json": job("secure", { credentials: ["seller-api", "billing-api"] }) });
  const rendered = join(root, "rendered");
  await mkdir(rendered);
  await writeFile(join(rendered, "seller-api.env"), "");
  await writeFile(join(rendered, "billing-api.env"), "");
  const restore = await fakeSystemctl(root, "inactive");
  let claims = 0;
  try {
    const outcome = await runNodeJob({
      configuration: localConfiguration(root), job: "secure", credentialsDirectory: rendered,
      fleet: root, nodeId: "cold-red-gate",
      claim: async () => { claims++; return { run: false, state: "claimed-elsewhere", window: "20261023T120000Z" }; },
    });
    assert.equal(claims, 1);
    assert.equal(outcome.state, "claimed-elsewhere", "file readiness is not fleet authorization");
  } finally { restore(); await rm(root, { recursive: true }); }
});
