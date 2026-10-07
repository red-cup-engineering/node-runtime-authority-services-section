import { texPlateContract, } from "./schema.mjs";
import { DEPENDENCY_COMMANDS, REFERENCE_COMMANDS, stripTexComment, } from "./syntax.mjs";
/** Admit generic TeX-family source text as a file plate, not as a runtime run. */
export function decodeTexPlate(text, options = {}) {
    const source = options.source ?? "tex-source";
    const format = options.format ?? "generic-tex";
    const lines = text.split(/\r?\n/u);
    const commands = [];
    const environments = [];
    const dependencies = [];
    const labels = [];
    const references = [];
    for (let offset = 0; offset < lines.length; offset += 1) {
        const line = stripTexComment(lines[offset] ?? "");
        const lineNumber = offset + 1;
        for (const command of texCommands(line, lineNumber)) {
            commands.push(command);
            if (command.name === "begin" && command.argument !== undefined) {
                environments.push(texEnvironment(line, command.argument, lineNumber));
            }
            if (command.name === "label" && command.argument !== undefined && command.argument !== "") {
                labels.push(Object.freeze({ name: command.argument, line: lineNumber }));
            }
            const dependencyKind = DEPENDENCY_COMMANDS[command.name];
            if (dependencyKind !== undefined && command.argument !== undefined && command.argument !== "") {
                dependencies.push(Object.freeze({
                    kind: dependencyKind,
                    target: command.argument,
                    command: command.name,
                    line: lineNumber,
                }));
            }
            if (REFERENCE_COMMANDS.has(command.name) && command.argument !== undefined && command.argument !== "") {
                references.push(Object.freeze({
                    target: command.argument,
                    command: command.name,
                    line: lineNumber,
                }));
            }
        }
    }
    return texPlateContract.assert({
        kind: "metroplat.tex.plate",
        source,
        format,
        commands: Object.freeze(commands),
        environments: Object.freeze(environments),
        dependencies: Object.freeze(dependencies),
        labels: Object.freeze(labels),
        references: Object.freeze(references),
        mediaType: "application/vnd.metroplat.tex.plate+json",
    }, "TeX plate");
}
function texCommands(line, lineNumber) {
    const commands = [];
    const commandPattern = /\\([A-Za-z@]+)\s*(?:\{([^{}]*)\})?/gu;
    for (const match of line.matchAll(commandPattern)) {
        const name = match[1] ?? "";
        if (name === "")
            continue;
        const argument = match[2];
        commands.push(Object.freeze({
            name,
            ...(argument === undefined ? {} : { argument }),
            line: lineNumber,
        }));
    }
    return Object.freeze(commands);
}
function texEnvironment(line, name, lineNumber) {
    const title = line.match(/\\begin\{[^{}]+\}\[([^\]]+)\]/u)?.[1];
    return Object.freeze({
        name,
        ...(title === undefined ? {} : { title }),
        line: lineNumber,
    });
}
