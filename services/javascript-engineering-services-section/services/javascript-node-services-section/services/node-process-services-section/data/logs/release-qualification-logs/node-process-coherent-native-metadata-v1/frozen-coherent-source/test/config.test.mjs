import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir, homedir } from "node:os";
import path from "node:path";
import test from "node:test";
import { processArgumentsWithoutConfigFlags, processDataRootConfig } from "../src/config.mjs";

function fixture(t) {
  const root = mkdtempSync(path.join(tmpdir(), "node-process-owner-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const directory = (name) => { const p = path.join(root, name); mkdirSync(p, { recursive: true }); return p; };
  return { root, directory };
}
function configFor(defaultRoot, extra = {}) {
  return processDataRootConfig({ defaultRoot, args: [], env: {}, envName: "METROPLAT_DATA_ROOT",
    configFileName: "test.config.json", cwd: defaultRoot, ...extra });
}
for (const marker of ["directory", "worktree-file", "none"]) {
  test(`an owning section can be its own checkout (${marker})`, (t) => {
    const { directory } = fixture(t); const section = directory("widget-services-section");
    if (marker === "directory") mkdirSync(path.join(section, ".git"));
    if (marker === "worktree-file") writeFileSync(path.join(section, ".git"), "gitdir: /not-an-authority\n");
    const before = readdirSync(section);
    const result = configFor(section);
    assert.deepEqual(result, { dataRoot: section, source: "default" });
    assert.equal(Object.isFrozen(result), true);
    assert.deepEqual(readdirSync(section), before);
    assert.equal(existsSync(path.join(section, "data")), false);
  });
}
test("a nested section is admitted independently of its ancestor checkout", (t) => {
  const { root, directory } = fixture(t); mkdirSync(path.join(root, ".git"));
  const section = directory("services/widget-services-section");
  assert.equal(configFor(section).dataRoot, section);
});
test("an app selects its owning section through its existing explicit input", (t) => {
  const { directory } = fixture(t); const app = directory("apps/some-app"); const section = directory("widget-services-section");
  assert.throws(() => configFor(app), /owning \*-services-section/);
  assert.deepEqual(configFor(app, { env: { METROPLAT_DATA_ROOT: section } }), { dataRoot: section, source: "env" });
});
for (const name of ["some-random-directory", "checkout", "-services-section", "data"]) {
  test(`an arbitrary selected root is refused (${name})`, (t) => {
    const { directory } = fixture(t); const root = directory(name);
    assert.throws(() => configFor(root), name === "data" ? /never the data tier/ : /owning \*-services-section/);
  });
}
test("a missing owner is refused without creating it", (t) => {
  const { root } = fixture(t); const missing = path.join(root, "missing-services-section");
  assert.throws(() => configFor(missing), /must exist as real directories/);
  assert.equal(existsSync(missing), false);
});
test("an owner that is a regular file is refused", (t) => {
  const { root } = fixture(t); const file = path.join(root, "file-services-section"); writeFileSync(file, "sentinel");
  assert.throws(() => configFor(file), /real directories/);
});
for (const name of [".local/state/widget-services-section", "node_modules/widget-services-section"]) {
  test(`an existing disguised installation or home root is refused (${name})`, (t) => {
    const { directory } = fixture(t); const section = directory(name);
    assert.throws(() => configFor(section), /cannot own runtime data/);
    assert.equal(existsSync(path.join(section, "data")), false);
  });
}
test("the real home .local selection is refused using read-only resolution", () => {
  const section = path.join(homedir(), ".local/state/561-group/not-created-services-section");
  assert.throws(() => configFor(section), /cannot own runtime data/);
});
test("an immutable installed-code root is refused before any data creation", () => {
  assert.throws(() => configFor("/gnu/store/not-created/widget-services-section"), /cannot own runtime data/);
});
for (const kind of ["owner", "ancestor", "dangling-owner"]) {
  test(`symlink backing is refused (${kind})`, (t) => {
    const { root, directory } = fixture(t); const section = directory("actual/widget-services-section"); let selected;
    if (kind === "ancestor") { symlinkSync(path.dirname(section), path.join(root, "alias")); selected = path.join(root, "alias/widget-services-section"); }
    else { selected = path.join(root, "alias-services-section"); symlinkSync(kind === "owner" ? section : path.join(root, "missing"), selected); }
    assert.throws(() => configFor(selected), /without symlink backing/);
  });
}
for (const kind of ["file", "symlink", "dangling-symlink"]) {
  test(`existing data backing is refused (${kind})`, (t) => {
    const { root, directory } = fixture(t); const section = directory("widget-services-section"); const data = path.join(section, "data");
    if (kind === "file") writeFileSync(data, "sentinel");
    else symlinkSync(kind === "symlink" ? directory("elsewhere") : path.join(root, "missing"), data);
    assert.throws(() => configFor(section), /existing data\/ must be a real directory/);
  });
}
test("an existing real data tier is admitted and cannot itself be selected", (t) => {
  const { directory } = fixture(t); const section = directory("widget-services-section");
  const data = directory("widget-services-section/data"); directory("widget-services-section/data/records");
  assert.equal(configFor(section).dataRoot, section);
  assert.throws(() => configFor(section, { args: ["--data-root", data] }), /never the data tier/);
});
test("config then environment then argv precedence and relative inputs are preserved", (t) => {
  const { root, directory } = fixture(t);
  const section = directory("default-services-section"); const configured = directory("config-services-section");
  const envRoot = directory("env-services-section"); const argRoot = directory("argv-services-section");
  const configPath = path.join(section, "test.config.json"); writeFileSync(configPath, JSON.stringify({ dataRoot: "../config-services-section" }));
  assert.deepEqual(configFor(section, { cwd: root }), { dataRoot: configured, source: "config", configPath });
  const env = { METROPLAT_DATA_ROOT: "env-services-section" };
  assert.deepEqual(configFor(section, { cwd: root, env }), { dataRoot: envRoot, source: "env", configPath });
  assert.deepEqual(configFor(section, { cwd: root, env, args: ["--data-root=argv-services-section"] }), { dataRoot: argRoot, source: "argv", configPath });
});
test("absolute default is independent of invoking cwd", (t) => {
  const { directory } = fixture(t); const section = directory("widget-services-section");
  assert.equal(configFor(section, { cwd: directory("elsewhere") }).dataRoot, section);
});
test("custom config selectors and root flags retain their precedence", (t) => {
  const { root, directory } = fixture(t); const section = directory("widget-services-section");
  const selected = directory("selected-services-section"); const config = path.join(root, "selected.json");
  writeFileSync(config, JSON.stringify({ dataRoot: "selected-services-section" }));
  const common = { cwd: root, configEnvName: "OWNER_CONFIG", configFlag: "--owner-config", dataRootFlag: "--owner-root" };
  assert.equal(configFor(section, { ...common, env: { OWNER_CONFIG: config } }).dataRoot, selected);
  assert.equal(configFor(section, { ...common, env: { OWNER_CONFIG: "/not/read.json" }, args: ["--owner-config", config, "--owner-root", section] }).dataRoot, section);
});
for (const args of [["--data-root"], ["--data-root="], ["--data-root", "--domain=x"], ["--data-root=x", "--data-root=y"], ["--config"], ["--config="], ["--config=x", "--config=y"]]) {
  test(`empty or repeated process flags are refused (${JSON.stringify(args)})`, (t) => {
    const { directory } = fixture(t); assert.throws(() => configFor(directory("widget-services-section"), { args }), /requires a non-empty value|must be supplied once/);
  });
}
for (const contents of ["{invalid", "[]", "null", '{"dataRoot":1}', '{"dataRoot":" "}']) {
  test(`invalid process configuration is refused (${contents})`, (t) => {
    const { directory } = fixture(t); const section = directory("widget-services-section");
    writeFileSync(path.join(section, "test.config.json"), contents); assert.throws(() => configFor(section), /invalid process config/);
  });
}
test("an empty config object leaves the default selected", (t) => {
  const { directory } = fixture(t); const section = directory("widget-services-section");
  writeFileSync(path.join(section, "test.config.json"), "{}"); assert.equal(configFor(section).source, "default");
});
test("a configured legacy environment input is still refused", (t) => {
  const { directory } = fixture(t); const section = directory("widget-services-section");
  assert.throws(() => configFor(section, { legacyEnvNames: ["OLD_ROOT"], env: { OLD_ROOT: section } }), /no longer a data-root input/);
});
test("relative defaults remain invalid", () => {
  assert.throws(() => configFor("relative/data-root"), /must be absolute/);
});
test("process config arguments are removed before the domain dispatcher", () => {
  const result = processArgumentsWithoutConfigFlags(["run", "--config", "a.json", "--data-root=b", "--domain", "value"]);
  assert.deepEqual(result, ["run", "--domain", "value"]); assert.equal(Object.isFrozen(result), true);
});
