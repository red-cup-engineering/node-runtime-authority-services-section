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
// Placement prices are dimensionless contention measures, never dollars or entitlements.
// Missing, contradictory or nonfinite readings cannot authorize a fleet claim.
const nonnegative = (v) => typeof v === "number" && Number.isFinite(v) && v >= 0;
const positive = (v) => nonnegative(v) && v > 0;

/** Return null, not zero or NaN, when a necessary resource reading is unavailable. */
export function costOf(job, node) {
  const requires = job.requires ?? {};
  const memoryGb = requires.memoryGb ?? 0.25;
  const diskGb = requires.freeDiskGb ?? 0;
  if (!nonnegative(node?.load1) || !positive(node?.cores)
    || !nonnegative(memoryGb) || !nonnegative(diskGb)
    || (memoryGb > 0 && !positive(node?.memoryAvailableGb))
    || (diskGb > 0 && !positive(node?.freeDiskGb))) return null;
  const cost = node.load1 / node.cores
    + (memoryGb > 0 ? memoryGb / node.memoryAvailableGb : 0)
    + (diskGb > 0 ? diskGb / node.freeDiskGb : 0);
  return nonnegative(cost) ? cost : null;
}

/** A fleet-facts publisher must preserve the difference between null (unknown) and zero (measured idle). */
export function roundedCostOf(job, node) {
  const cost = costOf(job, node);
  if (cost === null) return null;
  // Published prices are centi-unit ceilings: positive contention cannot round to a false zero.
  // Exact zero remains a measured zero, not an absence or an entitlement.
  const rounded = cost === 0 ? 0 : Math.ceil(cost * 100) / 100;
  return nonnegative(rounded) ? rounded : null;
}

/** Reject unknown prices instead of treating NaN as an immediate free bid. */
export function backoffMs(cost) {
  if (!nonnegative(cost)) throw new RangeError("Placement cost must be finite and nonnegative");
  return Math.min(60_000, Math.round(cost * 10_000));
}

/**
 * An interval window belongs to its original firstDueAt instant, not to
 * multiples of the Unix epoch. Calendar/demand use the legacy five-minute
 * CORRELATION bucket; neither that bucket nor this reader proves cron due.
 */
export function absoluteInstantOf(value) {
  const matched = typeof value === "string"
    ? /^([0-9]{4}-[0-9]{2}-[0-9]{2})T((?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9])(?:\.[0-9]{1,3})?(Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$/u.exec(value)
    : null;
  if (!matched) return null;
  const epoch = Date.parse(value);
  if (!Number.isFinite(epoch)) return null;
  const zone = matched[3];
  const offsetMinutes = zone === "Z" ? 0
    : (zone[0] === "+" ? 1 : -1) * (Number(zone.slice(1, 3)) * 60 + Number(zone.slice(4)));
  const echoed = new Date(epoch + offsetMinutes * 60_000).toISOString().slice(0, 19);
  return echoed === matched[1] + "T" + matched[2] ? epoch : null;
}
// The optional millisecond suffix is part of identity: two distinct legitimate
// firstDueAt instants within one UTC second may not borrow each other's bid.
const windowKey = epoch => new Date(epoch).toISOString()
  .replace(/[-:]/g, "").replace(/\.000Z$/u, "Z");

export function windowReadingOf(job, at) {
  const instant = at instanceof Date ? at.getTime() : NaN;
  if (!Number.isFinite(instant)) return { window: null, reason: "invalid-observed-clock" };
  const seconds = job?.everySeconds ?? job?.trigger?.everySeconds;
  if (seconds === undefined) {
    return { window: windowKey(Math.floor(instant / 300_000) * 300_000),
      basis: "coarse-correlation-bucket-not-cron-due" };
  }
  const first = absoluteInstantOf(job?.firstDueAt ?? job?.trigger?.firstDueAt);
  if (!Number.isSafeInteger(seconds) || seconds < 60 || seconds > 31_536_000 || first === null)
    return { window: null, reason: "invalid-interval-source" };
  if (instant < first) return { window: null, reason: "not-yet-due" };
  const period = seconds * 1000;
  const due = first + Math.floor((instant - first) / period) * period;
  const latenessMs = instant - due;
  const deadline = job?.startingDeadlineSeconds ?? job?.trigger?.startingDeadlineSeconds;
  if (deadline !== undefined && (!Number.isSafeInteger(deadline) || deadline < 1 || deadline > 31_536_000))
    return { window: null, reason: "invalid-starting-deadline" };
  if (deadline !== undefined && latenessMs > deadline * 1000)
    return { window: null, reason: "starting-deadline-expired",
      lastDueAt: new Date(due).toISOString() };
  return { window: windowKey(due), basis: "original-anchored-interval",
    lastDueAt: new Date(due).toISOString(), latenessMs };
}

export function windowOf(job, at) {
  return windowReadingOf(job, at).window;
}

export const bidPath = (job, window, node) => `bids/${job}/${window}/${node}.json`;
export const runPath = (job, window, node) => `runs/${job}/${window}/${node}.json`;

/** Whether a node's latest observation is recent enough to count as alive. */
export function fresh(node, now, staleAfterMs = 15 * 60_000, maxFutureSkewMs = 60_000) {
  const observed = Date.parse(node?.observedAt);
  const current = now instanceof Date ? now.getTime() : NaN;
  const age = current - observed;
  return Number.isFinite(age) && nonnegative(staleAfterMs) && nonnegative(maxFutureSkewMs)
    && age >= -maxFutureSkewMs && age <= staleAfterMs;
}

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
    const costs = Object.fromEntries(able.map((node) => {
      const published = node.costs?.[job.id];
      return [node.id, nonnegative(published) ? published : null];
    }));
    const cheapest = Math.min(...Object.values(costs).filter((cost) => cost !== null));
    return [job.id, { able: able.map((node) => node.id), costs, cheapest: Number.isFinite(cheapest) ? cheapest : null, refused }];
  }));
}
