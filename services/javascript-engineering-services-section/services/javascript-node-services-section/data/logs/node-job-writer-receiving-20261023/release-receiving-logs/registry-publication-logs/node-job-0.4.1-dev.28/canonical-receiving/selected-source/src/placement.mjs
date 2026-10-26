// Where a node job runs, decided by the nodes themselves from a grow-only substrate of facts.
//
// No record of "who runs what" is ever rewritten. Each node publishes facts about itself (its observation,
// the declarations it carries, what it refuses and why), bids for a job's current window when it can run
// it, and records the runs it starts. Every rule below is a pure function of those facts, so any reader
// derives the same answer from the same facts, and merging two copies of the substrate is set union.
//
// Coordination is spent only where claims overlap: two nodes able to run the same job in the same window.
// There the bid that lands first in the substrate's history wins. A node's bid waits in proportion to its
// cost, so the cheapest able node usually lands first: a price signal through the environment, not a
// planner. A job that tolerates a duplicate run (the default) still runs when the substrate is
// unreachable; one declared `exclusive` does not.

export const OBSERVATION_KIND = "node-job-node-observation/v1";
export const BID_KIND = "node-job-bid/v1";
export const RUN_KIND = "node-job-fleet-run/v1";

/**
 * Why this node can never run this job as it stands: static facts only (capabilities, credentials, the
 * declaration, a pin, core count, an operator's mask on its unit). Load, free memory and free disk change minute to minute; they are
 * prices (costOf), never refusals, so the only node able to run a job still runs it when contended.
 */
export function refusals(job, node) {
  const why = [];
  const requires = job.requires ?? {};
  for (const capability of requires.capabilities ?? []) if (!(node.capabilities ?? []).includes(capability)) why.push(`lacks-capability:${capability}`);
  for (const service of job.credentials ?? []) if (!(node.credentials ?? []).includes(service)) why.push(`lacks-credential:${service}`);
  if (!(node.jobs ?? []).includes(job.id)) why.push("lacks-declaration");
  const pinned = job.placement?.pinned;
  if (Array.isArray(pinned) && !pinned.includes(node.id)) why.push("not-pinned-here");
  if ((requires.cores ?? 0) > node.cores) why.push("too-few-cores");
  if ((node.masked ?? []).includes(job.id)) why.push("masked-here");
  return why;
}

/**
 * What running this job costs this node now: CPU contention per core, plus the share of free memory and
 * free disk the job needs. 1 is a node fully busy, or a job taking all that is free; above that the
 * node is overcommitted.
 */
export function costOf(job, node) {
  const requires = job.requires ?? {};
  return node.load1 / node.cores
    + (requires.memoryGb ?? 0.25) / Math.max(node.memoryAvailableGb, 0.01)
    + (requires.freeDiskGb ?? 0) / Math.max(node.freeDiskGb, 0.01);
}

/** Cheaper nodes bid sooner; a free node bids at once, a contended one waits up to a minute. */
export const backoffMs = (cost) => Math.min(60_000, Math.round(cost * 10_000));

/** The window a firing belongs to: the job's own period, or five minutes for calendar and demand jobs. */
export function windowOf(job, at) {
  const period = (job.everySeconds ?? job.trigger?.everySeconds ?? 300) * 1000;
  return new Date(Math.floor(at.getTime() / period) * period).toISOString().replace(/[-:]|\.\d+/g, "");
}

export const bidPath = (job, window, node) => `bids/${job}/${window}/${node}.json`;
export const runPath = (job, window, node) => `runs/${job}/${window}/${node}.json`;

/** Whether a node's latest observation is recent enough to count as alive. */
export const fresh = (node, now, staleAfterMs = 15 * 60_000) => now.getTime() - Date.parse(node.observedAt) <= staleAfterMs;

/**
 * Per job: the alive carriers able to take it with their published cost, and why every other carrier
 * cannot. Reads only what nodes published about themselves (`jobs`, `refuses`, `costs`), so a reader
 * never re-derives a node's state.
 */
export function servability(jobs, nodes, now = new Date()) {
  return Object.fromEntries(jobs.map((job) => {
    const carriers = nodes.filter((node) => (node.jobs ?? []).includes(job.id));
    const able = carriers.filter((node) => fresh(node, now) && !(node.refuses?.[job.id]?.length));
    const refused = Object.fromEntries(carriers.filter((node) => !able.includes(node))
      .map((node) => [node.id, fresh(node, now) ? node.refuses[job.id] : ["observation-stale"]]));
    const costs = Object.fromEntries(able.map((node) => [node.id, node.costs?.[job.id] ?? null]));
    const cheapest = Math.min(...Object.values(costs).filter((cost) => cost !== null));
    return [job.id, { able: able.map((node) => node.id), costs, cheapest: Number.isFinite(cheapest) ? cheapest : null, refused }];
  }));
}
