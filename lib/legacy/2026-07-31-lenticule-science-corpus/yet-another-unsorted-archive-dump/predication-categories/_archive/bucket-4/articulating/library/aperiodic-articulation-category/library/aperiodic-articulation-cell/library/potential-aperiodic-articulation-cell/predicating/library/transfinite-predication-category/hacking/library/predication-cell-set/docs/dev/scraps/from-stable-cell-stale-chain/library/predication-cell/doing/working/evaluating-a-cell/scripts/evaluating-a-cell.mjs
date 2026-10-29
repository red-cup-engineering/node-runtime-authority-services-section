import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../../");

const predicationCellSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "predication-cell.schema.json"), "utf8"),
);
const predicationValuationSchema = JSON.parse(
  readFileSync(
    resolve(
      REPO_ROOT,
      "../../../predication-settling-category/library/predication-settling/library/predication-valuation/predication-valuation.schema.json",
    ),
    "utf8",
  ),
);
const predicationFiberAlgebraSchema = JSON.parse(
  readFileSync(
    resolve(
      REPO_ROOT,
      "../../../predication-fibration/library/predication-fiber-algebra/predication-fiber-algebra.schema.json",
    ),
    "utf8",
  ),
);
const predicateCategorySchema = JSON.parse(
  readFileSync(
    resolve(
      REPO_ROOT,
      "../../../object/library/thing/library/category/library/predicate-category/predicate-category.schema.json",
    ),
    "utf8",
  ),
);
const predicateSetSchema = JSON.parse(
  readFileSync(
    resolve(
      REPO_ROOT,
      "../../../object/library/thing/library/category/library/predicate-category/library/predicate-set/predicate-set.schema.json",
    ),
    "utf8",
  ),
);
const entitySetSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "../../../entity-set/entity-set.schema.json"), "utf8"),
);
const residuatedLatticeSchema = JSON.parse(
  readFileSync(
    resolve(REPO_ROOT, "../../../lattice/library/residuated-lattice/residuated-lattice.schema.json"),
    "utf8",
  ),
);
const bilatticeValueSchema = JSON.parse(
  readFileSync(
    resolve(
      REPO_ROOT,
      "../../../lattice/library/twist-product/library/bilattice-value/bilattice-value.schema.json",
    ),
    "utf8",
  ),
);
const bilatticeSchema = JSON.parse(
  readFileSync(
    resolve(
      REPO_ROOT,
      "../../../object/library/thing/library/category/library/variety/library/bilattice/bilattice.schema.json",
    ),
    "utf8",
  ),
);

const ajv = new Ajv2020({ allErrors: true, strict: false });
[
  predicationCellSchema,
  predicateCategorySchema,
  predicateSetSchema,
  entitySetSchema,
  residuatedLatticeSchema,
  predicationFiberAlgebraSchema,
  predicationValuationSchema,
  bilatticeSchema,
  bilatticeValueSchema,
].forEach((s) => ajv.addSchema(s, s.$id));

const validateCell = ajv.compile(predicationCellSchema);
const validateValuation = ajv.compile(predicationValuationSchema);

export default async function evaluatingACell(input) {
  if (!input || typeof input !== "object") {
    throw new TypeError("evaluating-a-cell: input must be {cell, valuation}");
  }
  const { cell, valuation } = input;

  if (!validateCell(cell)) {
    throw new TypeError(
      `evaluating-a-cell: cell violates predication-cell schema: ${ajv.errorsText(validateCell.errors)}`,
    );
  }
  if (!validateValuation(valuation)) {
    throw new TypeError(
      `evaluating-a-cell: valuation violates predication-valuation schema: ${ajv.errorsText(validateValuation.errors)}`,
    );
  }

  const fiber = valuation["fiber-algebras"][cell.predicate];
  if (!fiber) {
    throw new RangeError(
      `evaluating-a-cell: valuation has no fiber-algebra for predicate ${JSON.stringify(cell.predicate)}`,
    );
  }

  const key = `${cell.subject}:${cell.object}`;
  const pair = fiber.assignments[key];

  // Knowledge-bottom default ⊥ = ⟨0, 0⟩. Identify it via lattice.bottom.
  const lattice = fiber.lattice;
  const bottomElem = lattice.bottom ?? lattice.carrier[0];
  const twistPair = pair ?? { pos: bottomElem, neg: bottomElem };

  // Encode the twist-product element as a bilattice-value over FOUR-like packaging:
  // the value field is the (pos, neg) pair stringified, and the bilattice context is
  // the carrier-and-tables from the underlying residuated lattice's twist product.
  // For the FOUR special case (L = 2), map ⟨pos, neg⟩ to {t, f, bot, top}.
  let bilatticeValueOutput;
  if (
    lattice.carrier.length === 2 &&
    lattice.carrier.includes("0") &&
    lattice.carrier.includes("1")
  ) {
    const pos = twistPair.pos;
    const neg = twistPair.neg;
    let v;
    if (pos === "1" && neg === "0") v = "t";
    else if (pos === "0" && neg === "1") v = "f";
    else if (pos === "0" && neg === "0") v = "bot";
    else if (pos === "1" && neg === "1") v = "top";
    else throw new RangeError(`evaluating-a-cell: twist pair ⟨${pos}, ${neg}⟩ not in 2^⋈`);
    bilatticeValueOutput = { bilattice: fourBilattice(), value: v };
  } else {
    // General twist-product encoding: pos and neg as separate fields; the caller
    // performs the carrier-arithmetic with the underlying residuated lattice.
    bilatticeValueOutput = {
      bilattice: { carrier: lattice.carrier, twist: true },
      value: `${twistPair.pos}|${twistPair.neg}`,
    };
  }

  return { cell, value: bilatticeValueOutput };
}

function fourBilattice() {
  return {
    carrier: ["t", "f", "bot", "top"],
    "truth-meet": {
      t:   { t: "t",   f: "f",   bot: "bot", top: "top" },
      f:   { t: "f",   f: "f",   bot: "f",   top: "f"   },
      bot: { t: "bot", f: "f",   bot: "bot", top: "f"   },
      top: { t: "top", f: "f",   bot: "f",   top: "top" },
    },
    "truth-join": {
      t:   { t: "t",   f: "t",   bot: "t",   top: "t"   },
      f:   { t: "t",   f: "f",   bot: "bot", top: "top" },
      bot: { t: "t",   f: "bot", bot: "bot", top: "t"   },
      top: { t: "t",   f: "top", bot: "t",   top: "top" },
    },
    "knowledge-meet": {
      t:   { t: "t",   f: "bot", bot: "bot", top: "t"   },
      f:   { t: "bot", f: "f",   bot: "bot", top: "f"   },
      bot: { t: "bot", f: "bot", bot: "bot", top: "bot" },
      top: { t: "t",   f: "f",   bot: "bot", top: "top" },
    },
    "knowledge-join": {
      t:   { t: "t",   f: "top", bot: "t",   top: "top" },
      f:   { t: "top", f: "f",   bot: "f",   top: "top" },
      bot: { t: "t",   f: "f",   bot: "bot", top: "top" },
      top: { t: "top", f: "top", bot: "top", top: "top" },
    },
    negating: { t: "f", f: "t", bot: "bot", top: "top" },
    conflating: { t: "t", f: "f", bot: "top", top: "bot" },
  };
}
