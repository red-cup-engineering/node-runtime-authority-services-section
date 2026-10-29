// iterating-operations-loop — cross-regime composing morphism.
// Controller regime: stable-aperiodic-articulation-cell (platform-level).
// Body composes morphisms across all four regimes; each stage emits a
// witness row tagged with its regime so the composition is auditable.
//
// Per AOP record P = (R, A, D, H, F):
//   stage 1: heartbeat-selection — stable-aperiodic-articulation-cell
//   stage 2: dispatch — scott-continuous-posit-category (κ = ω)
//   stage 3: mode-application — transfinite-predication-category (ω < κ < ω₁)
//   stage 4: tick — finite-settlement-algebra (κ < ω)
//   stage 5: cost-tracking — finite-settlement-algebra (κ < ω)

import dispatch from "#script/dispatch";
import tick from "#script/tick";
import heartbeat from "#script/heartbeat";

/**
 * One turn through the operations loop.
 *
 * @param {{slug: string, heartbeatState?: {cycle: number, lastTickedEntity?: string}}} operationsLoop
 * @param {Array<{slug: string, skills: string[]}>} agentSet
 * @param {{id: string, requiredSkill: string} | null} workItem
 * @param {Array<{name: string, apply: (e: object) => object}>} closureRules
 * @param {object | null} mode  optional predicating-regime restriction
 * @returns {{operationsLoop: object, witnessRows: object[]}}
 */
export default function iteratingOperationsLoop(
  operationsLoop,
  agentSet,
  workItem,
  closureRules,
  mode = null
) {
  if (!operationsLoop || !operationsLoop.slug) {
    throw new Error("iterating-operations-loop: operationsLoop must have slug");
  }
  if (!Array.isArray(agentSet) || agentSet.length === 0) {
    throw new Error("iterating-operations-loop: agentSet must be non-empty array");
  }
  if (!Array.isArray(closureRules)) {
    throw new Error("iterating-operations-loop: closureRules must be an array");
  }

  const witnessRows = [];

  // Stage 1 — heartbeat-selection (stable-aperiodic-articulation-cell)
  const inState = operationsLoop.heartbeatState ?? { cycle: 0 };
  const nextHeartbeat = heartbeat(inState, agentSet);
  witnessRows.push({
    stage: "heartbeat-selection",
    regime: "stable-aperiodic-articulation-cell",
    selectedEntity: nextHeartbeat.lastTickedEntity,
    cycle: nextHeartbeat.cycle
  });

  // Stage 2 — dispatch (scott-continuous-posit-category)
  let assignedAgent = null;
  if (workItem) {
    const decision = dispatch(agentSet, workItem);
    witnessRows.push({
      stage: "dispatch",
      regime: "scott-continuous-posit-category",
      decision
    });
    if (decision.kind === "assignment") {
      assignedAgent = agentSet.find((a) => a.slug === decision.assignedTo);
    }
  }

  // Stage 3 — mode-application (transfinite-predication-category)
  // Mode narrows the rule-set the closure can apply.
  let activeRules = closureRules;
  if (mode && Array.isArray(mode.narrows)) {
    activeRules = closureRules.filter((r) => !mode.narrows.includes(r.name));
    witnessRows.push({
      stage: "mode-application",
      regime: "transfinite-predication-category",
      mode: mode.slug,
      narrowedRules: mode.narrows,
      remainingRuleCount: activeRules.length
    });
  }

  // Stage 4 — tick (finite-settlement-algebra)
  const target = assignedAgent ?? agentSet.find((a) => a.slug === nextHeartbeat.lastTickedEntity);
  const tickResult = tick(target, activeRules);
  witnessRows.push({
    stage: "tick",
    regime: "finite-settlement-algebra",
    targetEntity: target.slug,
    ruleFired: tickResult.ruleFired ?? null,
    fixedPoint: tickResult.fixedPoint
  });

  // Stage 5 — cost-tracking (finite-settlement-algebra)
  // Single-unit cost per turn; quantale composition handled by composing-cost
  // when costs accumulate across turns.
  witnessRows.push({
    stage: "cost-tracking",
    regime: "finite-settlement-algebra",
    units: 1,
    chargedTo: target.slug
  });

  return {
    operationsLoop: {
      ...operationsLoop,
      heartbeatState: nextHeartbeat,
      lastTurnTarget: target.slug,
      lastTurnFixedPoint: tickResult.fixedPoint
    },
    witnessRows
  };
}
