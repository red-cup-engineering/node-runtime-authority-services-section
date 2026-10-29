import { COMPUTER_ENGINEERING_SPECIFICATION_ID, admit, collectTypeSystem, isSubtypeOf, type DataType, type Result } from "@red-cup-engineering/computer-data-engine";
import { tm, ty, shiftRmn, type Tm } from "@red-cup-engineering/relation-model-notation";
import { evaluate } from "@red-cup-engineering/relation-model-notation-eval";
import { descriptorTy, encodeDescriptor, decodeDescriptor, type RmnJsonDescriptor, type JsonValue } from "@red-cup-engineering/relation-model-notation-json-codec";
import { checkTy, tyEqual } from "@red-cup-engineering/relation-model-notation-typing";


export type OperationRefusal = Readonly<{ code: string; message: string }>;
/** This package binds the universal computer specification's code method; it owns no second operation vocabulary. */
export const COMPUTER_CODE_SPECIFICATION = COMPUTER_ENGINEERING_SPECIFICATION_ID;
export type RmnOperationBody = Readonly<{ kind: "rmn"; term: Tm; inputDescriptor: RmnJsonDescriptor; outputDescriptor: RmnJsonDescriptor }>;
/** The imperative shell is a declared capability effect, never an alternate code language. */
export type CapabilityEffectBody = Readonly<{ kind: "capability-effect"; capability: string }>;
export type Operation = Readonly<{ specification: typeof COMPUTER_ENGINEERING_SPECIFICATION_ID; version: 1; id: string; description?: string; domain: DataType; codomain: DataType; effects: readonly string[]; body: RmnOperationBody | CapabilityEffectBody }>;
export type OperationDefinition = Omit<Operation, "version">;
/** A host-capability operation whose type declarations remain at its receiving system. */
export type CapabilityOperationDeclaration = Readonly<{ id: string; description?: string; domain: DataType; codomain: DataType; effects?: readonly string[]; capability?: string }>;
export type HostResolver = (capability: string, effects: readonly string[]) => Promise<((input: unknown) => unknown | Promise<unknown>) | undefined> | ((input: unknown) => unknown | Promise<unknown>) | undefined;
export type { Result };
export type ExecutionOptions = Readonly<{ resolveHost?: HostResolver; resolveType?: (id: string) => DataType | undefined; allowedEffects?: readonly string[] }>;

const refusal = (code: string, message: string): Result<never, OperationRefusal> => Object.freeze({ ok: false, refusal: Object.freeze({ code, message }) });
export type ExecutionResult = Result<unknown, OperationRefusal> | Promise<Result<unknown, OperationRefusal>>;

/** Resolve an operation once, then use the same admission and effect boundary for local and wire calls. */
export function executeOperationById(id: string, input: unknown, options: ExecutionOptions & { resolveOperation?: (id: string) => Operation | undefined }): ExecutionResult {
  try {
    const operation = options.resolveOperation?.(id);
    return operation ? executeOperation(operation, input, options) : refusal("OperationUnavailable", "operation identity cannot be resolved");
  } catch (error) { return caught(error); }
}

const accepted = <T,>(value: T): Result<T, never> => Object.freeze({ ok: true, value });
const validEffects = (effects: readonly string[]) => Array.isArray(effects) && effects.every((effect) => typeof effect === "string" && effect.length > 0);
const descriptorIdentity = (value: unknown): string => value === null || typeof value !== "object" ? JSON.stringify(value) ?? "undefined" : Array.isArray(value) ? `[${value.map(descriptorIdentity).join(",")}]` : `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${descriptorIdentity((value as Record<string, unknown>)[key])}`).join(",")}}`;
const establishedOperations = new WeakSet<Operation>();

function immutableBody(body: Operation["body"]): Operation["body"] {
  const result = structuredClone(body);
  const pending: object[] = [result];
  const seen = new Set<object>();
  while (pending.length > 0) {
    const current = pending.pop()!;
    if (seen.has(current)) continue;
    seen.add(current);
    for (const value of Object.values(current)) if (value !== null && typeof value === "object") pending.push(value);
    Object.freeze(current);
  }
  return result;
}

/** Admit one executable operation without binding a host implementation. */
export function admitOperation(definition: OperationDefinition): Result<Operation, OperationRefusal> {
  if (establishedOperations.has(definition as Operation)) return accepted(definition as Operation);
  if (!definition || definition.specification !== COMPUTER_ENGINEERING_SPECIFICATION_ID || typeof definition.id !== "string" || definition.id.length === 0) return refusal("InvalidOperation", "operation must name the universal computer engineering specification and a nonempty id");
  if (!definition.domain || !definition.codomain || typeof definition.domain.id !== "string" || typeof definition.codomain.id !== "string" || typeof definition.domain.schema === "undefined" || typeof definition.codomain.schema === "undefined" || !validEffects(definition.effects)) return refusal("InvalidOperation", "operation needs admitted domain/codomain identities and string effects");
  if (!collectTypeSystem([definition.domain, definition.codomain]).ok) return refusal("InvalidOperation", "operation types must share established declarations");
  const body = definition.body;
  if (!body || !["rmn", "capability-effect"].includes(body.kind)) return refusal("InvalidOperation", "operation body must be rmn or a capability effect");
  if (body.kind === "capability-effect" && (typeof body.capability !== "string" || body.capability.length === 0)) return refusal("InvalidOperation", "capability effect needs a capability");
  if (body.kind === "rmn" && (!body.term || !body.inputDescriptor || !body.outputDescriptor)) return refusal("InvalidOperation", "rmn body needs term and descriptors");
  let copiedBody: Operation["body"];
  try {
    copiedBody = immutableBody(body);
    if (copiedBody.kind === "rmn" && !checkTy([], copiedBody.term, ty.arrow(descriptorTy(copiedBody.inputDescriptor), descriptorTy(copiedBody.outputDescriptor)))) return refusal("InvalidOperation", "RMN term does not typecheck against its descriptors");
  }
  catch (error) { return refusal("InvalidOperation", error instanceof Error ? error.message : String(error)); }
  const operation = Object.freeze({ specification: COMPUTER_ENGINEERING_SPECIFICATION_ID, version: 1 as const, id: definition.id, ...(typeof definition.description === "string" ? { description: definition.description } : {}), domain: definition.domain, codomain: definition.codomain, effects: Object.freeze([...new Set(definition.effects)]), body: copiedBody });
  establishedOperations.add(operation);
  return accepted(operation);
}

/** Declare a capability-effect operation through the one typed-operation admission path. */
export function declareCapabilityOperation(definition: CapabilityOperationDeclaration): Result<Operation, OperationRefusal> {
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

/** Compose two portable operations after carrier and RMN type equality checks. */
export function composeOperations(producer: Operation, consumer: Operation, id: string): Result<Operation, OperationRefusal> {
  if (!isSubtypeOf(producer?.codomain, consumer?.domain)) return refusal("CompositionRefused", "producer codomain is not a declared subtype of consumer domain");
  if (producer?.body?.kind !== "rmn" || consumer?.body?.kind !== "rmn") return refusal("CompositionRefused", "only portable RMN bodies compose");
  const middle = descriptorTy(producer.body.outputDescriptor), domain = descriptorTy(consumer.body.inputDescriptor);
  if (!tyEqual(middle, domain)) return refusal("CompositionRefused", "RMN descriptor types differ");
  if (descriptorIdentity(producer.body.outputDescriptor) !== descriptorIdentity(consumer.body.inputDescriptor)) return refusal("CompositionRefused", "RMN descriptors differ");
  const term = tm.lam(tm.app(shiftRmn(1, 0, consumer.body.term), tm.app(shiftRmn(1, 0, producer.body.term), tm.var(0))));
  if (!checkTy([], term, ty.arrow(descriptorTy(producer.body.inputDescriptor), descriptorTy(consumer.body.outputDescriptor)))) return refusal("CompositionRefused", "composed term does not typecheck");
  return admitOperation({ specification: COMPUTER_ENGINEERING_SPECIFICATION_ID, id, domain: producer.domain, codomain: consumer.codomain, effects: [...producer.effects, ...consumer.effects], body: { kind: "rmn", term, inputDescriptor: producer.body.inputDescriptor, outputDescriptor: consumer.body.outputDescriptor } });
}

/** Execute through one path, preserving synchronous operations and awaiting only host promises. */
export function executeOperation(operation: Operation, input: unknown, options: ExecutionOptions = {}): ExecutionResult {
  try {
    const domain = options.resolveType ? options.resolveType(operation?.domain?.id) : operation?.domain;
    const codomain = options.resolveType ? options.resolveType(operation?.codomain?.id) : operation?.codomain;
    if (!domain || !codomain) return refusal("TypeUnavailable", "operation type identity cannot be resolved");
    if (!collectTypeSystem([operation.domain, operation.codomain, domain, codomain]).ok) return refusal("TypeIdentityConflict", "resolved types conflict with the operation's declarations");
    const admitted = admitOperation(operation);
    if (!admitted.ok) return admitted;
    const op = admitted.value;
    if (!op.effects.every(effect => (options.allowedEffects ?? []).includes(effect))) return refusal("EffectRefused", "operation effects exceed allowed effects");
    const incoming = admit(domain, input);
    if (!incoming.ok) return refusal("InvalidInput", incoming.refusal.issues.map(issue => `${issue.path || "/"} ${issue.message}`).join("; "));
    const finish = (output: unknown): Result<unknown, OperationRefusal> => {
      const outgoing = admit(codomain, output);
      return outgoing.ok ? accepted(output) : refusal("InvalidOutput", outgoing.refusal.issues.map(issue => `${issue.path || "/"} ${issue.message}`).join("; "));
    };
    if (op.body.kind === "rmn") {
      const body = op.body;
      return finish(decodeDescriptor(body.outputDescriptor, evaluate(tm.app(body.term, encodeDescriptor(body.inputDescriptor, input as JsonValue)))));
    }
    if (!options.resolveHost) return refusal("HostUnavailable", "no host capability resolver");
    const invoke = (capability: Awaited<ReturnType<HostResolver>>): ExecutionResult => {
      if (typeof capability !== "function") return refusal("HostUnavailable", "host capability is unavailable");
      const output = capability(input);
      return isPromiseLike(output) ? Promise.resolve(output).then(finish).catch(caught) : finish(output);
    };
    const host = options.resolveHost(op.body.capability, op.effects);
    return isPromiseLike(host) ? Promise.resolve(host).then(invoke).catch(caught) : invoke(host);
  } catch (error) { return caught(error); }
}

export function isPromiseLike<T>(value: T | PromiseLike<T>): value is PromiseLike<T> {
  return value !== null && (typeof value === "object" || typeof value === "function") && typeof (value as { then?: unknown }).then === "function";
}

/** A thrown host failure keeps its own refusal code when it names one (`error.code`), else its class name, else ExecutionFailed. */
function caught(error: unknown): Result<never, OperationRefusal> {
  const code = error !== null && typeof error === "object" && typeof (error as { code?: unknown }).code === "string" && (error as { code: string }).code.length > 0 ? (error as { code: string }).code : undefined;
  return refusal(code ?? (error instanceof Error ? error.name : "ExecutionFailed"), error instanceof Error ? error.message : String(error));
}
