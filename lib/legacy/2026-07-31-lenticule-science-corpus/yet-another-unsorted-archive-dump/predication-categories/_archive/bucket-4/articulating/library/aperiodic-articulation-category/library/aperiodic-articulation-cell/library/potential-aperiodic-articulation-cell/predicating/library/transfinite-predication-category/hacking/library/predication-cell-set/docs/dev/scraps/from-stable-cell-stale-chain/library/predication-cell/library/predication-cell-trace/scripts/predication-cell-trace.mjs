import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../../../../..");

const schema = JSON.parse(
  readFileSync(resolve(__dirname, "../predication-cell-trace.schema.json"), "utf8"),
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

const ajv = new Ajv2020({ allErrors: true, strict: false });
ajv.addSchema(predicationCellSchema, predicationCellSchema.$id);
ajv.addSchema(bilatticeValueSchema, bilatticeValueSchema.$id);
ajv.addSchema(bilatticeSchema, bilatticeSchema.$id);
const validate = ajv.compile(schema);

/**
 * Construct and validate a predication-cell-trace.
 *
 * Enforces the Theory of Predication-Cell-Trace beyond schema shape:
 *   (Axiom 1) all trajectory entries share the same bilattice context — a
 *     trace is a chain in one fiber algebra A_p, not a hop across fibers.
 *   (Axiom 2) the trajectory is ≤_k-monotone in that shared bilattice —
 *     settling-monotonicity (concepts/settling-monotonicity.md) slices to
 *     chain-monotonicity at any fixed cell, by knowledge-order pointwise.
 *
 * Both axioms are decided using only the bilattice's own algebraic data: the
 * `knowledge-meet` table the bilattice schema requires.
 */
export default function predicationCellTrace(input) {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("predication-cell-trace: input must be an object");
  }
  if (!validate(input)) {
    throw new TypeError(
      `predication-cell-trace: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  const { trajectory } = input;
  if (trajectory.length > 1) {
    const ctx = trajectory[0].bilattice;
    for (let i = 1; i < trajectory.length; i += 1) {
      if (!sameBilattice(trajectory[i].bilattice, ctx)) {
        throw new TypeError(
          `predication-cell-trace: trajectory[${i}].bilattice differs from trajectory[0].bilattice; a trace is a chain in one fiber`,
        );
      }
    }
    for (let i = 0; i < trajectory.length - 1; i += 1) {
      const a = trajectory[i].value;
      const b = trajectory[i + 1].value;
      if (!leqKnowledge(ctx, a, b)) {
        throw new TypeError(
          `predication-cell-trace: ≤_k-monotonicity violated at step ${i}→${i + 1}: ${a} not ≤_k ${b}`,
        );
      }
    }
  }
  return { cell: input.cell, trajectory: input.trajectory };
}

export function validatePredicationCellTrace(trace) {
  predicationCellTrace(trace);
  return true;
}

function leqKnowledge(B, a, b) {
  const row = B["knowledge-meet"][a];
  if (row === undefined || row[b] === undefined) {
    throw new RangeError(
      `predication-cell-trace: bilattice's knowledge-meet table missing entry (${a}, ${b})`,
    );
  }
  return row[b] === a;
}

function sameBilattice(a, b) {
  return canonical(a) === canonical(b);
}

function canonical(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  const keys = Object.keys(value).sort();
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonical(value[k])).join(",") + "}";
}

export { schema as predicationCellTraceSchema };
