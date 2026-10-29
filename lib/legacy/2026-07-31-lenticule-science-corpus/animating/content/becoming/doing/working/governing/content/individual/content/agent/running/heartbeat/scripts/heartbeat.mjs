// heartbeat: (state, entitySet) → next-state
// Per-entity scheduler. Picks the next entity in round-robin order and reports
// the new state. Real tick application is delegated to caller (which composes
// with tick/). Per lab/.../predicated-agentic-orchestration-platform/heartbeat/.

/**
 * @param {{cycle: number, lastTickedEntity?: string}} state
 * @param {Array<{slug: string}>} entitySet
 * @returns {{cycle: number, lastTickedEntity: string}}
 */
export default function heartbeat(state, entitySet) {
  if (!state || typeof state.cycle !== "number") {
    throw new Error("heartbeat: state must have integer cycle");
  }
  if (!Array.isArray(entitySet) || entitySet.length === 0) {
    throw new Error("heartbeat: entitySet must be non-empty array");
  }
  const lastIdx = state.lastTickedEntity
    ? entitySet.findIndex((e) => e.slug === state.lastTickedEntity)
    : -1;
  const nextIdx = (lastIdx + 1) % entitySet.length;
  const nextEntity = entitySet[nextIdx];
  // Cycle increments only on wrap-around: lastIdx was the final element AND we
  // came back to index 0. First visit (lastIdx === -1) doesn't increment.
  const wrapped = lastIdx === entitySet.length - 1 && nextIdx === 0;
  return {
    cycle: wrapped ? state.cycle + 1 : state.cycle,
    lastTickedEntity: nextEntity.slug
  };
}
