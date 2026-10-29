import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../../");

const predicateCategorySchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "predicate-category.schema.json"), "utf8"),
);
const predicateSetSchema = JSON.parse(
  readFileSync(resolve(REPO_ROOT, "library", "predicate-set", "predicate-set.schema.json"), "utf8"),
);

const ajv = new Ajv2020({ allErrors: true, strict: false });
ajv.addSchema(predicateSetSchema, predicateSetSchema.$id);
const validateCategory = ajv.compile(predicateCategorySchema);

export default async function conversingAPredicate(input) {
  if (!input || typeof input !== "object") {
    throw new TypeError("conversing-a-predicate: input must be {predicate-category, source}");
  }
  const category = input["predicate-category"];
  const source = input.source;

  if (!validateCategory(category)) {
    throw new TypeError(
      `conversing-a-predicate: predicate-category violates schema: ${ajv.errorsText(validateCategory.errors)}`,
    );
  }
  if (typeof source !== "string") {
    throw new TypeError("conversing-a-predicate: source must be a kebab-case predicate-slug");
  }
  if (!category.objects.predicates.includes(source)) {
    throw new RangeError(
      `conversing-a-predicate: source ${JSON.stringify(source)} is not an object of the predicate-category`,
    );
  }

  const targets = category.converse
    .filter((m) => m.source === source)
    .map((m) => m.target);

  return { source, class: "converse", targets };
}
