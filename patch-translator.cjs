const fs = require("fs");
const F = "src/translate-markdown-jsnode-operation-package-specification.mjs";
let s = fs.readFileSync(F, "utf8");
const must = (cond, what) => { if (!cond) throw new Error("patch failed: " + what); };
const rep = (from, to, all = false) => { must(s.includes(from), from.slice(0, 70)); s = all ? s.split(from).join(to) : s.replace(from, () => to); };

rep(`import { sha256Digest, sha256Hex } from "@red-cup-engineering/cryptographic-computer-data-engineering-services-section/integrity";`,
`import { sha256Digest, sha256Hex } from "@red-cup-engineering/cryptographic-computer-data-engineering-services-section/integrity";
import { DEFINITIONALLY_EXACT_PARAMETERS } from "@red-cup-engineering/computer-data-engineering-services-section/artifact-fabrication";`);

// clauseLines: optional trailing [claims: a, b]
rep(`function clauseLines(lines, start, end, type, options = {}) {`, `function clauseLines(lines, start, end, type, claimed = false) {`);
rep(`    clauses.push({ id, statement, sourceSpan: span(index + 1), ...options });`,
`    const suffix = claimed ? /^(.*?) \\[claims: ([a-z0-9, -]+)\\]$/u.exec(statement) : null;
    clauses.push({ id, statement: suffix ? suffix[1] : statement, claimIds: suffix ? suffix[2].split(", ") : [], sourceSpan: span(index + 1) });`);

// constraints: version 2 when claimed
rep(`function constraints(lines, start, end, kind) {`, `function constraints(lines, start, end, kind, claimed = false) {`);
rep(`values.push({ type: "ArtifactFabricationConstraint", version: 1, id: slug(match[1]`, `values.push({ type: "ArtifactFabricationConstraint", version: claimed ? 2 : 1, id: slug(match[1]`);
rep("statement: nonempty(match[6], `${kind} statement`, index + 1), sourceSpan: span(index + 1) });", "statement: nonempty(match[6], `${kind} statement`, index + 1), ...(claimed ? { parameters: [], claimIds: [] } : {}), sourceSpan: span(index + 1) });");

// questions
rep(`function questions(lines, start, end) {`, `function questions(lines, start, end, claimed = false) {`);
rep("const match = /^- `([a-z][a-z0-9]*(?:-[a-z0-9]+)*)` \\[(blocking|nonblocking)\\]: (.+)$/u.exec(line);", "const match = /^- `([a-z][a-z0-9]*(?:-[a-z0-9]+)*)` \\[(blocking|nonblocking)\\]: (.+)$/u.exec(line);\n    const about = claimed ? /^(.*?) \\[claim: ([a-z][a-z0-9]*(?:-[a-z0-9]+)*)\\]$/u.exec(match?.[3] ?? \"\") : null;");
rep(`values.push({ type: "ArtifactFabricationOpenQuestion", version: 1, id: slug(match[1], "open-question ID", index + 1), question: nonempty(match[3], "open question", index + 1), blocking: match[2] === "blocking", sourceSpan: span(index + 1) });`,
`values.push({ type: "ArtifactFabricationOpenQuestion", version: claimed ? 2 : 1, id: slug(match[1], "open-question ID", index + 1), question: nonempty(about ? about[1] : match[3], "open question", index + 1), blocking: match[2] === "blocking", ...(claimed ? { claimId: about ? about[2] : null } : {}), sourceSpan: span(index + 1) });`);

const helpers = `
// The epistemic layer (candidate version 2). A work order with a \`## Claims\` section states, for every
// claim its clauses rest on, its status and basis; its numbers are \`{{claim-id}}\` placeholders (or
// \`{{exact-constant}}\` names from Data's definitionally exact set), and each dependency it names is a
// measured dependency claim. The Data admission refuses what the law refuses; this layer only parses.
//   - \`id\` | measured | kind | statement | quantity | locator | digest | derivation
//   - \`id\` | derived | kind | statement | quantity | kind:ref; kind:ref | derivation
//   - \`id\` | conjectured | kind | statement | quantity | hypothesis | observable | instrument | decision rule | estimate derivation
// quantity is \`none\` or \`<number> <unit>\`; a clause ends with \`[claims: id, id]\`; a question with \`[claim: id]\`.
function withClaims(claimed, headings) {
  return claimed ? headings.flatMap((heading) => heading === "## Open questions" ? [heading, "## Claims"] : [heading]) : headings;
}

function claimQuantity(token, line) {
  if (token === "none") return null;
  const match = /^(-?[0-9]+(?:\\.[0-9]+)?(?:e-?[0-9]+)?) (\\S.*)$/u.exec(token);
  if (!match) refuse("INVALID_CLAIM", "a claim quantity is \`none\` or \`<number> <unit>\`", span(line));
  return { type: "ArtifactFabricationQuantity", value: Number(match[1]), unit: match[2] };
}

function claimsFrom(lines, [start, end]) {
  const claims = [];
  for (let index = start; index < end; index += 1) {
    const line = lines[index];
    if (line.length === 0) continue;
    const match = /^- \`([a-z][a-z0-9]*(?:-[a-z0-9]+)*)\` \\| (measured|derived|conjectured) \\| ([a-z]+) \\| (.+)$/u.exec(line);
    if (!match) refuse("INVALID_CLAIM", "claims must use - \`stable-id\` | measured|derived|conjectured | kind | statement | quantity | basis...", span(index + 1));
    const [, id, status, kind, rest] = match;
    const parts = rest.split(" | ");
    const arity = { measured: 5, derived: 4, conjectured: 7 }[status];
    if (parts.length !== arity) refuse("INVALID_CLAIM", \`a \${status} claim carries statement and quantity then \${arity - 2} basis fields, separated by ' | '\`, span(index + 1));
    const [statement, quantity, ...basis] = parts;
    const base = { type: "ArtifactFabricationClaim", version: 1, id: slug(id, "claim ID", index + 1), kind, statement: nonempty(statement, "claim statement", index + 1), status, quantity: claimQuantity(quantity, index + 1), sourceSpan: span(index + 1) };
    if (status === "measured") claims.push({ ...base, basis: { type: "ArtifactFabricationMeasuredBasis", locator: basis[0], digest: basis[1], derivation: basis[2] } });
    else if (status === "derived") {
      const premises = basis[0].split("; ").map((item) => { const at = item.indexOf(":"); return { type: "ArtifactFabricationPremise", kind: item.slice(0, at), ref: item.slice(at + 1) }; });
      claims.push({ ...base, basis: { type: "ArtifactFabricationDerivedBasis", premises, derivation: basis[1] } });
    } else claims.push({ ...base, basis: { type: "ArtifactFabricationConjecturedBasis", hypothesis: basis[0], measurementPlan: { type: "ArtifactFabricationMeasurementPlan", observable: basis[1], instrument: basis[2], decisionRule: basis[3] }, estimateDerivation: basis[4] } });
  }
  return claims;
}

function clausesOf(type, clauses, claims) {
  if (claims === null) return clauses.map(({ id, statement, sourceSpan }) => ({ type, version: 1, id, statement, sourceSpan }));
  return clauses.map(({ id, statement, claimIds, sourceSpan }) => {
    const placed = [...new Set([...statement.matchAll(/\\{\\{([^{}]*)\\}\\}/gu)].map((item) => item[1]))];
    const parameters = placed.map((name) => {
      const claim = claims.find((item) => item.id === name);
      if (claim?.quantity) return { type: "ArtifactFabricationParameter", version: 1, name, value: claim.quantity.value, unit: claim.quantity.unit, claimId: name, exact: null };
      const exact = DEFINITIONALLY_EXACT_PARAMETERS[name];
      if (!claim && exact) return { type: "ArtifactFabricationParameter", version: 1, name, value: exact.value, unit: exact.unit, claimId: null, exact: name };
      refuse("UNKNOWN_PARAMETER_PLACEHOLDER", \`{{\${name}}} names no claim with a quantity and no definitionally exact constant\`, sourceSpan);
    });
    return { type, version: 2, id, statement, parameters, claimIds: [...new Set([...claimIds, ...parameters.map((item) => item.claimId).filter((item) => item !== null)])].sort(), sourceSpan };
  });
}

function conjecturedIds(claims) {
  return claims.filter(({ status }) => status === "conjectured").map(({ id }) => id).sort();
}

// A dependency named by a claimed work order is backed by an observed artifact: a measured dependency
// claim whose statement names it as name@version (the registry response is the claim's evidence).
function measuredDependencies(claims, dependencies, line) {
  const entries = Array.isArray(dependencies) ? dependencies.map((item) => [item?.name, item?.version]) : Object.entries(dependencies ?? {});
  for (const [name, version] of entries) {
    if (!claims.some((claim) => claim.kind === "dependency" && claim.status === "measured" && claim.statement.includes(\`\${name}@\${version}\`))) {
      refuse("DEPENDENCY_WITHOUT_MEASURED_CLAIM", \`dependency \${name}@\${version} needs a measured dependency claim naming it\`, span(line));
    }
  }
}

function translateV2(source, lines) {`;
rep(`function translateV2(source, lines) {`, helpers);

// headings
rep(`  const headings = modules ? [`, `  const claimed = lines.includes("## Claims");\n  const headings = withClaims(claimed, modules ? [`);
s = s.replace(/("## Sources", "## Operations", "## Tests", "## Examples", "## Traceability"\];)(\n  const atxHeadings)/, (m, a, b) => a.replace("];", "]);") + b);
must(/"## Traceability"\]\);\n  const atxHeadings/.test(s), "heading close");
// legacy headings
rep(`    const headings = ["# ", "## Requirements", "## Prohibitions", "## Laws", "## Standards", "## Open questions", "## Package", "## Operation", "## Tests", "## Examples", "## Traceability"];`,
`    const claimed = lines.includes("## Claims");\n    const headings = withClaims(claimed, ["# ", "## Requirements", "## Prohibitions", "## Laws", "## Standards", "## Open questions", "## Package", "## Operation", "## Tests", "## Examples", "## Traceability"]);`);

// clause blocks (both indentations)
s = s.replace(/(\s*)const requirementClauses = clauseLines\(lines, \.\.\.sections\["## Requirements"\], "requirements"\);\s*const prohibitionClauses = clauseLines\(lines, \.\.\.sections\["## Prohibitions"\], "prohibitions"\);\s*const requirements = requirementClauses\.map[^\n]*\n\s*const prohibitions = prohibitionClauses\.map[^\n]*\n\s*const constraintsValue = [^\n]*\n\s*const openQuestions = questions\(lines, \.\.\.sections\["## Open questions"\]\);/g,
(m, ws) => { const i = ws.replace(/\n/g, "") ; const p = "\n" + i;
 return `${p}const claimList = claimed ? claimsFrom(lines, sections["## Claims"]) : null;${p}const requirementClauses = clauseLines(lines, ...sections["## Requirements"], "requirements", claimed);${p}const prohibitionClauses = clauseLines(lines, ...sections["## Prohibitions"], "prohibitions", claimed);${p}const requirements = clausesOf("ArtifactFabricationRequirement", requirementClauses, claimList);${p}const prohibitions = clausesOf("ArtifactFabricationProhibition", prohibitionClauses, claimList);${p}const constraintsValue = [...constraints(lines, ...sections["## Laws"], "law", claimed), ...constraints(lines, ...sections["## Standards"], "standard", claimed)];${p}const openQuestions = questions(lines, ...sections["## Open questions"], claimed);`; });
must((s.match(/const claimList = claimed/g) || []).length === 2, "clause blocks x2");

// candidates
s = s.split(`type: "ArtifactFabricationSpecificationCandidate", version: 1,`).join(`type: "ArtifactFabricationSpecificationCandidate", version: claimed ? 2 : 1,`);
s = s.split(`requirements, prohibitions, openQuestions, constraints: constraintsValue`).join(`...(claimed ? { claims: claimList } : {}), requirements, prohibitions, openQuestions, constraints: constraintsValue`);
must((s.match(/claims: claimList/g) || []).length === 3, "candidate x3");
rep(`const obligation = { type: "ArtifactFabricationAcceptanceObligation", version: 1,`, `const obligation = { type: "ArtifactFabricationAcceptanceObligation", version: claimed ? 2 : 1, ...(claimed ? { parameters: [], claimIds: conjecturedIds(claimList) } : {}),`, true);
// modules obligations
rep(`exactKeys(value, ["id", "kind", "statement"], "acceptance obligation", acceptance.sourceSpan.startLine);`, `exactKeys(value, claimed ? ["id", "kind", "statement", "claimIds"] : ["id", "kind", "statement"], "acceptance obligation", acceptance.sourceSpan.startLine);`);
rep(`return { type: "ArtifactFabricationAcceptanceObligation", version: 1, id: slug(value.id`, `return { type: "ArtifactFabricationAcceptanceObligation", version: claimed ? 2 : 1, ...(claimed ? { parameters: [], claimIds: value.claimIds } : {}), id: slug(value.id`);
// dependencies
rep(`exactKeys(moduleRecord.value, ["operations", "examples", "dependencies"], "Modules", moduleRecord.sourceSpan.startLine);`, `exactKeys(moduleRecord.value, ["operations", "examples", "dependencies"], "Modules", moduleRecord.sourceSpan.startLine);\n    if (claimed) measuredDependencies(claimList, moduleRecord.value.dependencies, moduleRecord.sourceSpan.startLine);`);
rep(`if (metadata.version !== 2 || typeof metadata.topic !== "string") refuse("INVALID_PACKAGE_SECTION", "Package must carry version 2 and topic", span(packageFence.startLine, packageFence.endLine));`, `if (metadata.version !== 2 || typeof metadata.topic !== "string") refuse("INVALID_PACKAGE_SECTION", "Package must carry version 2 and topic", span(packageFence.startLine, packageFence.endLine));\n  if (claimed) { measuredDependencies(claimList, metadata.dependencies, packageFence.startLine); measuredDependencies(claimList, metadata.devDependencies, packageFence.startLine); }`);
rep(`exactKeys(metadata, ["packageName", "packageVersion", "license", "dependencies", "devDependencies"], "Package", packageFence.startLine);`, `exactKeys(metadata, ["packageName", "packageVersion", "license", "dependencies", "devDependencies"], "Package", packageFence.startLine);\n    if (claimed) { measuredDependencies(claimList, metadata.dependencies, packageFence.startLine); measuredDependencies(claimList, metadata.devDependencies, packageFence.startLine); }`);
fs.writeFileSync(F, s);
console.log("patched");
