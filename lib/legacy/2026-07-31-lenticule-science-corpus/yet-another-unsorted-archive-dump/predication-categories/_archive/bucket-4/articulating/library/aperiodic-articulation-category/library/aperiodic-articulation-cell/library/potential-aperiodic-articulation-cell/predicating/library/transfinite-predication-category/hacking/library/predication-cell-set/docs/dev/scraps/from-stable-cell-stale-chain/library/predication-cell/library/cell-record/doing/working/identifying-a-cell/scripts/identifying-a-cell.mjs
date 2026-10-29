import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../../");

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
ajv.addSchema(predicationCellSchema, predicationCellSchema.$id);
ajv.addSchema(bilatticeValueSchema, bilatticeValueSchema.$id);
ajv.addSchema(bilatticeSchema, bilatticeSchema.$id);
ajv.addSchema(cellIdSchema, cellIdSchema.$id);
const validateRecord = ajv.compile(cellRecordSchema);

// Canonical JSON serialization: keys sorted lexicographically at every object level,
// no whitespace, strict JSON. Matches RFC 8785 (JCS) shape for the subset of JSON
// values cell-records use.
function canonicalize(value) {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new RangeError("identifying-a-cell: non-finite number in canonical-JSON");
    return JSON.stringify(value);
  }
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) {
    return "[" + value.map(canonicalize).join(",") + "]";
  }
  if (typeof value === "object") {
    const keys = Object.keys(value).sort();
    return (
      "{" +
      keys
        .map((k) => JSON.stringify(k) + ":" + canonicalize(value[k]))
        .join(",") +
      "}"
    );
  }
  throw new TypeError(`identifying-a-cell: unserializable value of type ${typeof value}`);
}

export default async function identifyingACell(input) {
  if (!validateRecord(input)) {
    throw new TypeError(
      `identifying-a-cell: input violates cell-record schema: ${ajv.errorsText(validateRecord.errors)}`,
    );
  }
  const bytes = canonicalize(input);
  const digest = createHash("sha256").update(bytes, "utf8").digest("hex");
  return digest;
}
