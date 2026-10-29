import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../../../..");

const doingSchema = JSON.parse(
  readFileSync(resolve(__dirname, "../doing.schema.json"), "utf8"),
);
const predicationCellSchema = JSON.parse(
  readFileSync(
    resolve(REPO_ROOT, "library/predication-cell-set/library/predication-cell/predication-cell.schema.json"),
    "utf8",
  ),
);
const bilatticeValueSchema = JSON.parse(
  readFileSync(
    resolve(REPO_ROOT, "library/lattice/library/twist-product/library/bilattice-value/bilattice-value.schema.json"),
    "utf8",
  ),
);
const bilatticeSchema = JSON.parse(
  readFileSync(
    resolve(REPO_ROOT, "library/object/library/thing/library/category/library/variety/library/bilattice/bilattice.schema.json"),
    "utf8",
  ),
);
const fourBilatticeSchema = JSON.parse(
  readFileSync(
    resolve(REPO_ROOT, "library/object/library/thing/library/category/library/variety/library/bilattice/library/four-bilattice/four-bilattice.schema.json"),
    "utf8",
  ),
);
const cellIdSchema = JSON.parse(
  readFileSync(
    resolve(REPO_ROOT, "library/predication-cell-set/library/predication-cell/library/cell-record/library/cell-id/cell-id.schema.json"),
    "utf8",
  ),
);

const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats.default(ajv);
ajv.addSchema(predicationCellSchema, predicationCellSchema.$id);
ajv.addSchema(bilatticeValueSchema, bilatticeValueSchema.$id);
ajv.addSchema(bilatticeSchema, bilatticeSchema.$id);
ajv.addSchema(fourBilatticeSchema, fourBilatticeSchema.$id);
ajv.addSchema(cellIdSchema, cellIdSchema.$id);
const validateDoingAct = ajv.compile(doingSchema);

// FOUR bilattice knowledge order ≤_k.
// bot ≤_k {t, f} ≤_k top. {t, f} are ≤_k-incomparable.
const KNOWLEDGE_LEQ = {
  bot: { bot: true, t: true,  f: true,  top: true  },
  t:   { bot: false, t: true, f: false, top: true  },
  f:   { bot: false, t: false, f: true, top: true  },
  top: { bot: false, t: false, f: false, top: true },
};

const BELNAP_CLASS_BY_SYMBOL = {
  t: "inferring",
  f: "refuting",
  bot: "idling",
  top: "conflicting",
};

const STRATUM_BY_KIND = {
  sigma: "saturated",
  delta: "settled",
};

/**
 * Apply one settling-step against a predication-settling and return the
 * doing-act record witnessing the step.
 *
 * A doing-act is one operationally-realized advance v_τ → v_{τ+1} at one
 * affected cell, performed by applying either:
 *   - kind 'sigma' — the closure-operator nucleus, firing one rule of the
 *                    closure-rule-system against premise atoms at strata ≤ 1
 *                    and emitting a stratum-1 ('saturated') atom; or
 *   - kind 'delta' — the bilattice-stabilization-nucleus, iterating T_a^* at
 *                    the target cell to fixed point against atoms at strata
 *                    ≤ 2 and emitting a stratum-2 ('settled') atom.
 *
 * Settling monotonicity v_τ(p) ≤_k v_{τ+1}(p) is enforced against the FOUR
 * bilattice's knowledge order at construction time; non-monotone inputs
 * throw RangeError. Stratum is pinned from kind; belnap-class is derived
 * from value-after.
 *
 * Performs no filesystem write; appending the record to any persisted log
 * (doing.jsonl) is the caller's choice.
 *
 * @param {{
 *   cell: {subject: string, predicate: string, object: any},
 *   "value-before": {bilattice: object, value: string},
 *   "value-after":  {bilattice: object, value: string},
 *   kind: 'sigma'|'delta',
 *   "derived-from": string[],
 *   "derived-via": string,
 *   t?: string,
 *   "closure-status"?: string
 * }} input
 * @returns {object} the validated doing-act record
 */
export default function doing(input) {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("doing: input must be an object");
  }
  const kind = input.kind;
  const stratum = STRATUM_BY_KIND[kind];
  if (!stratum) {
    throw new TypeError(
      `doing: kind must be 'sigma' or 'delta'; got ${JSON.stringify(kind)}`,
    );
  }
  const before = input["value-before"]?.value;
  const after = input["value-after"]?.value;
  if (!(before in KNOWLEDGE_LEQ) || !(after in KNOWLEDGE_LEQ)) {
    throw new TypeError(
      `doing: value-before and value-after must each carry a bilattice-value symbol in the FOUR Belnap quartet {t,f,bot,top}; got before=${JSON.stringify(before)}, after=${JSON.stringify(after)}`,
    );
  }
  if (!KNOWLEDGE_LEQ[before][after]) {
    throw new RangeError(
      `doing: settling monotonicity violated — value-before '${before}' is not ≤_k value-after '${after}' in the FOUR bilattice. A doing-act can only raise the knowledge-order value at the cell, never lower or sidestep it.`,
    );
  }
  const belnapClass = BELNAP_CLASS_BY_SYMBOL[after];
  const premises = input["derived-from"];
  if (!Array.isArray(premises) || premises.length === 0) {
    throw new TypeError(
      "doing: derived-from must be a non-empty array of cell-ids; a doing-act always consumes at least one premise atom",
    );
  }
  const derivedVia = input["derived-via"];
  if (typeof derivedVia !== "string" || derivedVia.length === 0) {
    throw new TypeError(
      "doing: derived-via must be a gerund-slug naming the closure-rule or stabilization operator",
    );
  }
  const record = {
    cell: input.cell,
    "value-before": input["value-before"],
    "value-after": input["value-after"],
    kind,
    stratum,
    "derived-from": premises,
    "derived-via": derivedVia,
    "belnap-class": belnapClass,
    t: input.t ?? new Date().toISOString(),
  };
  if (input["closure-status"] !== undefined) {
    record["closure-status"] = input["closure-status"];
  }
  if (!validateDoingAct(record)) {
    throw new TypeError(
      `doing: record violates doing-act schema: ${ajv.errorsText(validateDoingAct.errors)}`,
    );
  }
  return record;
}

/**
 * σ-doing-act constructor — sugar for `doing({...input, kind: 'sigma'})`.
 */
export function sigmaDoing(input) {
  return doing({ ...input, kind: "sigma" });
}

/**
 * Δ-doing-act constructor — sugar for `doing({...input, kind: 'delta'})`.
 * Default derived-via slug is 'bilattice-stabilization'; callers may override.
 */
export function deltaDoing(input) {
  return doing({
    "derived-via": "bilattice-stabilization",
    ...input,
    kind: "delta",
  });
}

/**
 * Classify the post-step closure-status of the affected cell from booleans
 * recording whether σ and Δ have reached fixed-point there. Returns the
 * 4-class label from the orthogonal taxonomy.
 */
export function closureStatus({ sigmaFixed, deltaFixed }) {
  if (sigmaFixed && deltaFixed) return "fully-settled";
  if (sigmaFixed && !deltaFixed) return "stabilization-pending";
  if (!sigmaFixed && deltaFixed) return "saturation-pending";
  return "fully-open";
}

/**
 * Validate an existing record against the doing-act schema. Throws on
 * violation, returns true otherwise. Does not re-check monotonicity — that
 * lives in the constructor.
 */
export function validateDoing(record) {
  if (!validateDoingAct(record)) {
    throw new TypeError(
      `doing: record violates doing-act schema: ${ajv.errorsText(validateDoingAct.errors)}`,
    );
  }
  return true;
}

export { doingSchema };
