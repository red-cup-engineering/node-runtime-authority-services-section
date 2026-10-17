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

/**
 * Receive a governed computational budget from the *process-local* host.
 *
 * A remote JSON request can ask for a quantity but cannot authorize the
 * capacity to execute it. The actual Code/Systems host must install a
 * withResourceBudget request/continuation port in its execution context,
 * acquire the available allowance, account for work in the continuation,
 * and return exactly that output. This primitive supplies no budgets and
 * performs no resource accounting on the host's behalf.
 *
 * A missed callback, duplicate invocation, enlarged grant or substituted
 * result refuses. A function-valued port cannot arrive through JSON/RPC
 * input; trusted host construction is essential. In-process arbitrary JS
 * execution is outside this transport boundary's authority.
 */
export function withHostResourceBudget(context, { resource, requested } = {}, execute) {
  if (typeof resource !== "string" || !resource.trim() ||
      !Number.isSafeInteger(requested) || requested < 1 ||
      typeof execute !== "function")
    throw new TypeError("host budget requires a resource, positive safe integer request and function");
  const port = context?.withResourceBudget;
  if (typeof port !== "function")
    throw Object.assign(new Error("host-owned computational capacity is unavailable"), {
      code: "HostResourceUnavailable",
    });
  let called = false;
  let result;
  const work = granted => {
    if (called)
      throw Object.assign(new Error("host budget continuation was invoked twice"), {
        code: "HostBudgetRepeated",
      });
    called = true;
    if (!Number.isSafeInteger(granted) || granted < 1 || granted > requested)
      throw Object.assign(new RangeError("host grant is not a positive bound of the requested budget"), {
        code: "HostBudgetInvalid",
      });
    result = execute(granted);
    return result;
  };
  const completed = output => {
    if (!called || output !== result)
      throw Object.assign(new Error("host budget did not deliver the actual operation result"), {
        code: "HostBudgetUnreceived",
      });
    return output;
  };
  const finishedAsync = async output => {
    const produced = await result;
    if (!called || output !== produced)
      throw Object.assign(new Error("host budget did not deliver the actual operation result"), {
        code: "HostBudgetUnreceived",
      });
    return produced;
  };
  const value = port(Object.freeze({ resource, requested }), work);
  return isPromiseLike(value) || isPromiseLike(result)
    ? Promise.resolve(value).then(finishedAsync) : completed(value);
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
    // Permission is a set of exact effect names, never substring inclusion on a string.
    // A string such as "internet" must not authorize the distinct "net" effect.
    const allowedEffects = options.allowedEffects ?? [];
    if (!Array.isArray(allowedEffects) || !allowedEffects.every((effect) => typeof effect === "string" && effect.length > 0))
      return refusal("EffectRefused", "allowedEffects must be an array of nonempty effect names");
    if (!op.effects.every((effect) => allowedEffects.includes(effect))) return refusal("EffectRefused", "operation effects exceed allowed effects");
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
  // Use the existing typed code-admission gate before inspecting either operation.
  // A malformed or untrusted operation is a typed refusal, not a dereference
  // inside SignCell subtype comparison or an untyped SEN exception.
  const admittedProducer = admitOperation(producer);
  const admittedConsumer = admitOperation(consumer);
  if (!admittedProducer.ok || !admittedConsumer.ok)
    return refusal("CompositionRefused", "both operations must be admitted before composition");
  producer = admittedProducer.value;
  consumer = admittedConsumer.value;
  if (!isSubtypeOf(producer.codomain, consumer.domain)) return refusal("CompositionRefused", "producer codomain is not a declared subtype of consumer domain");
  if (producer?.body?.kind !== "sen" || consumer?.body?.kind !== "sen") return refusal("CompositionRefused", "only portable SEN bodies compose");
  const middle = descriptorTy(producer.body.outputDescriptor);
  const domain = descriptorTy(consumer.body.inputDescriptor);
  if (!tyEqual(middle, domain)) return refusal("CompositionRefused", "SEN descriptor types differ");
  if (descriptorIdentity(producer.body.outputDescriptor) !== descriptorIdentity(consumer.body.inputDescriptor)) return refusal("CompositionRefused", "SEN descriptors differ");
  const term = tm.lam(tm.app(shiftSen(1, 0, consumer.body.term), tm.app(shiftSen(1, 0, producer.body.term), tm.var(0))));
  if (!checkTy([], term, ty.arrow(descriptorTy(producer.body.inputDescriptor), descriptorTy(consumer.body.outputDescriptor)))) return refusal("CompositionRefused", "composed term does not typecheck");
  return admitOperation({ specification: COMPUTER_ENGINEERING_SPECIFICATION_ID, id, domain: producer.domain, codomain: consumer.codomain, effects: [...producer.effects, ...consumer.effects], body: { kind: "sen", term, inputDescriptor: producer.body.inputDescriptor, outputDescriptor: consumer.body.outputDescriptor } });
}
