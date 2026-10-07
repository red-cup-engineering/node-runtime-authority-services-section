import assert from "node:assert/strict";
import test from "node:test";
import { applyActivePathRelocation, planActivePathRelocation, relocateRepositoryPath } from "../src/workspace-path-relocation.mjs";

const root = "/work/repository";

test("projects active package file dependencies and absolute configuration paths through a relocation", () => {
  const source = { type: "active-path-reference-source", version: 1, kind: "json", path: "packages/consumer/package.json", text: '{"dependencies":{"core":"file:../old-core"},"config":"/work/repository/packages/old-core/data.json"}' };
  const plan = planActivePathRelocation(source, { repositoryRoot: root, relocations: [{ from: "packages/old-core", to: "computer-data/core" }] });
  const receipt = applyActivePathRelocation(source, plan);
  assert.equal(plan.relocatedPath, "packages/consumer/package.json");
  assert.equal(receipt.text, '{"dependencies":{"core":"file:../../computer-data/core"},"config":"/work/repository/computer-data/core/data.json"}');
});

test("rebases active Markdown links when the referring document moves", () => {
  const source = { type: "active-path-reference-source", version: 1, kind: "markdown", path: "old/docs/guide.md", text: "[core](../core/readme.md?format=full#usage)\n[bare](core/guide.md)\n[web](https://example.test/old/core)\n" };
  const plan = planActivePathRelocation(source, { repositoryRoot: root, relocations: [{ from: "old/docs", to: "computer-code/docs" }] });
  const receipt = applyActivePathRelocation(source, plan);
  assert.equal(receipt.relocatedPath, "computer-code/docs/guide.md");
  assert.equal(receipt.text, "[core](../../old/core/readme.md?format=full#usage)\n[bare](./core/guide.md)\n[web](https://example.test/old/core)\n");
});

test("projects parser-admitted module literals without scanning prose strings", () => {
  const text = 'import core from "../../old-core/index.mjs";\nconst prose = "../../old-core/index.mjs";\n';
  const literal = '"../../old-core/index.mjs"';
  const start = text.indexOf(literal);
  const source = { type: "active-path-reference-source", version: 1, kind: "module", path: "packages/consumer/src/main.mjs", text, references: [{ start, end: start + literal.length, value: "../../old-core/index.mjs" }] };
  const receipt = applyActivePathRelocation(source, planActivePathRelocation(source, { repositoryRoot: root, relocations: [{ from: "packages/old-core", to: "computer-data/core" }] }));
  assert.equal(receipt.text, 'import core from "../../../computer-data/core/index.mjs";\nconst prose = "../../old-core/index.mjs";\n');
});

test("rejects inactive carriers and stale source bytes", () => {
  assert.throws(() => planActivePathRelocation({ type: "journal", version: 1, kind: "json", path: "data/log.json", text: "{}" }, { repositoryRoot: root, relocations: [{ from: "a", to: "b" }] }), /active JSON/u);
  const source = { type: "active-path-reference-source", version: 1, kind: "json", path: "a/config.json", text: '{"path":"a/x"}' };
  const plan = planActivePathRelocation(source, { repositoryRoot: root, relocations: [{ from: "a", to: "b" }] });
  assert.throws(() => applyActivePathRelocation({ ...source, text: `${source.text}\n` }, plan), /changed after/u);
});

test("exposes selected-file projection and pathname projection without filesystem access", () => {
  const source = { type: "active-path-reference-source", version: 1, kind: "json", path: "a/config.json", text: '{"path":"a/x"}' };
  const plan = planActivePathRelocation(source, { repositoryRoot: root, relocations: [{ from: "a", to: "b" }] });
  assert.equal(relocateRepositoryPath("a/config.json", [{ from: "a", to: "b" }]), "b/config.json");
  assert.equal(applyActivePathRelocation(source, plan).text, '{"path":"b/x"}');
});

test("never rewrites JSON object keys that only resemble relocatable paths", () => {
  const source = { type: "active-path-reference-source", version: 1, kind: "json", path: "package.json", text: '{"exports":{"./old-core":"./old-core/index.mjs"}}' };
  const receipt = applyActivePathRelocation(source, planActivePathRelocation(source, { repositoryRoot: root, relocations: [{ from: "old-core", to: "computer-data/core" }] }));
  assert.equal(receipt.text, '{"exports":{"./old-core":"./computer-data/core/index.mjs"}}');
});

test("renders a relocated directory self-reference as the unambiguous relative directory", () => {
  const source = { type: "active-path-reference-source", version: 1, kind: "json", path: "old/package.json", text: '{"dependencies":{"self":"file:."}}' };
  const receipt = applyActivePathRelocation(source, planActivePathRelocation(source, { repositoryRoot: root, relocations: [{ from: "old", to: "computer-code" }] }));
  assert.equal(receipt.text, '{"dependencies":{"self":"file:./"}}');
});
