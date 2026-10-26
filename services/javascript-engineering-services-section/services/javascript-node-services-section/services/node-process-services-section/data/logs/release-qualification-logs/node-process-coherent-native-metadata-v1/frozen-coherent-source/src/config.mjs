import { existsSync, lstatSync, readFileSync, realpathSync } from "node:fs";
import { basename, dirname, isAbsolute, relative, resolve, sep } from "node:path";
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
    receiveResolvedServicesSectionDataRoot(dataRoot, source);
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
/** Receive an exact explicit section owner, independently of process input resolution.
 * Metadata only: callers own filing/authority and receive again before effects. */
export function receiveServicesSectionDataRoot(sectionRoot) {
    if (!explicitAbsolutePath(sectionRoot)) {
        throw new TypeError("sectionRoot must be an explicit nonempty absolute canonical path");
    }
    receiveResolvedServicesSectionDataRoot(sectionRoot, "explicit");
    return sectionRoot;
}

/** CDE's existing data-directory convention, using the shared section law. */
export function receiveOwnerDataRoot(root) {
    if (!explicitAbsolutePath(root) || basename(root) !== "data") {
        throw new TypeError("ownerDataRoot must name the actual owning services-section/data");
    }
    const section = dirname(root);
    const refusal = (reason) => new TypeError(`ownerDataRoot (${root}): ${reason}`);
    receiveSectionPathShape(section, refusal);
    // Valid-shaped missing roots retain CDE's original native filesystem errno.
    const info = lstatSync(root);
    if (!info.isDirectory() || realpathSync(root) !== root) {
        throw new TypeError("ownerDataRoot must be an existing unredirected directory");
    }
    receiveSectionPathMetadata(section, refusal);
    return root;
}

/** Metadata confinement only; missing descendants do not authorize creation. */
export function receiveOwnedDataDestination(ownerDataRoot, destination, { kind = "directory", label = "data destination" } = {}) {
    const root = receiveOwnerDataRoot(ownerDataRoot);
    if (kind !== "directory" && kind !== "file") {
        throw new TypeError("owned destination kind must be directory or file");
    }
    const suffix = explicitAbsolutePath(destination) ? relative(root, destination) : undefined;
    if (suffix === undefined || suffix === "" || suffix === ".." || suffix.startsWith(".." + sep) || isAbsolute(suffix)) {
        throw new TypeError(`${label} must be strictly inside ownerDataRoot`);
    }
    let at = destination, target = true;
    while (true) {
        let info;
        try { info = lstatSync(at); }
        catch (error) { if (error.code !== "ENOENT") throw error; }
        if (info) {
            if (!(target && kind === "file" ? info.isFile() : info.isDirectory()) || realpathSync(at) !== at) {
                throw new TypeError(`${label} or existing parent is redirected or has the wrong kind`);
            }
            break;
        }
        at = dirname(at); target = false;
    }
    return destination;
}

function explicitAbsolutePath(value) {
    return typeof value === "string" && value.trim().length > 0 && !/[\r\n\0]/u.test(value)
        && isAbsolute(value) && resolve(value) === value;
}

function receiveResolvedServicesSectionDataRoot(dataRoot, source) {
    const refusal = (reason) => new Error(`process data root from ${source} (${dataRoot}): ${reason}`);
    receiveSectionPathShape(dataRoot, refusal);
    receiveSectionPathMetadata(dataRoot, refusal);
}

// One semantic rule: the resolver and explicit adapters differ only at their boundaries.
function receiveSectionPathShape(dataRoot, refusal) {
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
}

function receiveSectionPathMetadata(dataRoot, refusal) {
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
