// responding — cross-regime orchestrator: user-prompt → SMD.
// Controller regime: stable-aperiodic-articulation-cell.
//
// The substrate's perceive-think-act cycle (per emsenn 2026-05-28 reframe,
// substrate-as-AI):
//
//   PERCEIVE  — receive the user-prompt
//   RECALL    — derive relevance-frontier (predicating; LLM as entity classifier)
//   PROJECT   — render relevant cells as HTML SHPs (positing)
//   DELIBERATE— ask LLM in natural language using the SHP context (articulating)
//   WRAP      — wrap LLM response as llm-model cell
//   REPORT    — reduce {prompt, llm-model, context} → SMD (settling)
//
// Each stage emits a witness row tagged with its regime. The missingKnowledge
// path: if recall produces no matched entities, the orchestrator records the
// signal in witness + output (downstream / next-turn consumers can invoke
// minting-thing to acquire the new entity).

import derivingRelevanceFrontier from "#script/deriving-relevance-frontier";
import projectingKnowledgeToShps from "#script/projecting-knowledge-to-shps";
import renderingSpacesuitToShp from "#script/rendering-spacesuit-to-shp";
import inferring from "#script/inferring";
import reducingToSmd from "#script/reducing-to-smd";

export default async function responding(userPrompt, knowledgeRegion, options = {}) {
  if (!userPrompt?.utterance) {
    throw new Error("responding: userPrompt.utterance required");
  }
  if (!Array.isArray(knowledgeRegion)) {
    throw new Error("responding: knowledgeRegion must be an array");
  }
  const endpointId = options.endpointId ?? "endpoint:groq";
  const witnessRows = [];

  // Stage 1 — PERCEIVE
  witnessRows.push({
    stage: "perceive",
    regime: "stable-aperiodic-articulation-cell",
    enactor: userPrompt.enactor,
    questionPreview: (userPrompt.utterance?.[1] ?? "").slice(0, 80)
  });

  // Stage 2 — RECALL (predicating-regime; deriving-relevance-frontier)
  const relevanceFrontier = await derivingRelevanceFrontier(userPrompt, knowledgeRegion, {
    endpointId,
    fetchImpl: options.fetchImpl,
    model: options.model
  });
  witnessRows.push({
    stage: "recall",
    regime: "transfinite-predication-category",
    matchedCount: relevanceFrontier.matchedEntities.length,
    neighborhoodSize: relevanceFrontier.neighborhood.length,
    missingKnowledge: relevanceFrontier.missingKnowledge
  });

  // Stage 3 — PROJECT (positing-regime; cells → HTML SHPs)
  const shps = projectingKnowledgeToShps(relevanceFrontier.neighborhood);
  witnessRows.push({
    stage: "project-to-shps",
    regime: "scott-continuous-posit-category",
    shpCount: shps.length
  });

  // Stage 4 — DELIBERATE (articulating-regime; LLM call with SHPs as context)
  // Even when missingKnowledge is true, we still try to answer — the LLM may
  // help articulate what the user is asking about, which informs minting.
  // If a context-spacesuit was supplied for the executor agent, render it
  // to HTML and prepend as working-memory context.
  let llmModel = null;
  if (!options.skipInferring) {
    const userQuestion = userPrompt.utterance[1];
    const spacesuitShp = options.executorSpacesuit
      ? renderingSpacesuitToShp(options.executorSpacesuit) + "\n"
      : "";
    const promptHtml = spacesuitShp + (
      shps.length > 0
        ? `${shps.join("\n")}\n<p class="user-question">${escapeHtml(userQuestion)}</p>`
        : `<p class="user-question">${escapeHtml(userQuestion)}</p><p class="note">No matching entities in current knowledge.</p>`
    );
    llmModel = await inferring([userPrompt.utterance[0], promptHtml], {
      endpointId,
      model: options.model,
      fetchImpl: options.fetchImpl
    });
    witnessRows.push({
      stage: "deliberate",
      regime: "aperiodic-articulation-category",
      endpoint: llmModel.endpoint,
      model: llmModel.model,
      shpsProvidedAsContext: shps.length,
      spacesuitLoaded: options.executorSpacesuit?.slug ?? null
    });

    // Stage 5 — WRAP (the llm-model object IS the substrate's wrapping)
    witnessRows.push({
      stage: "wrap-response",
      regime: "aperiodic-articulation-category",
      completionLength: llmModel.completion.length
    });
  }

  // Stage 6 — REPORT (settling-regime; reduce to SMD)
  const smd = reducingToSmd({
    userPrompt,
    llmModels: llmModel ? [llmModel] : [],
    contextCells: relevanceFrontier.neighborhood,
    slug: options.smdSlug
  });
  witnessRows.push({
    stage: "report",
    regime: "finite-settlement-algebra",
    smdSlug: smd.slug,
    sourceRefs: smd.sourceRefs.length
  });

  return {
    smd,
    relevanceFrontier,
    llmModel,
    missingKnowledge: relevanceFrontier.missingKnowledge,
    witnessRows,
    evidence: [
      "responding: cross-regime perceive-think-act cycle",
      `Stages: ${witnessRows.map((w) => w.stage).join(" → ")}`,
      `Distinct regimes traversed: ${new Set(witnessRows.map((w) => w.regime)).size}`
    ]
  };
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
