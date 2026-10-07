import { existsSync, realpathSync } from "node:fs";
import { basename, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
/**
 * Node argv and direct-entrypoint process boundary reads.
 */
/** True when `moduleUrl` names the script Node was asked to execute. */
export function isDirectEntrypoint(moduleUrl, argvPath) {
    return argvPath !== undefined && realpathSync(fileURLToPath(moduleUrl)) === realpathSync(argvPath);
}
/** Read service arguments after Node's executable and script slots. */
export function processArguments(argv = process.argv) {
    return Object.freeze(argv.slice(2));
}
/** Resolve this package root from a source or built service entrypoint URL. */
export function processPackageRoot(moduleUrl) {
    let current = dirname(fileURLToPath(moduleUrl));
    while (true) {
        if (existsSync(resolve(current, "package.json")))
            return current;
        const parent = dirname(current);
        if (parent === current) {
            const serviceRoot = resolve(dirname(fileURLToPath(moduleUrl)), "../..");
            return basename(serviceRoot) === "dist" ? resolve(serviceRoot, "..") : serviceRoot;
        }
        current = parent;
    }
}
/** Read Node's script argument slot for direct-entrypoint checks. */
export function processEntrypointArgument(argv = process.argv) {
    return argv[1];
}
