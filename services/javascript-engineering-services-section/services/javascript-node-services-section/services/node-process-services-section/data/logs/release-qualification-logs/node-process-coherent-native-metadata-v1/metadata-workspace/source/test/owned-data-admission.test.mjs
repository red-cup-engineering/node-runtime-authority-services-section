import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, lstatSync, mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { processDataRootConfig, receiveServicesSectionDataRoot, receiveOwnerDataRoot, receiveOwnedDataDestination } from "../src/config.mjs";

// Source fixtures only, under this received source's typed logs. Never /tmp or home state.
const fixtureParent = fileURLToPath(new URL("../data/logs/shared-data-admission-test-logs/", import.meta.url));
function fixture(t) {
    mkdirSync(fixtureParent, { recursive: true, mode: 0o700 });
    const directory = mkdtempSync(join(fixtureParent, "owned-"));
    const identity = lstatSync(directory);
    t.after(() => {
        const current = lstatSync(directory);
        assert(current.isDirectory() && !current.isSymbolicLink());
        assert.equal(current.dev, identity.dev); assert.equal(current.ino, identity.ino);
        rmSync(directory, { recursive: true });
    });
    const section = join(directory, "fixture-services-section");
    mkdirSync(section, { mode: 0o700 });
    return { directory, section, data: join(section, "data") };
}

test("explicit section admission receives an existing section independently of Git topology and allows missing data", (t) => {
    const { section, data } = fixture(t);
    assert.equal(receiveServicesSectionDataRoot(section), section);
    assert.equal(existsSync(data), false);
    mkdirSync(data); mkdirSync(join(section, ".git"));
    assert.equal(receiveServicesSectionDataRoot(section), section);
});

test("explicit section admission refuses missing, relative, empty, noncanonical and control-character inputs", (t) => {
    const { section } = fixture(t);
    for (const value of [undefined, null, 0, "", " ", "relative-services-section", section + "/", section + "/../" + basename(section), section + "\r", section + "\n", section + "\0"]) {
        assert.throws(() => receiveServicesSectionDataRoot(value));
    }
    assert.throws(() => receiveServicesSectionDataRoot(join(section, "missing-services-section")));
});

test("explicit section admission refuses home-state and installed roots without selecting an ambient fallback", (t) => {
    const { directory } = fixture(t);
    for (const name of [".local", "node_modules"]) {
        const section = join(directory, name, "nested-services-section");
        mkdirSync(section, { recursive: true });
        assert.throws(() => receiveServicesSectionDataRoot(section));
    }
    assert.throws(() => receiveServicesSectionDataRoot("/gnu/store/unreceived-services-section"));
    assert.throws(() => receiveServicesSectionDataRoot(join(directory, "-services-section")));
});

test("explicit section admission refuses a redirected owner or owner ancestor", (t) => {
    const { directory, section } = fixture(t);
    const linked = join(directory, "linked-services-section"); symlinkSync(section, linked);
    assert.throws(() => receiveServicesSectionDataRoot(linked));
    const ancestor = join(directory, "linked-parent"); symlinkSync(directory, ancestor);
    assert.throws(() => receiveServicesSectionDataRoot(join(ancestor, "fixture-services-section")));
});

test("explicit section admission refuses existing file, symlink and dangling-symlink data entries", (t) => {
    const { directory } = fixture(t);
    for (const mode of ["file", "link", "dangling"]) {
        const section = join(directory, mode + "-services-section"); mkdirSync(section);
        const data = join(section, "data");
        if (mode === "file") writeFileSync(data, "preserved");
        else symlinkSync(mode === "link" ? directory : join(directory, "absent"), data);
        assert.throws(() => receiveServicesSectionDataRoot(section));
    }
});

test("data-directory admission preserves the existing CDE section/data distinction and requires existing data", (t) => {
    const { section, data } = fixture(t);
    assert.throws(() => receiveOwnerDataRoot(section), TypeError);
    assert.throws(() => receiveOwnerDataRoot(data));
    mkdirSync(data);
    assert.equal(receiveOwnerDataRoot(data), data);
    assert.throws(() => receiveServicesSectionDataRoot(data));
});

test("owned destination admission allows missing directory and file descendants without creating them", (t) => {
    const { data } = fixture(t); mkdirSync(data);
    const directory = join(data, "logs", "example-logs", "missing");
    const file = join(data, "records", "example-records", "missing.json");
    assert.equal(receiveOwnedDataDestination(data, directory), directory);
    assert.equal(receiveOwnedDataDestination(data, file, { kind: "file" }), file);
    assert.equal(existsSync(join(data, "logs")), false);
    assert.equal(existsSync(join(data, "records")), false);
});

test("owned destination admission refuses self, parent, sibling-prefix and noncanonical paths", (t) => {
    const { data } = fixture(t); mkdirSync(data);
    for (const destination of [data, dirname(data), data + "-other/item", data + "/../escaped", data + "/state/../item", "relative", ""]) {
        assert.throws(() => receiveOwnedDataDestination(data, destination));
    }
    assert.throws(() => receiveOwnedDataDestination(data, join(data, "x"), { kind: "socket" }), TypeError);
});

test("owned destination admission receives only the requested existing target kind", (t) => {
    const { data } = fixture(t); mkdirSync(data);
    const directory = join(data, "logs"); mkdirSync(directory);
    const file = join(data, "record.json"); writeFileSync(file, "retained");
    assert.equal(receiveOwnedDataDestination(data, directory), directory);
    assert.equal(receiveOwnedDataDestination(data, file, { kind: "file" }), file);
    assert.throws(() => receiveOwnedDataDestination(data, file));
    assert.throws(() => receiveOwnedDataDestination(data, directory, { kind: "file" }));
    assert.throws(() => receiveOwnedDataDestination(data, join(file, "child")));
});

test("owned destination admission refuses redirected targets and ancestors even when a leaf is missing", (t) => {
    const { directory, data } = fixture(t); mkdirSync(data);
    const other = join(directory, "retained"); mkdirSync(other);
    const link = join(data, "redirect"); symlinkSync(other, link);
    assert.throws(() => receiveOwnedDataDestination(data, link));
    assert.throws(() => receiveOwnedDataDestination(data, join(link, "missing", "leaf"), { kind: "file" }));
    const dangling = join(data, "dangling"); symlinkSync(join(directory, "absent"), dangling);
    assert.throws(() => receiveOwnedDataDestination(data, dangling));
    assert.equal(lstatSync(other).isDirectory(), true);
});

test("explicit admission never parses an implicit config while the original resolver still does", (t) => {
    const { section } = fixture(t);
    writeFileSync(join(section, "config.json"), "{ invalid retained config");
    assert.equal(receiveServicesSectionDataRoot(section), section);
    assert.throws(() => processDataRootConfig({ defaultRoot: section, args: [], env: {}, configFileName: "config.json", envName: "EXPLICIT_OWNER" }));
});


test("data-directory admission preserves original missing-owner, missing-data and parent-file filesystem errors", (t) => {
    const { directory, data } = fixture(t);
    const missingOwnerData = join(directory, "missing-services-section", "data");
    assert.throws(() => receiveOwnerDataRoot(missingOwnerData), { code: "ENOENT" });
    assert.throws(() => receiveOwnerDataRoot(data), { code: "ENOENT" });
    const parentFile = join(directory, "file-services-section"); writeFileSync(parentFile, "retained parent");
    assert.throws(() => receiveOwnerDataRoot(join(parentFile, "data")), { code: "ENOTDIR" });
});


test("data-directory admission keeps malformed owner paths as TypeError before missing-path metadata", (t) => {
    const { directory } = fixture(t);
    for (const path of [join(directory, "not-an-owner", "data"),
        join(directory, ".local", "missing-services-section", "data"),
        join(directory, "node_modules", "missing-services-section", "data"),
        "/gnu/store/missing-services-section/data"]) {
        assert.throws(() => receiveOwnerDataRoot(path), (error) => error instanceof TypeError && error.code === undefined);
    }
});
