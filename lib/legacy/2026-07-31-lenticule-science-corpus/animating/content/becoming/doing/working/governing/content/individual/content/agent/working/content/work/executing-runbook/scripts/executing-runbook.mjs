// executing-runbook — cross-regime step iterator over a pre-settled runbook.
// Regime: cross-regime composing morphism; effective κ = max(step regimes).
//
// Walks runbook.steps in order, dispatches each step to a handler keyed by
// step.expectedWitness, accumulates witness rows tagged with the step's regime.
// Threads context: output of step n becomes input of step n+1 via state object.
//
// Handlers are kept here (in the executor) rather than per-morphism because each
// runbook's per-step contract is part of the executor's discipline, not the
// individual morphism's. A morphism is reusable across runbooks; how it's wired
// into a particular runbook is the runbook executor's concern.

import inferring from "#script/inferring";
import checkingBudget from "#script/checking-budget";
import trackingCell from "#script/tracking-cell";
import composingCost from "#script/composing-cost";

// Per-morphism handlers. Each takes (state, ctx) and returns
// { state: newState, outcome: "ok"|"error"|"skipped", detail? }
const STEP_HANDLERS = {
  "checking-budget": (state, ctx) => {
    const budget = ctx.budget ?? { boundValue: 100000, currency: "tokens", exhaustionPolicy: "abort" };
    const proposedAmount = ctx.estimatedTokens ?? 200;
    const decision = checkingBudget(budget, state.consumedTokens ?? 0, proposedAmount);
    const ok = decision.status === "available" || decision.status === "downgrade";
    return {
      state: { ...state, budgetCheck: decision },
      outcome: ok ? "ok" : "error",
      detail: { proposedAmount, status: decision.status }
    };
  },

  inferring: async (state, ctx) => {
    const utterance = ctx.utterance ?? [ctx.token ?? `session-${state.executorSlug}`, ctx.prompt];
    const result = await inferring(utterance, {
      endpointId: ctx.endpointId,
      model: ctx.model,
      fetchImpl: ctx.fetchImpl
    });
    return {
      state: { ...state, llmModel: result, completion: result.completion },
      outcome: "ok",
      detail: { endpoint: result.endpoint, model: result.model, completionPreview: result.completion.slice(0, 120) }
    };
  },

  "tracking-cell": async (state, ctx) => {
    // Track the inferring's completion as a settled predication-cell with SPO
    // shape per tracking-cell contract: subject=agent, predicate=articulated,
    // object=completion (truncated to a reasonable identifier).
    if (!state.llmModel) {
      return { state, outcome: "skipped", detail: { reason: "no llm-model in state" } };
    }
    const cell = {
      subject: `agent:${state.executorSlug}`,
      predicate: "articulated-via-inferring",
      object: state.llmModel.completion.slice(0, 200),
      value: "true",
      settled: true
    };
    const trace = ctx.trace ?? { path: ctx.tracePath ?? "(in-memory)", rowIds: [] };
    const result = await trackingCell(trace, cell, state.llmModel.transactionTime);
    return {
      state: { ...state, trackedCell: cell, trace: result.outputTrace },
      outcome: "ok",
      detail: { rowId: result.outputRowId, valueRowId: result.valueRowId }
    };
  },

  "composing-cost": (state, ctx) => {
    // Compose this turn's cost with any prior costs. Free endpoints have
    // dollars=0; we still track settlement-fuel and tokens for the quantale.
    const tokensIn = state.llmModel?.inputUtterance?.[1]?.length ?? 0;
    const tokensOut = state.llmModel?.completion?.length ?? 0;
    const costEvents = [
      ...(state.priorCosts ?? []),
      {
        settlementFuel: ctx.settlementFuel ?? 1,
        dollars: 0,
        tokens: { input: tokensIn, output: tokensOut }
      }
    ];
    const composed = composingCost(costEvents, "serial");
    return {
      state: { ...state, costComposed: composed },
      outcome: "ok",
      detail: composed
    };
  }
};

/**
 * @param {object} runbook  Runbook record with steps[].
 * @param {object} executor Agent record executing the runbook.
 * @param {object} workItem The work-item triggering execution.
 * @param {object} options  Per-runbook context (endpointId, prompt, budget, fetchImpl, etc.).
 * @returns {Promise<{state: object, witnessRows: object[]}>}
 */
export default async function executingRunbook(runbook, executor, workItem, options = {}) {
  if (!runbook?.steps) throw new Error("executing-runbook: runbook.steps required");
  if (!executor?.slug) throw new Error("executing-runbook: executor.slug required");
  if (!workItem) throw new Error("executing-runbook: workItem required");

  let state = {
    runbookSlug: runbook.slug,
    executorSlug: executor.slug,
    workItemId: workItem.id ?? "(no-id)"
  };
  const witnessRows = [];

  const ctx = {
    ...options,
    prompt: workItem.prompt ?? options.prompt,
    endpointId: workItem.endpointId ?? options.endpointId,
    model: workItem.model ?? options.model
  };

  const sortedSteps = [...runbook.steps].sort((a, b) => a.order - b.order);
  for (const step of sortedSteps) {
    const morphism = step.expectedWitness;
    const handler = STEP_HANDLERS[morphism];
    if (!handler) {
      witnessRows.push({
        stepOrder: step.order,
        morphism,
        regime: step.regime ?? "unknown",
        outcome: "skipped",
        detail: { reason: `no handler registered for "${morphism}"` }
      });
      continue;
    }
    try {
      const result = await handler(state, ctx);
      state = result.state;
      witnessRows.push({
        stepOrder: step.order,
        morphism,
        regime: step.regime,
        outcome: result.outcome,
        ...(result.detail ? { detail: result.detail } : {})
      });
      if (result.outcome === "error") break;
    } catch (err) {
      witnessRows.push({
        stepOrder: step.order,
        morphism,
        regime: step.regime,
        outcome: "error",
        detail: { error: err.message }
      });
      break;
    }
  }

  return { state, witnessRows };
}

export { STEP_HANDLERS };
