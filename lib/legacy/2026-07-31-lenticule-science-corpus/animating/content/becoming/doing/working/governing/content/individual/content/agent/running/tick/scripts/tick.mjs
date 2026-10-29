// tick: (entity, closure-rules) → entity'
// One closure-step on one entity per lab/.../predicated-agentic-orchestration-platform/tick/.
// For minimum-viable, applies a single rule (identity if no rule fires) and reports
// whether fixed-point has been reached. Real closure-rule registry comes later.

/**
 * @param {object} entity
 * @param {Array<{name: string, apply: (e: object) => object}>} closureRules
 * @returns {{outputEntity: object, ruleFired?: string, fixedPoint: boolean}}
 */
export default function tick(entity, closureRules) {
  if (entity == null || typeof entity !== "object") {
    throw new Error("tick: entity must be an object");
  }
  if (!Array.isArray(closureRules)) {
    throw new Error("tick: closureRules must be an array");
  }
  let current = entity;
  for (const rule of closureRules) {
    if (typeof rule?.apply !== "function") continue;
    const next = rule.apply(current);
    if (JSON.stringify(next) !== JSON.stringify(current)) {
      return { outputEntity: next, ruleFired: rule.name, fixedPoint: false };
    }
  }
  return { outputEntity: current, fixedPoint: true };
}
