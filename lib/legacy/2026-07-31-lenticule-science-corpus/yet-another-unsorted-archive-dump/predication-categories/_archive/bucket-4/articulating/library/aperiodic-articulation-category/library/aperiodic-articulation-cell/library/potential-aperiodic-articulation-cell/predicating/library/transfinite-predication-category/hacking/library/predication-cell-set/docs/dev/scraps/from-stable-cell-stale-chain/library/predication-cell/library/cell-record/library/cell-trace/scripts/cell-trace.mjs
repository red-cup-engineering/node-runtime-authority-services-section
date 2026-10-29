import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../../../../../../..");

const schema = JSON.parse(
  readFileSync(resolve(__dirname, "../cell-trace.schema.json"), "utf8"),
);
const cellRecordSchema = JSON.parse(
  readFileSync(
    resolve(REPO_ROOT, "library/predication-cell-set/library/predication-cell/library/cell-record/cell-record.schema.json"),
    "utf8",
  ),
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
ajv.addSchema(cellIdSchema, cellIdSchema.$id);
ajv.addSchema(cellRecordSchema, cellRecordSchema.$id);
const validate = ajv.compile(schema);

/**
 * Construct and validate a cell-trace.
 *
 * Enforces the Theory of Cell-Trace beyond schema shape:
 *   (Axiom 1) same-cell: all records[i].cell are deep-equal — a trace
 *     witnesses the trajectory of one fixed cell, not a hop across cells.
 *   (Axiom 2) transaction-id monotonicity: records[i].t ≤ records[j].t for
 *     i < j — the trace orders by time-of-assertion.
 *   (Axiom 3) shared bilattice context: all records[i].value.bilattice are
 *     deep-equal — the value chain lies in one fiber.
 *   (Axiom 4) ≤_k-value monotonicity: records[i].value.value ≤_k
 *     records[j].value.value for i < j, decided by the shared bilattice's
 *     own knowledge-meet table.
 *
 * The forgetful map cell-trace → predication-cell-trace strips t, stratum,
 * and provenance from each record; if the layer-5 axioms above hold, the
 * layer-1 axioms (same cell + ≤_k-monotone trajectory) hold by construction.
 */
export default function cellTrace(input) {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("cell-trace: input must be an object");
  }
  if (!validate(input)) {
    throw new TypeError(
      `cell-trace: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  const { records } = input;
  if (records.length > 1) {
    const baseCell = records[0].cell;
    for (let i = 1; i < records.length; i += 1) {
      if (!sameCell(records[i].cell, baseCell)) {
        throw new TypeError(
          `cell-trace: same-cell axiom violated at records[${i}]; trace must witness one fixed cell`,
        );
      }
    }
    for (let i = 0; i < records.length - 1; i += 1) {
      if (records[i].t > records[i + 1].t) {
        throw new TypeError(
          `cell-trace: transaction-id monotonicity violated at ${i}→${i + 1}: ${records[i].t} > ${records[i + 1].t}`,
        );
      }
    }
    const ctx = records[0].value.bilattice;
    for (let i = 1; i < records.length; i += 1) {
      if (!sameBilattice(records[i].value.bilattice, ctx)) {
        throw new TypeError(
          `cell-trace: bilattice-context axiom violated at records[${i}]; chain must lie in one fiber`,
        );
      }
    }
    for (let i = 0; i < records.length - 1; i += 1) {
      const a = records[i].value.value;
      const b = records[i + 1].value.value;
      if (!leqKnowledge(ctx, a, b)) {
        throw new TypeError(
          `cell-trace: ≤_k-monotonicity violated at step ${i}→${i + 1}: ${a} not ≤_k ${b}`,
        );
      }
    }
  }
  return { records: input.records };
}

export function validateCellTrace(trace) {
  cellTrace(trace);
  return true;
}

function leqKnowledge(B, a, b) {
  const row = B["knowledge-meet"][a];
  if (row === undefined || row[b] === undefined) {
    throw new RangeError(
      `cell-trace: bilattice's knowledge-meet table missing entry (${a}, ${b})`,
    );
  }
  return row[b] === a;
}

function sameCell(a, b) {
  return a.subject === b.subject && a.predicate === b.predicate && deepEqual(a.object, b.object);
}

function sameBilattice(a, b) {
  return canonical(a) === canonical(b);
}

function deepEqual(a, b) {
  if (a === b) return true;
  if (a === null || b === null) return a === b;
  if (typeof a !== typeof b) return false;
  if (typeof a !== "object") return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) return a.length === b.length && a.every((x, i) => deepEqual(x, b[i]));
  const ka = Object.keys(a).sort();
  const kb = Object.keys(b).sort();
  if (ka.length !== kb.length) return false;
  return ka.every((k, i) => k === kb[i] && deepEqual(a[k], b[k]));
}

function canonical(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  const keys = Object.keys(value).sort();
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonical(value[k])).join(",") + "}";
}

export { schema as cellTraceSchema };
