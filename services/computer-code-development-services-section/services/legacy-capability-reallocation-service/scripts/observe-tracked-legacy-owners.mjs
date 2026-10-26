#!/usr/bin/env node
import { readFileSync, writeFileSync } from "node:fs";
import { observeTrackedLegacyOwnerCandidates } from "../src/legacy-capability-reallocation.mjs";

const [request, output, ...extra] = process.argv.slice(2);
if (!request || extra.length) throw new TypeError("usage: observe-tracked-legacy-owners REQUEST.json [NEW-OUTPUT.json]");
const bytes = readFileSync(request);
if (bytes.length > 262_144) throw new TypeError("request exceeds 256 KiB");
const result = observeTrackedLegacyOwnerCandidates(JSON.parse(bytes.toString("utf8")));
if (output) writeFileSync(output, JSON.stringify(result, null, 2) + "\n", { flag: "wx", mode: 0o600 });
process.stdout.write(JSON.stringify(output ? { kind: result.kind, revision: result.revision, sources: result.records.length, owners: result.owners.length, candidates: result.records.reduce((n, row) => n + row.candidates.length, 0), output } : result) + "\n");
