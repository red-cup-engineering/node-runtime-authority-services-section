import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { createRelationWeb } from "@red-cup-engineering/graph-data-service/relation-web";
import { guixModuleClaims, observeGuileModuleFile, observeGuileModuleSource } from "../scripts/observe-guile-module.mjs";

function findRepoRoot(from) {
  let current = resolve(from);
  while (dirname(current) !== current) {
    if (existsSync(resolve(current, "guix/phezi/ochage/packages/koios-news.scm"))) return current;
    current = dirname(current);
  }
  throw new Error("repository Guix fixture not found");
}

test("Guile's native reader observes define-module uses and exports without evaluation", async () => {
  const source = [
    "(define-module (example package)",
    "  #:use-module (guix packages)",
    "  #:use-module (guix gexp)",
    "  #:export (example-package helper))",
    "(error \"this form must never be evaluated\")",
  ].join("\n");
  const observed = await observeGuileModuleSource({ source, path: "example/package.scm" });

  assert.equal(observed.id, "(example package)");
  assert.deepEqual(observed.uses, ["(guix packages)", "(guix gexp)"]);
  assert.deepEqual(observed.exports, ["example-package", "helper"]);
  assert.equal(observed.evidence.evaluated, false);
  assert.match(observed.evidence.sha256, /^sha256:[0-9a-f]{64}$/u);
});

test("a real repository Guix module flows through the relation web with file provenance", async () => {
  const repoRoot = findRepoRoot(import.meta.dirname);
  const path = resolve(repoRoot, "guix/phezi/ochage/packages/koios-news.scm");
  const observed = await observeGuileModuleFile(path);
  const claims = guixModuleClaims([observed]);
  const web = createRelationWeb();
  web.observe({
    id: observed.evidence.sha256,
    source: observed.evidence,
    relations: claims,
  });

  assert.equal(observed.id, "(phezi ochage packages koios-news)");
  assert.ok(observed.uses.includes("(guix packages)"));
  assert.ok(observed.exports.includes("koios-news-scheduled-runtime-package"));
  const relation = web.query({
    subject: observed.id,
    predicate: "uses-module",
    object: "(guix packages)",
  });
  assert.equal(relation.length, 1);
  assert.equal(relation[0].source.resource, path);
  assert.equal(relation[0].source.evaluated, false);
});

test("a module-less Guix entrypoint keeps its path identity and top-level use-modules", async () => {
  const repoRoot = findRepoRoot(import.meta.dirname);
  const path = resolve(repoRoot, "guix.scm");
  const observed = await observeGuileModuleFile(path);

  assert.equal(observed.id, path);
  assert.equal(observed.module, null);
  assert.deepEqual(observed.uses, ["(guix gexp)", "(phezi ochage packages atlas)"]);
  assert.deepEqual(observed.exports, []);
});
