// dispatch: (agents, work-item) → assignment | unmatched
// Reads each agent's capability predications (skills array), finds those whose
// skills contain work-item.requiredSkill, picks the first match. Per
// lab/.../predicated-agentic-orchestration-platform/dispatch/ and platform-opener.

/**
 * @param {Array<{slug: string, skills: string[]}>} agents
 * @param {{id: string, requiredSkill: string}} workItem
 * @returns {{kind: "assignment", assignedTo: string, matchStrength: "true"|"top"} | {kind: "unmatched", reason: string}}
 */
export default function dispatch(agents, workItem) {
  if (!Array.isArray(agents)) {
    throw new Error("dispatch: agents must be an array");
  }
  if (!workItem || typeof workItem.requiredSkill !== "string") {
    throw new Error("dispatch: workItem must have requiredSkill string");
  }
  const matches = agents.filter(
    (a) => Array.isArray(a.skills) && a.skills.includes(workItem.requiredSkill)
  );
  if (matches.length === 0) {
    return {
      kind: "unmatched",
      reason: `no agent has skill "${workItem.requiredSkill}"`
    };
  }
  return {
    kind: "assignment",
    assignedTo: matches[0].slug,
    matchStrength: matches.length === 1 ? "true" : "top"
  };
}
