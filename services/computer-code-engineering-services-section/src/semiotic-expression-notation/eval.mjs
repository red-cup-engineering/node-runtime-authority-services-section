/** One SEN contraction table. Step, complete development, and normalization
 * differ only in strategy; all congruence comes from grammar child slots.
 * Each takes the interpreter's primitive table, `{ name: (json) => json }`, for
 * the δ-rule `prim`; a `prim` whose name the table lacks is refused, never stuck. */
import {
  tm,
  instantiateSen,
  boolOfTerm,
  isSenValue,
  mapSenImmediate,
  SEN_FORMS,
  senListHeadTail,
  validateSenTerm,
} from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation";
import {
  jsonToTerm,
  termToJson,
} from "@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation/json-codec";
import { coincides, semanticBytes } from "@red-cup-engineering/computer-content-engineering-services-section/semiotic-content-address";

function dedupe(terms) {
  const seen = new Set();
  return Object.freeze(
    terms.filter((term) => {
      const key = JSON.stringify(term);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }),
  );
}

function rebuild(term, children) {
  return mapSenImmediate(
    term,
    (child, index, childIndex) => children[index]?.[childIndex ?? 0] ?? child,
  );
}

/** Apply a δ-rule: the named primitive on the JSON its value argument encodes. */
function delta(name, argument, primitives) {
  if (!Object.hasOwn(primitives, name)) {
    const error = new Error(`SEN: no primitive named ${JSON.stringify(name)} in this interpreter`);
    error.code = "unknown-primitive";
    throw error;
  }
  return jsonToTerm(primitives[name](termToJson(argument)));
}

/** Contract one root redex using already-selected child terms, or null. */
function contract(term, children = {}, primitives = {}) {
  const child = (index) => children[index]?.[0] ?? term[index];
  switch (term[0]) {
    case "app":
      return term[1][0] === "lam"
        ? instantiateSen(child(1)[1], child(2))
        : null;
    case "fst":
      return term[1][0] === "pair" ? child(1)[1] : null;
    case "snd":
      return term[1][0] === "pair" ? child(1)[2] : null;
    case "coincide":
      return isSenValue(child(1)) && isSenValue(child(2))
        ? tm.bool(semanticBytes(child(1)).equals(semanticBytes(child(2))))
        : null;
    case "cond": {
      const value = boolOfTerm(child(1));
      return value === undefined ? null : value ? child(2) : child(3);
    }
    case "fold": {
      const decomposed = senListHeadTail(child(3));
      if (decomposed === "empty") return child(2);
      if (decomposed === undefined) return null;
      return tm.fold(
        child(1),
        tm.app(tm.app(child(1), child(2)), decomposed.head),
        decomposed.tail,
      );
    }
    case "prim":
      return isSenValue(child(2)) ? delta(term[1], child(2), primitives) : null;
    case "case":
      return child(1)[0] === "inl"
        ? instantiateSen(child(2), child(1)[1])
        : child(1)[0] === "inr"
          ? instantiateSen(child(3), child(1)[2])
          : null;
    default:
      return null;
  }
}

/** Full one-step relation: one root contraction or one immediate-child step. */
function stepUnchecked(term, primitives) {
  const out = [],
    root = contract(term, {}, primitives);
  if (root) out.push(root);
  mapSenImmediate(term, (child, index, childIndex) => {
    for (const next of stepUnchecked(child, primitives)) {
      const children = { [index]: [] };
      if (childIndex === undefined) children[index][0] = next;
      else {
        children[index] = [...term[index]];
        children[index][childIndex] = next;
      }
      out.push(rebuild(term, children));
    }
    return child;
  });
  return dedupe(out);
}

/** Select normal order's one next contraction without constructing the rest
 * of the one-step relation. The descriptor fixes child order for every SEN
 * form, so this remains the same first result as step. */
function firstStepUnchecked(term, primitives) {
  const root = contract(term, {}, primitives);
  if (root) return root;
  const form = SEN_FORMS[term[0]];
  for (const index of form.terms ?? []) {
    const next = firstStepUnchecked(term[index], primitives);
    if (next) {
      const out = [...term];
      out[index] = next;
      return out;
    }
  }
  return undefined;
}

export function step(source, primitives = {}) {
  return stepUnchecked(validateSenTerm(source), primitives);
}

/** Takahashi development: contract only redexes present in the input tree. */
function devUnchecked(term, primitives) {
  const children = {};
  mapSenImmediate(term, (child, index, childIndex) => {
    if (childIndex === undefined) {
      children[index] = [devUnchecked(child, primitives)];
    } else {
      children[index] ??= [...term[index]];
      children[index][childIndex] = devUnchecked(child, primitives);
    }
    return child;
  });
  return contract(term, children, primitives) ?? rebuild(term, children);
}

export function dev(source, primitives = {}) {
  return devUnchecked(validateSenTerm(source), primitives);
}

/** Normal order over the same contraction table; it never returns undefined. */
export function normalize(source, primitives = {}) {
  let current = validateSenTerm(source);
  while (true) {
    const next = firstStepUnchecked(current, primitives);
    if (!next) return current;
    current = next;
  }
}
export const evaluate = normalize;
export { evaluate as eval };

/** Call-by-need over the same contraction table. Normal order re-searches the
 * whole term per step and duplicates unevaluated arguments under substitution,
 * which is exponential on folds whose combiner uses its accumulator twice
 * (dedupe, member). Here a term meets its environment as a closure, each
 * argument is one memoized thunk, and a fold's accumulator is forced per
 * element. SEN is confluent, so whenever this reaches a data normal form it is
 * normal order's normal form. A redex the table leaves stuck (a cond on an
 * unknown or contested reading, a free variable, abort) or a lambda in the
 * result is not data: the caller falls back to `normalize`, which owns those. */
const STUCK = Symbol("sen-stuck");
const stuck = () => {
  throw STUCK;
};

class Thunk {
  constructor(term, env) {
    this.term = term;
    this.env = env;
    this.value = undefined;
  }
}
const ready = (value) => {
  const thunk = new Thunk(undefined, undefined);
  thunk.value = value;
  return thunk;
};
const bind = (thunk, env) => ({ thunk, next: env });

function force(thunk, primitives) {
  if (thunk.value === undefined) {
    if (thunk.term === undefined) stuck(); // re-entered while forcing: a cycle
    const { term, env } = thunk;
    thunk.term = undefined;
    thunk.value = whnf(term, env, primitives);
    thunk.env = undefined;
  }
  return thunk.value;
}

function apply(fn, argument, primitives) {
  if (fn.form !== "lam") stuck();
  return whnf(fn.body, bind(argument, fn.env), primitives);
}

function whnf(term, env, primitives) {
  switch (term[0]) {
    case "var": {
      let frame = env;
      for (let index = term[1]; index > 0 && frame; index -= 1) frame = frame.next;
      if (!frame) stuck();
      return force(frame.thunk, primitives);
    }
    case "lam":
      return { form: "lam", body: term[1], env };
    case "app":
      return apply(whnf(term[1], env, primitives), new Thunk(term[2], env), primitives);
    case "pair":
      return { form: "pair", left: new Thunk(term[1], env), right: new Thunk(term[2], env) };
    case "fst":
    case "snd": {
      const pair = whnf(term[1], env, primitives);
      if (pair.form !== "pair") stuck();
      return force(term[0] === "fst" ? pair.left : pair.right, primitives);
    }
    case "star":
      return { form: "star" };
    case "mark":
      return { form: "mark", surface: term[1] };
    case "coincide": {
      const left = deepForce(whnf(term[1], env, primitives), primitives),
        right = deepForce(whnf(term[2], env, primitives), primitives);
      return { form: "mark", surface: coincident(left, right) ? "held" : "denied" };
    }
    case "cond": {
      const test = whnf(term[1], env, primitives);
      if (test.form !== "mark" || (test.surface !== "held" && test.surface !== "denied")) stuck();
      return whnf(test.surface === "held" ? term[2] : term[3], env, primitives);
    }
    case "fold": {
      const combine = new Thunk(term[1], env);
      let list = whnf(term[3], env, primitives),
        accumulator = new Thunk(term[2], env);
      if (list.form !== "pair" || force(list.left, primitives).form !== "mark") stuck();
      let spine = force(list.right, primitives);
      while (spine.form === "pair") {
        const step = apply(force(combine, primitives), accumulator, primitives);
        accumulator = ready(apply(step, spine.left, primitives));
        spine = force(spine.right, primitives);
      }
      if (spine.form !== "star") stuck();
      return force(accumulator, primitives);
    }
    case "prim":
      return whnf(delta(term[1], reify(whnf(term[2], env, primitives), primitives), primitives), undefined, primitives);
    case "inl":
      return { form: "inl", value: new Thunk(term[1], env), type: term[2] };
    case "inr":
      return { form: "inr", value: new Thunk(term[2], env), type: term[1] };
    case "case": {
      const subject = whnf(term[1], env, primitives);
      if (subject.form === "inl") return whnf(term[2], bind(subject.value, env), primitives);
      if (subject.form === "inr") return whnf(term[3], bind(subject.value, env), primitives);
      return stuck();
    }
    default:
      return stuck();
  }
}

/** Force a weak head value through to closed data, as `coincide` demands both
 * sides be values before it contracts; a lambda is not data. */
const forced = new WeakSet();
function deepForce(value, primitives) {
  const pending = [value];
  while (pending.length > 0) {
    const current = pending.pop();
    if (forced.has(current)) continue;
    switch (current.form) {
      case "pair":
        pending.push(force(current.left, primitives), force(current.right, primitives));
        break;
      case "inl":
      case "inr":
        pending.push(force(current.value, primitives));
        break;
      case "star":
      case "mark":
        break;
      default:
        stuck();
    }
    forced.add(current);
  }
  return value;
}

/** Coincidence of two forced data values, without encoding either: canonical
 * CBOR writes a tagged array as its members' encodings in order, so the bytes
 * agree exactly when the forms agree and the members coincide, down to the
 * marks, which coincide as the content address's own scalars do. */
function coincident(left, right) {
  const pending = [[left, right]];
  while (pending.length > 0) {
    const [a, b] = pending.pop();
    if (a === b) continue;
    if (a.form !== b.form) return false;
    switch (a.form) {
      case "mark":
        if (!coincides(a.surface, b.surface)) return false;
        break;
      case "pair":
        pending.push([a.left.value, b.left.value], [a.right.value, b.right.value]);
        break;
      case "inl":
      case "inr":
        if (!semanticBytes(a.type).equals(semanticBytes(b.type))) return false;
        pending.push([a.value.value, b.value.value]);
        break;
      default:
        break;
    }
  }
  return true;
}

/** Deep-force a weak head value into its closed data term; a lambda is not data. */
const reified = new WeakMap();
function reify(value, primitives) {
  const known = reified.get(value);
  if (known) return known;
  let term;
  switch (value.form) {
    case "star":
      term = tm.star();
      break;
    case "mark":
      term = tm.mark(value.surface);
      break;
    case "pair":
      term = tm.pair(reify(force(value.left, primitives), primitives), reify(force(value.right, primitives), primitives));
      break;
    case "inl":
      term = tm.inl(reify(force(value.value, primitives), primitives), value.type);
      break;
    case "inr":
      term = tm.inr(value.type, reify(force(value.value, primitives), primitives));
      break;
    default:
      stuck();
  }
  reified.set(value, term);
  return term;
}

/** A run term is admitted once per frozen tree; `jsonToTerm` builds only valid data. */
const admitted = new WeakSet();
function admit(runTerm) {
  if (admitted.has(runTerm)) return runTerm;
  validateSenTerm(runTerm);
  if (Object.isFrozen(runTerm)) admitted.add(runTerm);
  return runTerm;
}

export function evaluateRunTerm(runTerm, input, primitives = {}) {
  const source = tm.app(admit(runTerm), jsonToTerm(input));
  let value;
  try {
    value = reify(whnf(source, undefined, primitives), primitives);
  } catch {
    // Stuck, a lambda, or a failure the eager accumulator may have reached
    // where normal order would not: normal order decides.
    return termToJson(normalize(source, primitives));
  }
  return termToJson(value);
}
