import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import path from "node:path";
import test from "node:test";

import { EMPTY_WITNESS_ROOT } from "@red-cup-engineering/computer-content-address-engineering-services-section/semantic-content-identity";

const script = fileURLToPath(new URL("../../src/semiotic-expression-notation/runtime/semantic-content-identity-cli.mjs", import.meta.url));
const content = Object.freeze({
  objectKind: "example.cli-mark",
  semanticType: ["base"],
  term: ["mark", "body"],
  witnessRoot: EMPTY_WITNESS_ROOT,
});

function invoke(args = [], input = content) {
  return spawnSync(process.execPath, [...process.execArgv.filter((arg) => !arg.startsWith("--test")), script, ...args], {
    input: JSON.stringify(input), encoding: "utf8", timeout: 5_000,
  });
}

test("CLI emits the admitted semantic carrier and base64 bytes", () => {
  const result = invoke();
  assert.equal(result.status, 0, result.stderr);
  const receipt = JSON.parse(result.stdout);
  assert.equal(receipt.id, receipt.token);
  assert.equal(receipt.envelope.objectKind, content.objectKind);
  assert.match(receipt.bytes, /^[A-Za-z0-9+/]+=*$/u);
});

test("CLI writes exact canonical bytes only with an explicit output path", async (t) => {
  const directory = await mkdtemp(path.join(tmpdir(), "semantic-content-identity-cli-"));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const output = path.join(directory, "identity.sen.cbor");
  const result = invoke(["--output", output]);
  assert.equal(result.status, 0, result.stderr);
  const receipt = JSON.parse(result.stdout);
  assert.equal(receipt.output, output);
  assert.equal((await readFile(output)).length, receipt.byteLength);
});
