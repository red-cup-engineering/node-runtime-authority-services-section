#!/usr/bin/env node
// Usage: install-fleet-sync.mjs --store <git-url> [--branch fleet-facts] [--id node-id] [--jobs dir ...]
//        [--capability name ...] [--credentials dir]
// Joins this node to the fleet: clones the fleet store, installs a systemd user timer that runs fleet-sync
// every 5 minutes, and exports NODE_JOB_NODE_ID / NODE_JOB_FLEET to every unit the user manager starts,
// so runNodeJob on this node bids for each job's window against the other nodes able to run it. Each sync first
// fast-forwards this service's own clone, so every node converges on the current rules without a reinstall.
// Idempotent; rerun to change the arguments.
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { hostname, homedir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

const { values } = parseArgs({ options: {
  store: { type: "string" }, branch: { type: "string", default: "fleet-facts" }, id: { type: "string", default: hostname() }, credentials: { type: "string" },
  jobs: { type: "string", multiple: true, default: [] }, capability: { type: "string", multiple: true, default: [] },
} });
if (!values.store) throw new Error("--store <git-url> is required");

const state = join(process.env.XDG_STATE_HOME ?? join(homedir(), ".local/state"), "node-fleet");
const clone = join(state, "store");
const units = join(process.env.XDG_CONFIG_HOME ?? join(homedir(), ".config"), "systemd/user");
const environment = join(process.env.XDG_CONFIG_HOME ?? join(homedir(), ".config"), "environment.d");
const sync = fileURLToPath(new URL("./fleet-sync.mjs", import.meta.url));
const code = fileURLToPath(new URL("..", import.meta.url));
const quote = (value) => `"${String(value).replaceAll("\\", "\\\\").replaceAll('"', '\\"')}"`;

mkdirSync(state, { recursive: true }); mkdirSync(units, { recursive: true }); mkdirSync(environment, { recursive: true });
if (!existsSync(join(clone, ".git"))) execFileSync("git", ["clone", "--quiet", "--single-branch", "--branch", values.branch, values.store, clone], { stdio: "inherit" });

const variables = {
  NODE_JOB_NODE_ID: values.id,
  NODE_JOB_FLEET: clone,
  ...(values.credentials ? { NODE_JOB_CREDENTIALS_DIRECTORY: values.credentials } : {}),
};
writeFileSync(join(environment, "60-node-fleet.conf"), Object.entries(variables).map(([key, value]) => `${key}=${value}`).join("\n") + "\n");
const args = [sync, clone, ...values.jobs.flatMap((dir) => ["--jobs", dir]), ...values.capability.flatMap((name) => ["--capability", name])];
writeFileSync(join(units, "node-fleet-sync.service"), `[Unit]
Description=Publish this node's observation, carried jobs and prices to the fleet substrate

[Service]
Type=oneshot
${Object.entries(variables).map(([key, value]) => `Environment=${quote(`${key}=${value}`)}`).join("\n")}
ExecStartPre=-${[execFileSync("sh", ["-c", "command -v git"], { encoding: "utf8" }).trim(), "-C", code, "pull", "--quiet", "--ff-only"].map(quote).join(" ")}
ExecStart=${[process.execPath, ...args].map(quote).join(" ")}
TimeoutStartSec=120
`);
writeFileSync(join(units, "node-fleet-sync.timer"), `[Unit]
Description=Keep this node's fleet observation fresh

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
RandomizedDelaySec=30s
Persistent=true

[Install]
WantedBy=timers.target
`);
const systemctl = (...rest) => execFileSync("systemctl", ["--user", ...rest], { stdio: "inherit" });
systemctl("set-environment", ...Object.entries(variables).map(([key, value]) => `${key}=${value}`));
systemctl("daemon-reload");
systemctl("enable", "--now", "node-fleet-sync.timer");
systemctl("start", "node-fleet-sync.service");
console.log(JSON.stringify({ joined: values.id, store: values.store, branch: values.branch, clone }));
