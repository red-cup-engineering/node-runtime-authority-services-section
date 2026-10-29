import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCHEMA_PATH = resolve(__dirname, "../cell-id.schema.json");

const schema = JSON.parse(readFileSync(SCHEMA_PATH, "utf8"));
const ajv = new Ajv2020({ allErrors: true, strict: false });
const validate = ajv.compile(schema);

/**
 * Canonical-JSON serialization for content addressing.
 *
 * Sorts object keys lexicographically at every level, omits whitespace,
 * forbids NaN / Infinity / undefined (JSON.stringify would already throw on
 * those). The output bytes are stable across hosts so the hash of the same
 * record is reproducible.
 *
 * @param {unknown} value
 * @returns {string} the canonical JSON string
 */
export function canonicalize(value) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return "[" + value.map(canonicalize).join(",") + "]";
  }
  const keys = Object.keys(value).sort();
  const parts = keys.map((k) => JSON.stringify(k) + ":" + canonicalize(value[k]));
  return "{" + parts.join(",") + "}";
}

/**
 * Compute the cell-id of a cell-record.
 *
 * cell-id(record) = SHA-256-hex(canonicalize(record)). The output is a
 * 64-character lowercase hex string conforming to the cell-id schema.
 * Two records with the same canonical encoding produce the same id; any
 * difference in any field produces a different id (up to collision
 * probability of SHA-256).
 *
 * @param {object} record a cell-record (not validated here; pass through
 *   cellRecord() first if you need the schema check)
 * @returns {string} 64-hex-char cell-id
 */
export default function cellId(record) {
  if (record === null || typeof record !== "object" || Array.isArray(record)) {
    throw new TypeError("cell-id: record must be an object");
  }
  const canonical = canonicalize(record);
  const id = createHash("sha256").update(canonical, "utf8").digest("hex");
  if (!validate(id)) {
    throw new TypeError(
      `cell-id: computed id violates schema: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return id;
}

/**
 * Validate that a string is a well-formed cell-id (64-char lowercase hex).
 */
export function validateCellId(id) {
  if (!validate(id)) {
    throw new TypeError(
      `cell-id: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return true;
}

export { schema as cellIdSchema };
