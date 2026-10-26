#!/usr/bin/env node
// Usage: fleet-sync.mjs <fleet-clone> [--jobs deploy/jobs ...] [--capability name ...]
// Runs on every node on a timer. Publishes only facts about this node: its observation, the job
// declarations it carries, and for each of those jobs why it cannot run it (refuses) or what running it
// would cost now (costs). Nothing about any other node is written, so no two nodes ever edit one file.
import { readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { parseArgs } from "node:util";
import { publish } from "../src/fleet.mjs";
import { observeNode } from "../src/observe.mjs";
import { roundedCostOf, refusals } from "../src/placement.mjs";

const { values, positionals } = parseArgs({ allowPositionals: true, options: { capability: { type: "string", multiple: true, default: [] }, jobs: { type: "string", multiple: true, default: [] } } });
const fleet = resolve(positionals[0] ?? ".");
const declarations = values.jobs.flatMap((directory) => readdirSync(directory).filter((name) => name.endsWith(".json")).sort()
  .map((name) => JSON.parse(readFileSync(join(directory, name), "utf8")))).filter((job) => typeof job?.id === "string");
const observed = observeNode({ capabilities: values.capability, jobs: declarations.map((job) => job.id) });
const refuses = Object.fromEntries(declarations.map((job) => [job.id, refusals(job, observed)]).filter(([, why]) => why.length));
const costs = Object.fromEntries(declarations.filter((job) => !refuses[job.id]).map((job) => [job.id, roundedCostOf(job, observed)]));
const observation = { ...observed, refuses, costs };
const metrics = {};
const beforePublish = performance.now();
const pushed = publish(fleet, [
  { path: `nodes/${observation.id}.json`, value: observation },
  ...declarations.map((job) => ({ path: `jobs/${job.id}.json`, value: job })),
], `Observe ${observation.id}`, metrics);
const publishMs = Math.round(performance.now() - beforePublish);
console.log(JSON.stringify({ observed: observation.id, pushed, load1: observation.load1, memoryAvailableGb: observation.memoryAvailableGb,
  carries: declarations.length, refuses: Object.keys(refuses).length,
  publishMeasurement: { kind: "fleet-publish-meters/v1", wallMs: publishMs, ...metrics } }));
if (!pushed) process.exitCode = 1;
