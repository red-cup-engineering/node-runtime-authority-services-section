// deriving-relevance-frontier — predicating-regime fiber selection.
// Regime: transfinite-predication-category; ω < κ < ω₁.
//
// Per emsenn 2026-05-28 reframe (substrate-as-AI; LLMs as dictionaries):
// this morphism IS the AI's recall act — the substrate consults an LLM to
// identify which of ITS OWN known entities the user-prompt is asking about.
// The LLM is a pattern matcher; the entities live in the substrate.
//
// Mechanism:
//   1. Extract known entity slugs from the knowledge-region (subjects of
//      settled cells).
//   2. Render an HTML prompt presenting the entity list + the user-prompt.
//   3. Call inferring (the LLM is being used here as an external recognizer).
//   4. Extract matches by substring-checking known entity slugs against the
//      LLM's untrusted text response. We do NOT trust the LLM's structure —
//      we validate against our known set.
//   5. Build the relevance-frontier object with matches + neighborhood +
//      missingKnowledge signal.
//
// missingKnowledge: true means the substrate doesn't have an entity for what
// the user is asking about. The orchestrator (responding) decides whether
// to mint a new entity via the agential-self-generation pathway.

import inferring from "#script/inferring";

function knownEntitiesFromRegion(knowledgeRegion) {
  // Subjects (and objects, since they may appear as subjects in other cells)
  // of settled cells. De-duped.
  const set = new Set();
  for (const cell of knowledgeRegion) {
    if (cell?.subject) set.add(cell.subject);
    if (cell?.object) set.add(cell.object);
  }
  return [...set];
}

function renderEntityListHtml(entities) {
  const items = entities.map((e) => `<li data-entity="${escapeHtml(e)}">${escapeHtml(e)}</li>`).join("");
  return `<article class="known-entities"><ul>${items}</ul></article>`;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function neighborhoodFor(knowledgeRegion, entities) {
  // Cells where any of the matched entities appears as subject or object.
  const set = new Set(entities);
  return knowledgeRegion.filter((c) => set.has(c.subject) || set.has(c.object));
}

function extractMatches(llmResponseText, knownEntities) {
  // Permissive extraction with a sentinel short-circuit:
  //   1. If the LLM emitted the explicit "NONE" sentinel as a standalone
  //      word, honor it — that's the LLM telling us no known entity applies.
  //   2. Otherwise, any known entity slug appearing as a substring in the
  //      response counts as a match. We only trust slugs in our known set;
  //      hallucinated entities outside the set are filtered automatically.
  if (/\bNONE\b/.test(llmResponseText)) return [];
  return knownEntities.filter((e) => llmResponseText.includes(e));
}

/**
 * @param {object} userPrompt  user-prompt object (from prompting morphism)
 * @param {Array<{subject,predicate,object,value,settled}>} knowledgeRegion  settled cells
 * @param {{endpointId?: string, fetchImpl?: any, model?: string}} options
 * @returns {Promise<{matchedEntities: string[], neighborhood: object[], missingKnowledge: boolean, derivedFrom: object, derivedAt: string, evidence: string[]}>}
 */
export default async function derivingRelevanceFrontier(userPrompt, knowledgeRegion, options = {}) {
  if (!userPrompt?.utterance) {
    throw new Error("deriving-relevance-frontier: userPrompt.utterance required");
  }
  if (!Array.isArray(knowledgeRegion)) {
    throw new Error("deriving-relevance-frontier: knowledgeRegion must be an array");
  }
  const endpointId = options.endpointId ?? "endpoint:groq";

  const knownEntities = knownEntitiesFromRegion(knowledgeRegion);

  if (knownEntities.length === 0) {
    // The substrate is empty — any prompt is about missing knowledge.
    return {
      matchedEntities: [],
      neighborhood: [],
      missingKnowledge: true,
      derivedFrom: {
        userPromptRef: userPrompt.utterance[0],
        llmModelRef: "skipped:empty-substrate",
        knownEntityCount: 0
      },
      derivedAt: new Date().toISOString(),
      evidence: [
        "deriving-relevance-frontier: no known entities; missingKnowledge",
        "Regime: transfinite-predication-category (predicating-regime fiber selection)"
      ]
    };
  }

  const userQuestion = userPrompt.utterance[1];
  const entityListHtml = renderEntityListHtml(knownEntities);
  const promptHtml = [
    entityListHtml,
    `<p class="user-question">${escapeHtml(userQuestion)}</p>`,
    `<p class="instruction">Which of the entities listed above is the user-question about? List ALL relevant entity slugs (the data-entity values) inline in your answer. If none of the entities apply, write the single word NONE.</p>`
  ].join("");

  const llmModel = await inferring([userPrompt.utterance[0], promptHtml], {
    endpointId,
    model: options.model,
    fetchImpl: options.fetchImpl
  });

  const responseText = llmModel.completion;
  const matched = extractMatches(responseText, knownEntities);
  const missingKnowledge = matched.length === 0;
  const neighborhood = matched.length > 0 ? neighborhoodFor(knowledgeRegion, matched) : [];

  return {
    matchedEntities: matched,
    neighborhood,
    missingKnowledge,
    derivedFrom: {
      userPromptRef: userPrompt.utterance[0],
      llmModelRef: `${llmModel.endpoint}::${llmModel.model}@${llmModel.transactionTime}`,
      knownEntityCount: knownEntities.length
    },
    derivedAt: new Date().toISOString(),
    evidence: [
      "deriving-relevance-frontier: LLM-as-recognizer over substrate's known entities",
      `Regime: transfinite-predication-category; ${matched.length}/${knownEntities.length} matched; missingKnowledge=${missingKnowledge}`
    ]
  };
}
