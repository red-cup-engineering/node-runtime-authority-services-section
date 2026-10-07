import {
  SEN_JSON,
  isRelationalTerm,
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

export const senProjector                       = restrict(jsonProjector, {
  type: "sen",
  corner: "assertion",
  rung: "scott",
  recognize: (resource) => {
    try {
      return isRelationalTerm(JSON.parse(resource.content));
    } catch {
      return false;
    }
  },
});
