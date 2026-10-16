import {
  SEN_FORMS,
  tm,
  validateSenTerm,
} from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation";
import { inferTy, isClosed } from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation/typing";
import {
  arrayTag,
  objectTag,
  stringTag,
} from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation/json-codec";
import { parse as parseJson } from "@red-cup-engineering/json-services-section";
import { EMPTY_WITNESS_ROOT } from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation/semantic-content-identity";
import { identifyNormalizedSemanticContent } from "./runtime.mjs";

const text = (value) => JSON.stringify(value);
const namedList = (items) => items.reduceRight((tail, item) => ["pair", item, tail], ["star"]);

export function namedString(value) {
  return ["pair", ["mark", text(stringTag)], ["mark", text(value)]];
}

export function namedArray(items) {
  return ["pair", ["mark", text(arrayTag)], namedList(items)];
}

export function namedObject(entries) {
  const sorted = [...entries].sort(([left], [right]) => left.localeCompare(right));
  return ["pair", ["mark", text(objectTag)], namedList(sorted.map(([key, value]) => ["pair", ["mark", text(key)], value]))];
}

export function namedBool(value) {
  return ["mark", value ? "held" : "denied"];
}

export function namedGenerator(name) {
  if (!["specialization", "converse", "subjectProjection", "objectProjection"].includes(name)) {
    throw new TypeError(`namedGenerator: unknown generator ${JSON.stringify(name)}`);
  }
  return ["mark", name];
}

function resolve(scope, name) {
  for (let index = scope.length - 1; index >= 0; index -= 1) {
    if (scope[index] === name) return scope.length - 1 - index;
  }
  throw new TypeError(`compileNamedSen: unbound variable ${JSON.stringify(name)}`);
}

function namedTermSlot(form, slot) {
  return slot + (form.binders?.filter((binder) => binder <= slot).length ?? 0);
}

function sourceSlot(form, slot) {
  return slot + (form.binders?.filter((binder) => binder < slot).length ?? 0);
}

function compile(surface, scope) {
  if (!Array.isArray(surface) || typeof surface[0] !== "string") {
    throw new TypeError("compileNamedSen: a named SEN term must be a tagged array");
  }
  if (surface[0] === "embed") {
    // An embed is its own closed term, even under a surrounding named binder;
    // checking this boundary prevents ambient binders from capturing it.
    if (surface.length !== 2 || !isClosed(surface[1])) throw new TypeError("compileNamedSen: embed requires one closed SEN term");
    return surface[1];
  }
  if (surface[0] === "var") {
    if (surface.length !== 2 || typeof surface[1] !== "string") throw new TypeError("compileNamedSen: var requires one name");
    return tm.var(resolve(scope, surface[1]));
  }
  const form = SEN_FORMS[surface[0]];
  if (form === undefined) throw new TypeError(`compileNamedSen: unknown SEN form ${JSON.stringify(surface[0])}`);
  const out = [surface[0]];
  for (const slot of Object.keys(form.atoms ?? {}).map(Number))
    out[slot] = surface[sourceSlot(form, slot)];
  for (const slot of form.types ?? [])
    out[slot] = surface[sourceSlot(form, slot)];
  for (const slot of form.terms ?? []) {
    const namedSlot = namedTermSlot(form, slot);
    const childScope = form.binders?.includes(slot)
      ? [...scope, binderName(surface, namedSlot - 1)]
      : scope;
    out[slot] = compile(surface[namedSlot], childScope);
  }
  for (const slot of form.termLists ?? []) {
    if (!Array.isArray(surface[slot])) throw new TypeError(`compileNamedSen: ${surface[0]} requires a term list`);
    out[slot] = surface[slot].map((child) => compile(child, scope));
  }
  return out;
}

function binderName(surface, slot) {
  const name = surface[slot];
  if (typeof name !== "string") throw new TypeError("compileNamedSen: binder names must be text");
  return name;
}

export function compileNamedSen(surface) {
  const term = compile(surface, []);
  // Validate the completed tree once. Validating every recursive return above
  // re-walked each descendant subtree; absolute-continuity terms are composed
  // from large embedded terms, making that quadratic in the output size.
  validateSenTerm(term);
  return term;
}

export function parseNamedSen(source) {
  const term = compileNamedSen(parseJson(source));
  if (!isClosed(term) || inferTy([], term) === null) throw new TypeError("parseNamedSen: compiled term is not closed and well typed");
  return term;
}

function namedOf(term, scope) {
  const compiled = validateSenTerm(term);
  if (compiled[0] === "var") {
    const name = scope[scope.length - 1 - compiled[1]];
    if (name === undefined) throw new TypeError(`canonicalNamedSen: free positional variable ${compiled[1]}`);
    return ["var", name];
  }
  const form = SEN_FORMS[compiled[0]];
  const out = [...compiled];
  // Insert independently scoped binder names right-to-left, so each insertion
  // leaves the original positions of earlier branch children intact.
  for (const slot of [...(form.terms ?? [])].reverse()) {
    if (form.binders?.includes(slot)) {
      const name = `$${scope.length}`;
      out.splice(slot, 0, name);
      out[slot + 1] = namedOf(compiled[slot], [...scope, name]);
    } else {
      out[slot] = namedOf(compiled[slot], scope);
    }
  }
  for (const slot of form.termLists ?? []) out[slot] = compiled[slot].map((child) => namedOf(child, scope));
  return out;
}

export function canonicalNamedSen(term) {
  return text(namedOf(term, []));
}

export function digestNamedSen(term) {
  const semanticType = inferTy([], term);
  if (!isClosed(term) || semanticType === null) throw new TypeError("digestNamedSen: term must be closed and well typed");
  return identifyNormalizedSemanticContent({
    objectKind: "semiotic-expression-notation.named-term",
    semanticType,
    term,
    witnessRoot: EMPTY_WITNESS_ROOT,
  }).token;
}
