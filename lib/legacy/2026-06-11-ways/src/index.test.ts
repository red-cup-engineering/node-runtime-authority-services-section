// Theorem-shaped tests over the checker and catalog.
import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { INVARIANTS } from "./invariants.ts";
import { checkPackage, layerOf } from "./check.ts";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "..", "..", "..");

test("every invariant id is unique and every invariant names its way", () => {
  const ids = INVARIANTS.map((i) => i.id);
  assert.equal(new Set(ids).size, ids.length);
  for (const i of INVARIANTS) assert.ok(i.way.length > 0, `${i.id} names no way`);
});

test("layerOf reads the layer from the directory, and rejects strays", () => {
  assert.equal(layerOf(path.join(repoRoot, "apps", "ways")), "apps");
  assert.equal(layerOf(path.join(repoRoot, "lib", "meme-topology")), "lib");
  assert.throws(() => layerOf(repoRoot), TypeError);
});

test("ways judges itself: report settles, charges partition the findings", async () => {
  const report = await checkPackage(path.join(repoRoot, "apps", "ways"), repoRoot);
  assert.equal(report.layer, "apps");
  assert.ok(report.findings.length > 0);
  const total = Object.values(report.settled).reduce((a, b) => a + b, 0);
  assert.equal(total, report.findings.length);
  for (const f of report.findings) {
    assert.ok(["potential", "active", "stable", "absurd"].includes(f.charge));
    assert.ok(Object.isFrozen(f));
  }
  // Self-lawfulness on the manifest invariants (M1-M4 potential).
  for (const id of ["M1", "M2", "M3", "M4"]) {
    const f = report.findings.find((x) => x.invariant === id);
    assert.equal(f?.charge, "potential", `${id} should be potential on ways itself: ${f?.message}`);
  }
});

test("the zero-dep codec exemplar is lawful on layering", async () => {
  const report = await checkPackage(path.join(repoRoot, "lib", "news-codecs"), repoRoot);
  const l4 = report.findings.find((f) => f.invariant === "L4");
  assert.equal(l4?.charge, "potential", `news-codecs L4: ${l4?.message}`);
});
