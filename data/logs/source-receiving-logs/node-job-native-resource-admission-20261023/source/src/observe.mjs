// What a node can offer right now, read from the node itself.
import { cpus, totalmem, freemem, loadavg, hostname } from "node:os";
import { accessSync, constants, existsSync, readdirSync, readlinkSync, statfsSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { OBSERVATION_KIND } from "./placement.mjs";

const GB = 1024 ** 3;
const round = (value) => Math.round(value * 100) / 100;

/** Preserve source precision when pricing scarce resources; unknown samples remain null, not free. */
export function observedResourceUnits({ load1, memoryAvailableBytes, diskAvailableBytes }) {
  const valid = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0;
  return {
    load1: valid(load1) ? load1 : null,
    memoryAvailableGb: valid(memoryAvailableBytes) ? memoryAvailableBytes / GB : null,
    freeDiskGb: valid(diskAvailableBytes) ? diskAvailableBytes / GB : null,
  };
}

function availableMemory() {
  // MemAvailable counts reclaimable cache; freemem() alone makes every Linux node look full.
  try {
    const kb = /MemAvailable:\s+(\d+)/.exec(readFileSync("/proc/meminfo", "utf8"))?.[1];
    if (kb) return Number(kb) * 1024;
  } catch {}
  return freemem();
}

/** Credential services a node holds: the `<service>.env` files rendered into its credentials directory. */
export function heldCredentials(directory) {
  if (!directory || !existsSync(directory)) return [];
  // A filename alone cannot advertise a host credential the runner cannot open.
  // Match the runner's metadata-only, user-access preflight; never inspect secret values.
  return readdirSync(directory).filter((name) => name.endsWith(".env")).filter((name) => {
    try {
      const file = join(directory, name);
      if (!statSync(file).isFile()) return false;
      accessSync(file, constants.R_OK);
      return true;
    } catch { return false; }
  }).map((name) => name.slice(0, -4)).sort();
}

// Capabilities a node can prove about itself; flags only add what the OS cannot show.
export function detectCapabilities({ exists = existsSync, env = process.env } = {}) {
  const found = [];
  if (env.XDG_RUNTIME_DIR && exists(`${env.XDG_RUNTIME_DIR}/systemd`)) found.push("systemd-user");
  if (exists("/gnu/store")) found.push("guix");
  return found;
}

/**
 * Job units an operator masked on this node (a unit file linked to /dev/null, runtime or persistent), as
 * the job ids they name. A mask silently swallows every start, so the node must publish it as a refusal.
 */
export function maskedJobs({ env = process.env, home = env.HOME } = {}) {
  const directories = [env.XDG_RUNTIME_DIR && `${env.XDG_RUNTIME_DIR}/systemd/user`, home && `${home}/.config/systemd/user`, "/etc/systemd/user"].filter(Boolean);
  const masked = new Set();
  for (const directory of directories) {
    if (!existsSync(directory)) continue;
    for (const name of readdirSync(directory)) {
      const job = /-job-(.+)\.service$/.exec(name)?.[1];
      if (!job) continue;
      try { if (readlinkSync(`${directory}/${name}`) === "/dev/null") masked.add(job); } catch {}
    }
  }
  return [...masked].sort();
}

export function observeNode({ id = process.env.NODE_JOB_NODE_ID ?? hostname(), capabilities = [], credentialsDirectory = process.env.CREDENTIALS_DIRECTORY ?? process.env.NODE_JOB_CREDENTIALS_DIRECTORY, diskPath = process.env.HOME ?? "/", jobs = null, masked = maskedJobs(), now = new Date() } = {}) {
  const disk = statfsSync(diskPath);
  return {
    kind: OBSERVATION_KIND,
    id,
    observedAt: now.toISOString(),
    capabilities: [...new Set([...detectCapabilities(), ...capabilities])].sort(),
    cores: cpus().length,
    memoryGb: round(totalmem() / GB),
    ...observedResourceUnits({
      load1: loadavg()[0], memoryAvailableBytes: availableMemory(),
      diskAvailableBytes: disk.bavail * disk.bsize,
    }),
    credentials: heldCredentials(credentialsDirectory),
    masked,
    ...(jobs === null ? {} : { jobs: [...new Set(jobs)].sort() }),
  };
}
