/**
 * Authored execution limits are independent of fleet placement prices. A capacity
 * sample is a preflight, not a reservation; MemoryMax enforces each admitted run.
 */
import { readFileSync } from "node:fs";

const integer = (value, minimum = 1) => Number.isSafeInteger(value) && value >= minimum;

export function resourceLimitsOf(value, maxSeconds, where) {
  if (value === undefined) return undefined;
  const required = ["memoryMaxBytes", "memorySwapMaxBytes", "tasksMax", "cpuQuotaPercent", "memoryReserveBytes"];
  const allowed = new Set([...required, "memoryHighBytes"]);
  if (value === null || typeof value !== "object" || Array.isArray(value) ||
      Object.keys(value).some(key => !allowed.has(key)) ||
      required.some(key => !integer(value[key], key === "memorySwapMaxBytes" || key === "memoryReserveBytes" ? 0 : 1)) ||
      !integer(maxSeconds) ||
      !Number.isSafeInteger(value.memoryMaxBytes + value.memoryReserveBytes) ||
      (value.memoryHighBytes !== undefined && (!integer(value.memoryHighBytes) || value.memoryHighBytes > value.memoryMaxBytes))) {
    throw new TypeError(`${where} has invalid resources: finite memory, swap, tasks, CPU, reserve and maxSeconds are required`);
  }
  return Object.freeze({ ...value });
}

/** Linux's current physical availability; no cached fleet observation substitutes it. */
export function availableMemoryBytes() {
  const match = /^MemAvailable:\s+(\d+) kB$/mu.exec(readFileSync("/proc/meminfo", "utf8"));
  const bytes = match === null ? NaN : Number(match[1]) * 1024;
  if (!integer(bytes, 0)) throw new Error("node-job: current physical memory availability is unknown");
  return bytes;
}

export function assertResourceAdmission(resources, readAvailable = availableMemoryBytes) {
  if (resources === undefined) return;
  let available;
  try { available = readAvailable(); } catch {
    const error = new Error("node-job: resource admission refused; current physical memory availability is unknown");
    error.code = "NODE_JOB_RESOURCE_ADMISSION";
    throw error;
  }
  const required = resources.memoryMaxBytes + resources.memoryReserveBytes;
  if (!integer(available, 0) || available < required) {
    const error = new Error(`node-job: resource admission refused; available memory ${Number.isSafeInteger(available) ? available : "unknown"}, required ${required}`);
    error.code = "NODE_JOB_RESOURCE_ADMISSION";
    throw error;
  }
}

export function resourceProperties(resources) {
  if (resources === undefined) return [];
  return [
    `--property=MemoryMax=${resources.memoryMaxBytes}`,
    ...(resources.memoryHighBytes === undefined ? [] : [`--property=MemoryHigh=${resources.memoryHighBytes}`]),
    `--property=MemorySwapMax=${resources.memorySwapMaxBytes}`,
    `--property=TasksMax=${resources.tasksMax}`,
    `--property=CPUQuota=${resources.cpuQuotaPercent}%`,
  ];
}
