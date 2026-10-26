// The fleet substrate: a git clone that only ever gains files. Facts are added, never edited, except each
// node's own observation, a single-writer register whose newer value always supersedes the older.
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { BID_KIND, RUN_KIND, backoffMs, bidPath, costOf, refusals, runPath, windowOf } from "./placement.mjs";

const git = (clone, ...args) => execFileSync("git", ["-C", clone, ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });

export function pull(clone) {
  try { git(clone, "pull", "--quiet", "--rebase", "--autostash"); return true; } catch { return false; }
}

/** Add facts and push them. Returns false when the substrate cannot be reached; the facts stay committed locally. */
export function publish(clone, facts, message) {
  for (let attempt = 1; attempt <= 4; attempt++) {
    pull(clone);
    for (const { path, value } of facts) {
      mkdirSync(dirname(join(clone, path)), { recursive: true });
      writeFileSync(join(clone, path), `${JSON.stringify(value, null, 2)}\n`);
      git(clone, "add", path);
    }
    git(clone, "commit", "--quiet", "--allow-empty", "-m", message);
    try { git(clone, "push", "--quiet"); return true; } catch { if (attempt < 4) git(clone, "reset", "--quiet", "--soft", "HEAD~1"); }
  }
  return false;
}

/** The node whose bid for this window entered the substrate's history first. */
export function firstBidder(clone, job, window) {
  const added = git(clone, "log", "--reverse", "--diff-filter=A", "--format=", "--name-only", "--", `bids/${job}/${window}/`).split("\n").filter(Boolean);
  return added.length ? added[0].split("/").pop().replace(/\.json$/, "") : null;
}

const present = (clone, directory) => existsSync(join(clone, directory)) ? readdirSync(join(clone, directory)).map((name) => name.replace(/\.json$/, "")) : [];

/**
 * Decide whether this node runs this job's current window. `observation` is this node's own, fresh.
 * Returns { run, state, ... }; when run is true the caller starts the job and then calls recordRun.
 */
export async function claimWindow({ clone, job, observation, now = new Date(), wait = sleep }) {
  const window = windowOf(job, now);
  const refused = refusals(job, observation);
  if (refused.length) return { run: false, state: "refused-here", window, refused };
  const cost = costOf(job, observation);
  await wait(backoffMs(cost));
  const reachable = pull(clone);
  const already = present(clone, `bids/${job.id}/${window}`);
  if (already.length && !already.includes(observation.id)) return { run: false, state: "claimed-elsewhere", window, by: firstBidder(clone, job.id, window) ?? already[0] };
  const pushed = reachable && publish(clone, [{ path: bidPath(job.id, window, observation.id), value: { kind: BID_KIND, job: job.id, window, node: observation.id, cost, at: new Date().toISOString() } }], `Bid ${observation.id} for ${job.id} ${window}`);
  if (!pushed) return job.exclusive ? { run: false, state: "fleet-unreachable", window } : { run: true, state: "uncoordinated", window, cost };
  const winner = firstBidder(clone, job.id, window);
  return winner === observation.id ? { run: true, state: "won", window, cost } : { run: false, state: "claimed-elsewhere", window, by: winner };
}

export function recordRun(clone, { job, window, node, unit, release }) {
  return publish(clone, [{ path: runPath(job, window, node), value: { kind: RUN_KIND, job, window, node, unit, release, startedAt: new Date().toISOString() } }], `Run ${job} ${window} on ${node}`);
}
