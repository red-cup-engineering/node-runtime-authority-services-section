export const DEPENDENCY_COMMANDS = Object.freeze({
    input: "input",
    include: "include",
    includeonly: "include",
    import: "import",
    subfile: "input",
    usepackage: "package",
    addbibresource: "bibliography",
    bibliography: "bibliography",
    uses: "uses",
});
export const REFERENCE_COMMANDS = new Set(["ref", "eqref", "autoref", "cref", "Cref", "pageref", "uses"]);
export function stripTexComment(line) {
    for (let index = 0; index < line.length; index += 1) {
        if (line[index] === "%" && line[index - 1] !== "\\")
            return line.slice(0, index);
    }
    return line;
}
export function matchAll(text, pattern) {
    return [...text.matchAll(pattern)].map((match) => match[1] ?? "").filter((value) => value !== "");
}
export function countMatches(text, pattern) {
    return [...text.matchAll(pattern)].length;
}
export function uniqueSorted(values) {
    return Object.freeze([...new Set(values)].sort((left, right) => left.localeCompare(right)));
}
export function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&");
}
