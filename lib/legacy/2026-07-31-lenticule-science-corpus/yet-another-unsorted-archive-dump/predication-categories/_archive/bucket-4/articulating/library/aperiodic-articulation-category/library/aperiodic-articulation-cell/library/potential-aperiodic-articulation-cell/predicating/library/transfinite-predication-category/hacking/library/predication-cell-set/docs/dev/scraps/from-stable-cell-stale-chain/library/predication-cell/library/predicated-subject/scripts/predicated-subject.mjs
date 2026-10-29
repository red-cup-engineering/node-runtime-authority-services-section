import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../../../../..");

const schema = JSON.parse(
  readFileSync(resolve(__dirname, "../predicated-subject.schema.json"), "utf8"),
);
const entitySchema = JSON.parse(
  readFileSync(
    resolve(REPO_ROOT, "library/entity-set/library/entity/entity.schema.json"),
    "utf8",
  ),
);

const ajv = new Ajv2020({ allErrors: true, strict: false });
ajv.addSchema(entitySchema, entitySchema.$id);
const validate = ajv.compile(schema);

/**
 * Construct and validate a predicated-subject.
 *
 * A predicated-subject is an entity in the first-coordinate role of a
 * predication cell. The schema is structurally entity's schema, referenced
 * via $ref; the role is fixed by the schema's $id. Validation therefore
 * delegates to entity's schema, and a successful validation is the theorem
 * "this data is an entity that can stand in subject-position."
 */
export default function predicatedSubject(input) {
  if (!validate(input)) {
    throw new TypeError(
      `predicated-subject: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return input;
}

export function validatePredicatedSubject(s) {
  if (!validate(s)) {
    throw new TypeError(
      `predicated-subject: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return true;
}

export { schema as predicatedSubjectSchema };
