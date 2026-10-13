import {
  SEN_JSON,
  isRelationalTerm,
  parseSen,
} from "@red-cup-engineering/computer-code-engineering-services-section/semiotic-expression-notation/reader";
import {                 restrict } from "@red-cup-engineering/computer-content-engineering-services-section/typed-resource-classification";
import { jsonProjector } from "@red-cup-engineering/computer-content-engineering-services-section/json-projector";

export {
  SEN_JSON,
  extractRelationalScripts,
  htmlIsRelational,
  isRelationalTerm,
  parseSen,
  sessionIsRelational,
  settleRelationalHtml,
  settleRelationalSession,
  settleSen,
} from "@red-cup-engineering/computer-code-engineering-services-section/semiotic-expression-notation/reader";

/** A representation read admits finite, closed, well-typed SEN syntax. Its
 * strict rung describes this parser/type-checker, not evaluation or the
 * semantic closure regime of the carried program. read/write never settle a
 * term: a redex crosses this boundary unchanged. Resource exhaustion may still
 * refuse admission; this grading promises no uniform time or memory bound. */
export const senProjector                       = restrict(jsonProjector, {
  type: "sen",
  corner: "assertion",
  rung: "strict",
  recognize: (resource) => {
    try {
      return isRelationalTerm(JSON.parse(resource.content));
    } catch {
      return false;
    }
  },
  read: (resource) => [parseSen(resource.content)],
  write: (items) => {
    const document = jsonProjector.write(items);
    if (items.length !== 0) parseSen(document);
    return document;
  },
});
