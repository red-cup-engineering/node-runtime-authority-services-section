import { admit, collectTypeSystem, isSubtypeOf } from "@red-cup-engineering/signcell/type-system";
import { tm, ty, shiftSen } from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation";
import { evaluate, evaluateRunTerm } from "./semiotic-expression-notation/eval.mjs";
import { descriptorTy, encodeDescriptor, decodeDescriptor } from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation/json-codec";
import { checkTy, tyEqual } from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation/typing";

/** The common engineering specification addressed by portable executable code. */
export const COMPUTER_ENGINEERING_SPECIFICATION_ID = "https://schemas.561.group/computer/computer-engineering.schema.json";
export const COMPUTER_CODE_SPECIFICATION = COMPUTER_ENGINEERING_SPECIFICATION_ID;

export function isPromiseLike(value) {
  return value !== null && (typeof value === "object" || typeof value === "function") && typeof value.then === "function";
}

/** Evaluate one precondition/body/postcondition boundary without imposing host or transport policy. */
export function evaluateBoundary(input, admitInput, move, admitOutput) {
  const admitted = admitInput(input);
  const output = move(admitted);
  return isPromiseLike(output) ? Promise.resolve(output).then(admitOutput) : admitOutput(output);
}

export const refusal = (code, message) => Object.freeze({ ok: false, refusal: Object.freeze({ code, message }) });
const accepted = (value) => Object.freeze({ ok: true, value });
const validEffects = (effects) => Array.isArray(effects) && effects.every((effect) => typeof effect === "string" && effect.length > 0);
const establishedOperations = new WeakSet();

/** Deep-freeze a structured clone so an admitted portable body cannot be changed after admission. */
export function immutableBody(body) {
  const result = structuredClone(body);
  const pending = [result];
  const seen = new Set();
  while (pending.length > 0) {
    const current = pending.pop();
    if (seen.has(current)) continue;
    seen.add(current);
    for (const value of Object.values(current)) if (value !== null && typeof value === "object") pending.push(value);
    Object.freeze(current);
  }
  return result;
}

/** Admit one executable code declaration without selecting a host, a registry, or a transport. */
export function admitOperation(definition) {
  if (establishedOperations.has(definition)) return accepted(definition);
  if (!definition || definition.specification !== COMPUTER_ENGINEERING_SPECIFICATION_ID || typeof definition.id !== "string" || definition.id.length === 0) {
    return refusal("InvalidOperation", "operation must name the computer engineering specification and a nonempty id");
  }
  if (!definition.domain || !definition.codomain || typeof definition.domain.id !== "string" || typeof definition.codomain.id !== "string" || typeof definition.domain.schema === "undefined" || typeof definition.codomain.schema === "undefined" || !validEffects(definition.effects)) {
    return refusal("InvalidOperation", "operation needs admitted domain/codomain identities and string effects");
  }
  if (!collectTypeSystem([definition.domain, definition.codomain]).ok) return refusal("InvalidOperation", "operation types must share established declarations");
  const body = definition.body;
  if (!body || !["sen", "capability-effect"].includes(body.kind)) return refusal("InvalidOperation", "operation body must be sen or a capability effect");
  if (body.kind === "capability-effect" && (typeof body.capability !== "string" || body.capability.length === 0)) return refusal("InvalidOperation", "capability effect needs a capability");
  if (body.kind === "sen" && (!body.term || !body.inputDescriptor || !body.outputDescriptor)) return refusal("InvalidOperation", "sen body needs term and descriptors");
  let copiedBody;
  try {
    copiedBody = immutableBody(body);
    if (copiedBody.kind === "sen" && !checkTy([], copiedBody.term, ty.arrow(descriptorTy(copiedBody.inputDescriptor), descriptorTy(copiedBody.outputDescriptor)))) {
      return refusal("InvalidOperation", "SEN term does not typecheck against its descriptors");
    }
  } catch (error) {
    return refusal("InvalidOperation", error instanceof Error ? error.message : String(error));
  }
  const operation = Object.freeze({
    specification: COMPUTER_ENGINEERING_SPECIFICATION_ID,
    version: 1,
    id: definition.id,
    ...(typeof definition.description === "string" ? { description: definition.description } : {}),
    domain: definition.domain,
    codomain: definition.codomain,
    effects: Object.freeze([...new Set(definition.effects)]),
    body: copiedBody,
  });
  establishedOperations.add(operation);
  return accepted(operation);
}

/** Declare a host capability effect through the same typed code-declaration admission. */
export function declareCapabilityOperation(definition) {
  return admitOperation({
    specification: COMPUTER_ENGINEERING_SPECIFICATION_ID,
    id: definition.id,
    ...(typeof definition.description === "string" ? { description: definition.description } : {}),
    domain: definition.domain,
    codomain: definition.codomain,
    effects: definition.effects ?? [],
    body: { kind: "capability-effect", capability: definition.capability ?? definition.id },
  });
}

function caught(error) {
  const code = error !== null && typeof error === "object" && typeof error.code === "string" && error.code.length > 0 ? error.code : undefined;
  return refusal(code ?? (error instanceof Error ? error.name : "ExecutionFailed"), error instanceof Error ? error.message : String(error));
}

/** Execute a portable term or explicitly granted host capability, with typed admission before and after the effect. */
export function executeOperation(operation, input, options = {}) {
  try {
    const domain = options.resolveType ? options.resolveType(operation?.domain?.id) : operation?.domain;
    const codomain = options.resolveType ? options.resolveType(operation?.codomain?.id) : operation?.codomain;
    if (!domain || !codomain) return refusal("TypeUnavailable", "operation type identity cannot be resolved");
    if (!collectTypeSystem([operation.domain, operation.codomain, domain, codomain]).ok) return refusal("TypeIdentityConflict", "resolved types conflict with the operation's declarations");
    const admitted = admitOperation(operation);
    if (!admitted.ok) return admitted;
    const op = admitted.value;
    if (!op.effects.every((effect) => (options.allowedEffects ?? []).includes(effect))) return refusal("EffectRefused", "operation effects exceed allowed effects");
    const predicate = (type, code) => (value) => {
      const result = admit(type, value);
      if (!result.ok) throw Object.assign(new TypeError(result.refusal.issues.map((issue) => `${issue.path || "/"} ${issue.message}`).join("; ")), { code });
      return value;
    };
    const move = (value) => {
      if (op.body.kind === "sen") {
        const body = op.body;
        return decodeDescriptor(body.outputDescriptor, evaluate(tm.app(body.term, encodeDescriptor(body.inputDescriptor, value))));
      }
      if (!options.resolveHost) throw Object.assign(new Error("no host capability resolver"), { code: "HostUnavailable" });
      const invoke = (capability) => {
        if (typeof capability !== "function") throw Object.assign(new Error("host capability is unavailable"), { code: "HostUnavailable" });
        return capability(value);
      };
      const host = options.resolveHost(op.body.capability, op.effects);
      return isPromiseLike(host) ? Promise.resolve(host).then(invoke) : invoke(host);
    };
    const output = evaluateBoundary(input, predicate(domain, "InvalidInput"), move, predicate(codomain, "InvalidOutput"));
    return isPromiseLike(output) ? Promise.resolve(output).then(accepted).catch(caught) : accepted(output);
  } catch (error) {
    return caught(error);
  }
}

/** Bind a local JavaScript or portable SEN body to declared pre/postconditions. */
export function createOperationExecutor(definition) {
  if (typeof definition.id !== "string" || definition.id.trim().length === 0) throw new TypeError("operation: id is required");
  if (definition.run === undefined && definition.runTerm === undefined) throw new TypeError(`operation ${definition.id}: run or runTerm is required`);
  const { id, domain, codomain, projectOutput } = definition;
  const runTerm = definition.runTerm === undefined ? undefined : immutableBody(definition.runTerm);
  const body = definition.run ?? ((input) => evaluateRunTerm(runTerm, input));
  const inputPredicate = (value) => domain === undefined ? value : domain.assert(value, `operation ${id} input`);
  const outputPredicate = (value) => codomain === undefined ? value : codomain.assert(value, `operation ${id} output`);
  const finish = projectOutput === undefined ? outputPredicate : (output) => projectOutput(output, outputPredicate);
  return (input, arguments_, context) => evaluateBoundary(input, inputPredicate, (admitted) => body(admitted, arguments_, context), finish);
}

const descriptorIdentity = (value) => value === null || typeof value !== "object" ? JSON.stringify(value) ?? "undefined" : Array.isArray(value) ? `[${value.map(descriptorIdentity).join(",")}]` : `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${descriptorIdentity(value[key])}`).join(",")}}`;

/** Compose portable operations only when their declared carrier and SEN boundaries agree. */
export function composeOperations(producer, consumer, id) {
  if (!isSubtypeOf(producer?.codomain, consumer?.domain)) return refusal("CompositionRefused", "producer codomain is not a declared subtype of consumer domain");
  if (producer?.body?.kind !== "sen" || consumer?.body?.kind !== "sen") return refusal("CompositionRefused", "only portable SEN bodies compose");
  const middle = descriptorTy(producer.body.outputDescriptor);
  const domain = descriptorTy(consumer.body.inputDescriptor);
  if (!tyEqual(middle, domain)) return refusal("CompositionRefused", "SEN descriptor types differ");
  if (descriptorIdentity(producer.body.outputDescriptor) !== descriptorIdentity(consumer.body.inputDescriptor)) return refusal("CompositionRefused", "SEN descriptors differ");
  const term = tm.lam(tm.app(shiftSen(1, 0, consumer.body.term), tm.app(shiftSen(1, 0, producer.body.term), tm.var(0))));
  if (!checkTy([], term, ty.arrow(descriptorTy(producer.body.inputDescriptor), descriptorTy(consumer.body.outputDescriptor)))) return refusal("CompositionRefused", "composed term does not typecheck");
  return admitOperation({ specification: COMPUTER_ENGINEERING_SPECIFICATION_ID, id, domain: producer.domain, codomain: consumer.codomain, effects: [...producer.effects, ...consumer.effects], body: { kind: "sen", term, inputDescriptor: producer.body.inputDescriptor, outputDescriptor: consumer.body.outputDescriptor } });
}
