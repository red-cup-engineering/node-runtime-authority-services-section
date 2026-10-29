import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../../../../../../");

const predicationCellSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library/predication-cell-set/library/predication-cell/predication-cell.schema.json"), "utf8"),
);
const bilatticeValueSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library/lattice/library/twist-product/library/bilattice-value/bilattice-value.schema.json"), "utf8"),
);
const bilatticeSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library/object/library/thing/library/category/library/variety/library/bilattice/bilattice.schema.json"), "utf8"),
);
const fourBilatticeSchema = JSON.parse(
  readFileSync(
    resolve(REPO_ROOT, "library/object/library/thing/library/category/library/variety/library/bilattice/library/four-bilattice/four-bilattice.schema.json"),
    "utf8",
  ),
);
const cellRecordSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library/predication-cell-set/library/predication-cell/library/cell-record/cell-record.schema.json"), "utf8"),
);
const cellIdSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library/predication-cell-set/library/predication-cell/library/cell-record/library/cell-id/cell-id.schema.json"), "utf8"),
);

const ajv = new Ajv2020({ allErrors: true, strict: false });
ajv.addSchema(predicationCellSchema, predicationCellSchema.$id);
ajv.addSchema(bilatticeValueSchema, bilatticeValueSchema.$id);
ajv.addSchema(bilatticeSchema, bilatticeSchema.$id);
ajv.addSchema(fourBilatticeSchema, fourBilatticeSchema.$id);
ajv.addSchema(cellRecordSchema, cellRecordSchema.$id);
ajv.addSchema(cellIdSchema, cellIdSchema.$id);

const validateCell = ajv.compile(predicationCellSchema);
const validateRecord = ajv.compile(cellRecordSchema);

const FOUR = {
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
  negating:   { t: "f", f: "t", bot: "bot", top: "top" },
  conflating: { t: "t", f: "f", bot: "top", top: "bot" },
};

export default async function predicating(input) {
  const cell = input && input.cell ? input.cell : input;

  if (!validateCell(cell)) {
    throw new TypeError(
      `predicating: input cell violates predication-cell schema: ${ajv.errorsText(validateCell.errors)}`,
    );
  }

  const value =
    input && input.value
      ? input.value
      : { bilattice: FOUR, value: "t" };

  const t = (input && input.t) || new Date().toISOString();

  const record = {
    cell: { subject: cell.subject, predicate: cell.predicate, object: cell.object },
    value,
    t,
  };

  if (input && input.stratum) record.stratum = input.stratum;
  if (input && input["derived-from"]) record["derived-from"] = input["derived-from"];
  if (input && input["derived-via"]) record["derived-via"] = input["derived-via"];

  if (!validateRecord(record)) {
    throw new TypeError(
      `predicating: output cell-record violates schema: ${ajv.errorsText(validateRecord.errors)}`,
    );
  }

  return record;
}
