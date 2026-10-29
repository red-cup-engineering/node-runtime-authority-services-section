import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../..");

const schema = JSON.parse(
  readFileSync(resolve(__dirname, "../relationlessness.schema.json"), "utf8"),
);
const predicationCellSchema = JSON.parse(
  readFileSync(
    resolve(REPO_ROOT, "library/predication-cell-set/library/predication-cell/predication-cell.schema.json"),
    "utf8",
  ),
);

const ajv = new Ajv2020({ allErrors: true, strict: false });
ajv.addSchema(predicationCellSchema, predicationCellSchema.$id);
const validate = ajv.compile(schema);

/**
 * Construct and validate an instance of relationlessness.
 *
 * Relationlessness is the originating predication cell
 *   φ* = (X = "relationlessness", p* = "has-no-relation", R = "relating-locus")
 * and there is exactly one inhabitant — that specific cell. The schema is
 * the predication-cell schema constrained by const at all three
 * coordinates; validating against it is the proof that the cell is φ*.
 *
 * The Leibniz claim this script witnesses: configurational absence has no
 * separate slot in the predicate category. The would-be "nothing" IS this
 * cell, asserted with positive evidence via articulating.
 */
export default function relationlessness(input) {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("relationlessness: input must be a predication-cell object");
  }
  if (!validate(input)) {
    throw new TypeError(
      `relationlessness: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return { subject: input.subject, predicate: input.predicate, object: input.object };
}

export function validateRelationlessness(cell) {
  if (!validate(cell)) {
    throw new TypeError(
      `relationlessness: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return true;
}

export { schema as relationlessnessSchema };
