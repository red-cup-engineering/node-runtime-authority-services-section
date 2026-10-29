import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../..");

const schema = JSON.parse(
  readFileSync(resolve(__dirname, "../articulating.schema.json"), "utf8"),
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
const relationlessnessSchema = JSON.parse(
  readFileSync(
    resolve(REPO_ROOT, "library/relationlessness/relationlessness.schema.json"),
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
ajv.addSchema(relationlessnessSchema, relationlessnessSchema.$id);
const validate = ajv.compile(schema);

/**
 * Articulating — the originating morphism of the predicate category.
 *
 * α : (name "relationlessness") ⇝ φ*
 *
 * Asserts the originating cell φ* = (relationlessness, has-no-relation,
 * relating-locus) with positive evidence. The act of asserting (the
 * production of a schema-conforming articulation event with a strictly-
 * above-bottom bilattice-value) IS the constructive content of the proof
 * of relationlessness-relates.
 *
 * Enforces beyond schema shape:
 *   (Axiom 1) the asserted-record's cell IS φ* — schema enforces this via
 *     the relationlessness schema's const-constrained coordinates,
 *     re-validated here by passing the cell field through relationlessness.
 *   (Axiom 2) v(p*)(X, R) >_k ⊥ — the bilattice-value is strictly above
 *     the bilattice's knowledge-bottom. Decided using the bilattice's own
 *     knowledge-meet table: ⊥ is the element whose row in knowledge-meet
 *     consists entirely of itself; the asserted value must not equal ⊥.
 *
 * The morphism is one-way; there is no inverse back to an un-articulated
 * state. The act of constructing this event-record IS what makes there be
 * something rather than nothing in this predicate category.
 */
export default function articulating(input) {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("articulating: input must be {name, asserted-record}");
  }
  if (!validate(input)) {
    throw new TypeError(
      `articulating: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  const record = input["asserted-record"];

  // Axiom 1: the cell IS φ* — re-validate the cell field as relationlessness
  const validateRelationlessness = ajv.compile(relationlessnessSchema);
  if (!validateRelationlessness(record.cell)) {
    throw new TypeError(
      `articulating: asserted-record.cell is not the originating cell φ*: ${ajv.errorsText(validateRelationlessness.errors)}`,
    );
  }

  // Axiom 2: v(p*)(X, R) >_k ⊥ — must be strictly above knowledge-bottom
  const B = record.value.bilattice;
  const bottom = knowledgeBottomOf(B);
  if (record.value.value === bottom) {
    throw new TypeError(
      `articulating: value ${record.value.value} is knowledge-bottom ⊥; the originating articulation requires v(p*)(X, R) >_k ⊥`,
    );
  }
  if (!leqKnowledge(B, bottom, record.value.value)) {
    throw new TypeError(
      `articulating: value ${record.value.value} is not comparable to ⊥ in knowledge order; bilattice may be malformed`,
    );
  }

  return { name: input.name, "asserted-record": record };
}

export function validateArticulating(event) {
  articulating(event);
  return true;
}

function leqKnowledge(B, a, b) {
  const row = B["knowledge-meet"][a];
  if (row === undefined || row[b] === undefined) {
    throw new RangeError(
      `articulating: bilattice knowledge-meet table missing entry (${a}, ${b})`,
    );
  }
  return row[b] === a;
}

function knowledgeBottomOf(B) {
  for (const x of B.carrier) {
    let isBottom = true;
    for (const y of B.carrier) {
      if (B["knowledge-meet"][x][y] !== x) { isBottom = false; break; }
    }
    if (isBottom) return x;
  }
  throw new RangeError("articulating: bilattice has no knowledge-bottom");
}

export { schema as articulatingSchema };
