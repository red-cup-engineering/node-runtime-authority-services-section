// loading-context-spacesuit — predicating-regime extension morphism.
// Regime: transfinite-predication-category; closure ordinal κ < ω₁.
// Per lab/.../context-spacesuit.md: loading is extension (⊙) — adds the
// suit's fiber to the agent's bare predication-cell.
//
// Domain: (agent, context-spacesuit). Codomain: agent-with-loadedSuit.
// Variance: extension. Monotone in both inputs.

export default function loadingContextSpacesuit(agent, spacesuit) {
  if (!agent || typeof agent !== "object" || !agent.slug) {
    throw new Error("loading-context-spacesuit: agent must be an object with a slug");
  }
  if (!spacesuit || typeof spacesuit !== "object" || !spacesuit.slug) {
    throw new Error("loading-context-spacesuit: spacesuit must be an object with a slug");
  }
  return {
    ...agent,
    loadedSuit: spacesuit.slug
  };
}
