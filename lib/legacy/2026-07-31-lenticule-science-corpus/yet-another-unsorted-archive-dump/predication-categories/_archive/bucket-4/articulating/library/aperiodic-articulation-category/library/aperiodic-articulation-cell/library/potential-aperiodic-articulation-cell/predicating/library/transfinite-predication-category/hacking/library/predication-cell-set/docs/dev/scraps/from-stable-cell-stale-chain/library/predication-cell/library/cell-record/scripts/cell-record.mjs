import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../..");

const cellRecordSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library/cell-record/cell-record.schema.json"), "utf8"),
);
const predicationCellSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library/predication-cell/predication-cell.schema.json"), "utf8"),
);
const bilatticeValueSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library/bilattice-value/bilattice-value.schema.json"), "utf8"),
);
const bilatticeSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library/variety/library/bilattice/bilattice.schema.json"), "utf8"),
);
const cellIdSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library/cell-id/cell-id.schema.json"), "utf8"),
);

const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats.default(ajv);
ajv.addSchema(cellRecordSchema, cellRecordSchema.$id);
ajv.addSchema(predicationCellSchema, predicationCellSchema.$id);
ajv.addSchema(bilatticeValueSchema, bilatticeValueSchema.$id);
ajv.addSchema(bilatticeSchema, bilatticeSchema.$id);
ajv.addSchema(cellIdSchema, cellIdSchema.$id);
const validate = ajv.compile(cellRecordSchema);

/**
 * Construct and validate a cell-record.
 *
 * A cell-record is the triple (cell, value, t) pairing a predication-cell
 * with a bilattice-value under some valuation, carrying an ISO-8601
 * transaction-id. Optional provenance fields are passed through if present.
 *
 * @param {{cell: object, value: object, t?: string, stratum?: string, "derived-from"?: string[], "derived-via"?: string}} input
 * @returns {object} the validated cell-record
 */
export default function cellRecord(input) {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("cell-record: input must be an object");
  }
  const record = {
    cell: input.cell,
    value: input.value,
    t: input.t ?? new Date().toISOString(),
  };
  if (input.stratum !== undefined) record.stratum = input.stratum;
  if (input["derived-from"] !== undefined) record["derived-from"] = input["derived-from"];
  if (input["derived-via"] !== undefined) record["derived-via"] = input["derived-via"];
  if (!validate(record)) {
    throw new TypeError(
      `cell-record: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return record;
}

/**
 * Validate an existing cell-record. Returns true on conformance, throws
 * otherwise. Useful for verifying records read from a JSONL log.
 */
export function validateCellRecord(record) {
  if (!validate(record)) {
    throw new TypeError(
      `cell-record: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return true;
}

export { cellRecordSchema };
