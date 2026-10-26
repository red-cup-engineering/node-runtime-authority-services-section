import { existsSync, lstatSync, readFileSync } from "node:fs";
import { basename, dirname, isAbsolute, resolve } from "node:path";
import { processArguments } from "./entrypoint.mjs";
import { processEnvironment } from "./environment.mjs";
// @red-cup-engineering/computer-file-engineering-services-section (computer-file-engineering-services-section)
// is this house's real file-read primitive, but its readFileText is async
// (node:fs/promises) and every read below is a synchronous CLI-boundary
// config resolution that must complete before the caller's event loop does
// anything else -- forcing it async would cascade through every process
// entrypoint that calls processDataRootConfig. Using node:fs directly here
// until file-services carries a synchronous variant; recorded as a finding,
// not routed around silently.
const pathExists = existsSync;
function readFileUtf8(filePath) {
    return readFileSync(filePath, "utf8");
}
/** Resolve the owning services section immediately above its data/ tree.
 * `defaultRoot` must be absolute; only explicit overrides depend on cwd.
 * Config, environment and argv keep their existing precedence. Executable
 * package roots need an explicit owner binding when they are not a section.
 * Validates real existing owner ancestry and any existing data/ entry without
 * writing. Callers must receive destinations again at their effect boundary. */
export function processDataRootConfig(options) {
    if (!isAbsolute(options.defaultRoot)) {
        throw new Error(`process data root default must be absolute, got ${options.defaultRoot}`);
    }
    const args = options.args ?? processArguments();
    const env = options.env ?? processEnvironment();
    const cwd = options.cwd ?? process.cwd();
    const dataRootFlag = options.dataRootFlag ?? "--data-root";
    const configFlag = options.configFlag ?? "--config";
    rejectLegacyDataRootEnv(env, options.legacyEnvNames ?? [], options.envName);
    let dataRoot = resolve(cwd, options.defaultRoot);
    let source = "default";
    const configPath = resolveConfigPath({
        args,
        env,
        cwd,
        configFlag,
        ...(options.configEnvName === undefined ? {} : { configEnvName: options.configEnvName }),
        defaultConfigPath: resolve(dataRoot, options.configFileName),
    });
    if (configPath !== undefined) {
        const configured = readDataRootConfig(configPath);
        if (configured !== undefined) {
            dataRoot = resolve(dirname(configPath), configured);
            source = "config";
        }
    }
    const envRoot = trimmed(env[options.envName]);
    if (envRoot !== undefined) {
        dataRoot = resolve(cwd, envRoot);
        source = "env";
    }
    const argvRoot = readFlagValue(args, dataRootFlag, "process data root");
    if (argvRoot.value !== undefined) {
        dataRoot = resolve(cwd, argvRoot.value);
        source = "argv";
    }
    receiveServicesSectionDataRoot(dataRoot, source);
    return Object.freeze({
        dataRoot,
        source,
        ...(configPath === undefined ? {} : { configPath }),
    });
}
/** Remove process config flags before forwarding argv to a domain dispatcher. */
export function processArgumentsWithoutConfigFlags(args, flags = ["--data-root", "--config"]) {
    const kept = [];
    for (let index = 0; index < args.length; index += 1) {
        const value = args[index];
        const flag = flags.find((candidate) => value === candidate || value.startsWith(`${candidate}=`));
        if (flag === undefined) {
            kept.push(value);
        }
        else if (value === flag) {
            index += 1;
        }
    }
    return Object.freeze(kept);
}
function resolveConfigPath(options) {
    const argvConfig = readFlagValue(options.args, options.configFlag, "process config");
    if (argvConfig.value !== undefined)
        return resolve(options.cwd, argvConfig.value);
    const envConfig = options.configEnvName === undefined ? undefined : trimmed(options.env[options.configEnvName]);
    if (envConfig !== undefined)
        return resolve(options.cwd, envConfig);
    return pathExists(options.defaultConfigPath) ? options.defaultConfigPath : undefined;
}
function readDataRootConfig(configPath) {
    let parsed;
    try {
        parsed = JSON.parse(readFileUtf8(configPath));
    }
    catch (error) {
        throw new Error(`invalid process config ${configPath}: ${error instanceof Error ? error.message : String(error)}`);
    }
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error(`invalid process config ${configPath}: expected a JSON object`);
    }
    const dataRoot = parsed.dataRoot;
    if (dataRoot === undefined)
        return undefined;
    if (typeof dataRoot !== "string" || dataRoot.trim() === "") {
        throw new Error(`invalid process config ${configPath}: dataRoot must be a non-empty string`);
    }
    return dataRoot.trim();
}
function rejectLegacyDataRootEnv(env, legacyEnvNames, envName) {
    for (const name of legacyEnvNames) {
        if (name === envName)
            continue;
        if (trimmed(env[name]) !== undefined) {
            throw new Error(`${name} is no longer a data-root input; use ${envName}, --data-root, or the process config file`);
        }
    }
}
/** Git checkout layout and executable installation roots do not establish
 * data ownership. Inspect just this owner path and its immediate data entry. */
function receiveServicesSectionDataRoot(dataRoot, source) {
    const refusal = (reason) => new Error(`process data root from ${source} (${dataRoot}): ${reason}`);
    if (basename(dataRoot) === "data") {
        throw refusal("pass the owning services section above data/, never the data tier itself");
    }
    if (!basename(dataRoot).endsWith("-services-section") || basename(dataRoot) === "-services-section") {
        throw refusal("expected an owning *-services-section directory; select it through config, environment or argv");
    }
    const components = dataRoot.split(/[\\/]/);
    if (components.includes(".local") || components.includes("node_modules") ||
        dataRoot === "/gnu/store" || dataRoot.startsWith("/gnu/store/")) {
        throw refusal("home .local, node_modules and immutable store paths cannot own runtime data");
    }
    let current = dataRoot;
    while (true) {
        let entry;
        try {
            entry = lstatSync(current);
        }
        catch (error) {
            throw refusal(`owner ancestry must exist as real directories (${error?.code ?? "unreadable"})`);
        }
        if (entry.isSymbolicLink() || !entry.isDirectory()) {
            throw refusal("owner ancestry must be real directories without symlink backing");
        }
        const parent = dirname(current);
        if (parent === current) break;
        current = parent;
    }
    let dataEntry;
    try {
        dataEntry = lstatSync(resolve(dataRoot, "data"));
    }
    catch (error) {
        if (error?.code !== "ENOENT") throw refusal(`cannot inspect data/ (${error?.code ?? "unreadable"})`);
    }
    if (dataEntry !== undefined && (dataEntry.isSymbolicLink() || !dataEntry.isDirectory())) {
        throw refusal("existing data/ must be a real directory without symlink backing");
    }
}
function readFlagValue(args, flag, label) {
    let found = false;
    let value;
    for (let index = 0; index < args.length; index += 1) {
        const arg = args[index];
        if (arg === flag) {
            if (found)
                throw new Error(`${label}: ${flag} must be supplied once`);
            const next = trimmed(args[index + 1]);
            if (next === undefined || next.startsWith("--"))
                throw new Error(`${label}: ${flag} requires a non-empty value`);
            found = true;
            value = next;
            index += 1;
        }
        else if (arg.startsWith(`${flag}=`)) {
            if (found)
                throw new Error(`${label}: ${flag} must be supplied once`);
            const next = trimmed(arg.slice(flag.length + 1));
            if (next === undefined)
                throw new Error(`${label}: ${flag} requires a non-empty value`);
            found = true;
            value = next;
        }
    }
    return Object.freeze({ found, ...(value === undefined ? {} : { value }) });
}
function trimmed(value) {
    const text = value?.trim();
    return text === undefined || text === "" ? undefined : text;
}
