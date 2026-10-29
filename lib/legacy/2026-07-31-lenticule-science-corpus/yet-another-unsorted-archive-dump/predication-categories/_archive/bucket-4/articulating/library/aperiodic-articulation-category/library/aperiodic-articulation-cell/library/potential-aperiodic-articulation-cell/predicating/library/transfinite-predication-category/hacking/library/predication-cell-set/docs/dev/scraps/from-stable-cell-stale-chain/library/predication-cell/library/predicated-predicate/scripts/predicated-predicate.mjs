import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../../../../..");

const schema = JSON.parse(
  readFileSync(resolve(__dirname, "../predicated-predicate.schema.json"), "utf8"),
);
const predicateSchema = JSON.parse(
  readFileSync(
    resolve(
      REPO_ROOT,
      "library/object/library/thing/library/category/library/predicate-category/library/predicate/predicate.schema.json",
    ),
    "utf8",
  ),
);

const ajv = new Ajv2020({ allErrors: true, strict: false });
ajv.addSchema(predicateSchema, predicateSchema.$id);
const validate = ajv.compile(schema);

/**
 * Construct and validate a predicated-predicate.
 *
 * A predicated-predicate is a predicate in the second-coordinate role of a
 * predication cell. The schema is structurally predicate's schema, referenced
 * via $ref; the role is fixed by the schema's $id. Validation therefore
 * delegates to predicate's schema, and a successful validation is the theorem
 * "this data is a predicate that can stand in cell-second-coordinate position
 * and index a fiber algebra A_p."
 */
export default function predicatedPredicate(input) {
  if (!validate(input)) {
    throw new TypeError(
      `predicated-predicate: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return input;
}

export function validatePredicatedPredicate(p) {
  if (!validate(p)) {
    throw new TypeError(
      `predicated-predicate: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return true;
}

export { schema as predicatedPredicateSchema };
