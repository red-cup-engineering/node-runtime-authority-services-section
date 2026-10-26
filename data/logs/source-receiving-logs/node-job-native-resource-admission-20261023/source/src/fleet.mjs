// The fleet substrate: a git clone that only ever gains files. Facts are added, never edited, except each
// node's own observation, a single-writer register whose newer value always supersedes the older.
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { BID_KIND, RUN_KIND, backoffMs, bidPath, costOf, fresh, refusals, runPath, windowReadingOf } from "./placement.mjs";

const git = (clone, ...args) => execFileSync("git", ["-C", clone, ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });

export function pull(clone) {
  try { git(clone, "pull", "--quiet", "--rebase", "--autostash"); return true; } catch { return false; }
}

/** Add facts and push them. Returns false when the substrate cannot be reached; the facts stay committed locally. */
export function publish(clone, facts, message, metrics = null) {
  if (metrics !== null && (typeof metrics !== "object" || Array.isArray(metrics))) throw new TypeError("publish metrics must be an object");
  if (metrics) Object.assign(metrics, { attempts: 0, pulls: 0, pullSuccesses: 0, writes: 0, writtenBytes: 0, addCalls: 0, stagedDiffChecks: 0, unchangedPublishes: 0, commits: 0, pushAttempts: 0 });
  const count = (name, amount = 1) => { if (metrics) metrics[name] += amount; };
  for (let attempt = 1; attempt <= 4; attempt++) {
    count("attempts");
    count("pulls");
    const pulled = pull(clone);
    if (pulled) count("pullSuccesses");
    let changedFiles = 0;
    // The observation changes every cycle; the installed declarations usually do not.
    // Do not rewrite identical bytes or spawn one git-add process per declaration.
    for (const { path, value } of facts) {
      const target = join(clone, path), serialized = `${JSON.stringify(value, null, 2)}\n`;
      if (!existsSync(target) || readFileSync(target, "utf8") !== serialized) {
        mkdirSync(dirname(target), { recursive: true });
        writeFileSync(target, serialized);
        changedFiles++;
        count("writes");
        count("writtenBytes", Buffer.byteLength(serialized, "utf8"));
      }
    }
    // Unchanged local facts cannot prove remote admission while disconnected.
    // Retry remote reads without paying for redundant staging, commits or pushes.
    if (!changedFiles && !pulled) continue;
    if (facts.length) {
      count("addCalls");
      git(clone, "add", "--", ...facts.map(({ path }) => path));
    }
    // An identical snapshot already read back from a reachable remote needs no empty
    // commit or push. Do not skip a staged-but-uncommitted fact or mistake an
    // unreachable remote for a successfully published snapshot.
    if (!changedFiles && pulled) {
      count("stagedDiffChecks");
      let unchanged = false;
      try { git(clone, "diff", "--cached", "--quiet"); unchanged = true; }
      catch (error) { if (error?.status !== 1) return false; }
      if (unchanged) { count("unchangedPublishes"); return true; }
    }
    git(clone, "commit", "--quiet", "--allow-empty", "-m", message);
    count("commits");
    count("pushAttempts");
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
export async function claimWindow({ clone, job, observation, now = new Date(), wait = sleep, clock = () => now }) {
  // Original schedule occurrence is an admission precondition, not a claim
  // manufactured by observing a wake. Refuse before wait, clone I/O or bid.
  const due = windowReadingOf(job, now);
  const window = due.window;
  if (window === null) return { run: false, state: due.reason, window: null };
  const refused = refusals(job, observation);
  if (refused.length) return { run: false, state: "refused-here", window, refused };
  if (!fresh(observation, now)) return { run: false, state: "untrusted-observation", window };
  const cost = costOf(job, observation);
  if (cost === null) return { run: false, state: "unpriced-here", window };
  await wait(backoffMs(cost));
  // Backoff and remote contention take actual time. A due alarm is not a
  // lease: if the original occurrence/deadline ceased to be eligible during
  // the delay, refuse BEFORE any Git bid. The production runner supplies its
  // real host clock; fixed-time callers can retain a deterministic test clock.
  if (windowReadingOf(job, clock()).window !== window)
    return { run: false, state: "window-changed-before-bid", window };
  const reachable = pull(clone);
  // A prior run witness bars replay even when an older uncoordinated run has no bid.
  // This is local/substrate evidence, not a global exactly-once transaction.
  if (existsSync(join(clone, runPath(job.id, window, observation.id))))
    return { run: false, state: "already-run-here", window };
  const already = present(clone, `bids/${job.id}/${window}`);
  // A published bid does not renew permission to run the same window. In particular, a
  // retry after a lost response must not duplicate an expensive or consequential job.
  // A prior bid with no run receipt is still held: absence of a run is not proof of safety.
  if (already.includes(observation.id)) return { run: false, state: "already-bid-here", window };
  if (already.length && !already.includes(observation.id)) return { run: false, state: "claimed-elsewhere", window, by: firstBidder(clone, job.id, window) ?? already[0] };
  const pushed = reachable && publish(clone, [{ path: bidPath(job.id, window, observation.id), value: { kind: BID_KIND, job: job.id, window, node: observation.id, cost, at: new Date().toISOString() } }], `Bid ${observation.id} for ${job.id} ${window}`);
  if (!pushed) return job.exclusive ? { run: false, state: "fleet-unreachable", window } : { run: true, state: "uncoordinated", window, cost };
  const winner = firstBidder(clone, job.id, window);
  return winner === observation.id ? { run: true, state: "won", window, cost } : { run: false, state: "claimed-elsewhere", window, by: winner };
}

export function recordRun(clone, { job, window, node, unit, release }) {
  return publish(clone, [{ path: runPath(job, window, node), value: { kind: RUN_KIND, job, window, node, unit, release, startedAt: new Date().toISOString() } }], `Run ${job} ${window} on ${node}`);
}
