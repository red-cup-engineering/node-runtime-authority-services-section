import assert from "node:assert/strict";
import test from "node:test";
import { auditText, classifyEvidence } from "../src/audit-content-addressing.mjs";

test("detects canonical NI and raw hex candidates", () => {
  const evidence = auditText(
    'const good = "ni:///sha-256;koqacr8nz6PJjJUPQ9zy04JpLJiP3DSvPGDioN_dqBU";\n' +
    'const old = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";',
    "fixture.mjs",
  );
  assert.equal(evidence.some((item) => item.kind === "canonical-ni"), true);
  assert.equal(evidence.some((item) => item.kind === "sha256-hex-literal"), true);
  assert.equal(classifyEvidence(evidence), "mixed");
});

test("explicit external protocol mode preserves a typed exemption", () => {
  const evidence = auditText("const cid = CID.parse(value);", "adapter.mjs");
  assert.equal(
    classifyEvidence(evidence, "exempt-external-protocol"),
    "exempt-external-protocol",
  );
});


test("detects historical and ad-hoc SHA-256 address aliases even without literal digests", () => {
  const evidence = auditText(
    [
      "const a = \`urn:sha256:\${digest}\`;",
      "const b = \`blob:sha256:\${packetDigest}\`;",
      "const c = \`sha256:\${digest}\`;",
      "const c2 = \`urn:sha-256:\${digest}\`;",
      "const d = \`metroplat:artifact:1:rfc8785-jcs:sha-256:\${digest}\`;",
    ].join("\n"),
    "legacy-addresses.mjs",
  );
  const aliases = evidence.filter((item) => item.kind === "legacy-sha256-address-alias");
  assert.equal(aliases.length, 5);
  assert.equal(classifyEvidence(evidence), "legacy-only");
});

test("does not classify canonical NI as a legacy SHA-256 alias", () => {
  const evidence = auditText(
    'const id = "ni:///sha-256;koqacr8nz6PJjJUPQ9zy04JpLJiP3DSvPGDioN_dqBU";',
    "canonical.mjs",
  );
  assert.equal(evidence.some((item) => item.kind === "legacy-sha256-address-alias"), false);
  assert.equal(classifyEvidence(evidence), "canonical");
});
