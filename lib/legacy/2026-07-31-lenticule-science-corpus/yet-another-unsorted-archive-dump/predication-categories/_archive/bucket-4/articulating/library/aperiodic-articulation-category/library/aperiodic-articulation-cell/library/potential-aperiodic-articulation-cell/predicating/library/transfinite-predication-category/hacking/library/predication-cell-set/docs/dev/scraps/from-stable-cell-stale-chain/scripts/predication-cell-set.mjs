import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../..");

const cellSetSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library/predication-cell-set/predication-cell-set.schema.json"), "utf8"),
);
const entitySetSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library/entity-set/entity-set.schema.json"), "utf8"),
);
const predicateSetSchema = JSON.parse(
  readFileSync(
    resolve(
      REPO_ROOT,
      "library/object/library/thing/library/category/library/predicate-category/library/predicate-set/predicate-set.schema.json",
    ),
    "utf8",
  ),
);

const ajv = new Ajv2020({ allErrors: true, strict: false });
ajv.addSchema(cellSetSchema, cellSetSchema.$id);
ajv.addSchema(entitySetSchema, entitySetSchema.$id);
ajv.addSchema(predicateSetSchema, predicateSetSchema.$id);
const validate = ajv.compile(cellSetSchema);

/**
 * Construct and validate a predication-cell-set Φ = E × Π × E.
 *
 * The set is stored as its two generators (an entity-set and a
 * predicate-set) together with the cached cardinality |E|² × |Π|. The
 * Cartesian product is enumerated on demand by `enumerate()`, not stored
 * as a flat list — the cardinality grows quadratically in |E|.
 *
 * @param {{entity-set: object, predicate-set: object, cardinality?: number}} input
 */
export default function predicationCellSet(input) {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("predication-cell-set: input must be an object");
  }
  const E = input["entity-set"];
  const Pi = input["predicate-set"];
  if (!E || !Pi) {
    throw new TypeError("predication-cell-set: input must carry entity-set and predicate-set");
  }
  const cardinality = (E.entities?.length ?? 0) ** 2 * (Pi.predicates?.length ?? 0);
  const set = {
    "entity-set": E,
    "predicate-set": Pi,
    cardinality,
  };
  if (input.cardinality !== undefined && input.cardinality !== cardinality) {
    throw new RangeError(
      `predication-cell-set: cached cardinality ${input.cardinality} disagrees with computed ${cardinality}`,
    );
  }
  if (!validate(set)) {
    throw new TypeError(
      `predication-cell-set: schema violation: ${ajv.errorsText(validate.errors)}`,
    );
  }
  return set;
}

/**
 * Enumerate the Cartesian product E × Π × E as predication-cells.
 *
 * Yields one cell per (s, p, o) triple. Order: (s outer, p middle, o
 * inner) over the entity- and predicate-set arrays in their declared
 * order. For finite sets this terminates in |E|² × |Π| steps.
 *
 * @param {object} set a validated predication-cell-set
 * @returns {Generator<{subject: string, predicate: string, object: string}>}
 */
export function* enumerate(set) {
  const entities = set["entity-set"]?.entities ?? [];
  const predicates = set["predicate-set"]?.predicates ?? [];
  for (const s of entities) {
    for (const p of predicates) {
      for (const o of entities) {
        yield { subject: s, predicate: p, object: o };
      }
    }
  }
}

export { cellSetSchema as predicationCellSetSchema };
