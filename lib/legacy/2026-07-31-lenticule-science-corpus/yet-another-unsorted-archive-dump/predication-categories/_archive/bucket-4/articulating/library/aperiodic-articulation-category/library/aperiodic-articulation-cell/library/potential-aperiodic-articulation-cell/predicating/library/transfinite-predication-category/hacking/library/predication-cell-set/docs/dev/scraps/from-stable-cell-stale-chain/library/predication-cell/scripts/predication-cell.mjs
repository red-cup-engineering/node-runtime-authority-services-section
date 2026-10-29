import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCHEMA_PATH = resolve(__dirname, "../predication-cell.schema.json");

const schema = JSON.parse(readFileSync(SCHEMA_PATH, "utf8"));

const ajv = new Ajv2020({ allErrors: true, strict: false });
const validate = ajv.compile(schema);

/**
 * Construct and validate a predication-cell.
 *
 * A predication cell is the oriented triple (subject, predicate, object).
 * It is a pure position — it carries no value. The script returns the cell
 * canonicalized to the three required fields and rejects any input that
 * carries extra properties (the schema's additionalProperties: false), in
 * particular any `value` field — values live in the predication fiber
 * algebra at the cell's predicate coordinate, not on the cell itself.
 *
 * @param {{subject: string, predicate: string, object: unknown}} input
 * @returns {{subject: string, predicate: string, object: unknown}}
 */
export default function predicationCell(input) {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("predication-cell: input must be an object");
  }
  if (!validate(input)) {
    throw new TypeError(
      `predication-cell: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return {
    subject: input.subject,
    predicate: input.predicate,
    object: input.object,
  };
}

/**
 * Validate an existing predication-cell against the schema without
 * canonicalization. Returns true on conformance, throws otherwise.
 */
export function validatePredicationCell(cell) {
  if (!validate(cell)) {
    throw new TypeError(
      `predication-cell: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return true;
}

export { schema as predicationCellSchema };
