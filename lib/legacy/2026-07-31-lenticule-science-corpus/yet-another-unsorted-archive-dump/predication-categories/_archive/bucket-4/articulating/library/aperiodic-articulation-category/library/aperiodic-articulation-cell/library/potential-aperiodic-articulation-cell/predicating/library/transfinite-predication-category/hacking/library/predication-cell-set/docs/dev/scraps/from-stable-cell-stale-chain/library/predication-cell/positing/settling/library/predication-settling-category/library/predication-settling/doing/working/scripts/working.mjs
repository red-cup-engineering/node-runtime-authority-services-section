import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import doing from "../../scripts/doing.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../../../../..");

const workingSchema = JSON.parse(
  readFileSync(resolve(__dirname, "../working.schema.json"), "utf8"),
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
const validateWorkingAct = ajv.compile(workingSchema);

/**
 * Apply one working-act and return its record.
 *
 * A working-act is the restriction of `doing` (its parent morphism) to
 * target cells in the operational sub-presheaf — categorically the pullback
 * of doing along Φ_op ↪ Φ. The function delegates settling-monotonicity,
 * stratum-from-kind derivation, Belnap classification, and core validation
 * to `doing`, then attaches the operational discriminator and revalidates.
 *
 * @param {{
 *   cell: {subject: string, predicate: string, object: any},
 *   "value-before": {bilattice: object, value: string},
 *   "value-after":  {bilattice: object, value: string},
 *   kind: 'sigma'|'delta',
 *   "derived-from": string[],
 *   "derived-via": string,
 *   t?: string,
 *   "closure-status"?: string,
 *   "target-class"?: 'operational'
 * }} input
 * @returns {object} the validated working-act record
 */
export default function working(input) {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("working: input must be an object");
  }
  if (input["target-class"] !== undefined && input["target-class"] !== "operational") {
    throw new RangeError(
      `working: target-class must be 'operational' (or omitted); got ${JSON.stringify(input["target-class"])}. Doing-acts on normative cells live at sibling governing/; doing-acts on plan-document cells live at sibling planning/.`,
    );
  }
  const doingRecord = doing(input);
  const record = { ...doingRecord, "target-class": "operational" };
  if (!validateWorkingAct(record)) {
    throw new TypeError(
      `working: record violates working-act schema: ${ajv.errorsText(validateWorkingAct.errors)}`,
    );
  }
  return record;
}

/** σ-working-act constructor — sugar for `working({...input, kind: 'sigma'})`. */
export function sigmaWorking(input) {
  return working({ ...input, kind: "sigma" });
}

/** Δ-working-act constructor — sugar for `working({...input, kind: 'delta'})`. */
export function deltaWorking(input) {
  return working({
    "derived-via": "bilattice-stabilization",
    ...input,
    kind: "delta",
  });
}

/** Validate an existing record against the working-act schema. */
export function validateWorking(record) {
  if (!validateWorkingAct(record)) {
    throw new TypeError(
      `working: record violates working-act schema: ${ajv.errorsText(validateWorkingAct.errors)}`,
    );
  }
  return true;
}

export { workingSchema };
