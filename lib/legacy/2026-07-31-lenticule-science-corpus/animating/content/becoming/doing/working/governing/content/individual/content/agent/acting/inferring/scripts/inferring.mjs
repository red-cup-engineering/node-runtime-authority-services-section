// inferring: prompt × model → utterance
// Variance: restriction of the articulating-class morphism to the LLM-endpoint enactor.
//
// The LLM reply IS an utterance [token, claim] (a real articulation, not a flat record):
//   token (slot 0) = a JSON Schema document carrying the CALL PROVENANCE — originating prompt, endpoint,
//                    model, transaction time. Encoded {const: <provenance>}.
//   claim (slot 1) = a JSON Schema document carrying the REPLY TEXT. Encoded {const: <reply>}.
// So inferring's output composes directly into the descent: articulating(inferring(prompt, model)).
//
// Effectful: HTTP POST to the endpoint. Here the text is PACKED (prompt content → request body) and
// UNPACKED (response content → the claim). Uses the shared helpers (`loading` accepts prompt/model
// inline OR as a URI + validates by $id) and the shared `_resolving-api-key` plumbing (env key reader).

import loading from "#loading";
import validating from "#validating";
import resolvingApiKey from "#script/resolving-api-key";

const INF = "https://561.group/swarm-intelligence/articulating/library/aperiodic-articulation-category/inferring";
const LLM_MODEL = `${INF}/library/llm-model/llm-model.schema.json`;
const PROMPT = `${INF}/library/prompt/prompt.schema.json`;
const UTTERANCE = "https://561.group/swarm-intelligence/library/utterance/utterance.schema.json";

const ENDPOINTS = {
  "endpoint:groq": {
    url: "https://api.groq.com/openai/v1/chat/completions",
    apiKeyEnvVars: ["GROQ_API_KEY", "API_KEY_GROQ_GROQCLOUD"],
    defaultModel: "llama-3.3-70b-versatile"
  },
  "endpoint:cerebras": {
    url: "https://api.cerebras.ai/v1/chat/completions",
    apiKeyEnvVars: ["CEREBRAS_API_KEY", "API_KEY_CEREBRAS_INFERENCE"],
    defaultModel: "gpt-oss-120b"
  },
  "endpoint:nvidia-nim": {
    url: "https://integrate.api.nvidia.com/v1/chat/completions",
    apiKeyEnvVars: ["NVIDIA_API_KEY", "API_KEY_NVIDIA_NIM"],
    defaultModel: "meta/llama-3.3-70b-instruct"
  }
};

// PACK: the wire text from a prompt (a claim schema-document). {const:<text>} carries literal text; a
// bare string is a lenient bridge; any other schema-doc is serialized so the model sees its shape.
function packPromptText(prompt) {
  if (typeof prompt === "string") return prompt;
  if (prompt && typeof prompt.const === "string") return prompt.const;
  if (prompt && prompt.const !== undefined) return JSON.stringify(prompt.const);
  return JSON.stringify(prompt);
}

// UNPACK helpers over the produced utterance.
export const replyText = (utterance) => utterance?.[1]?.const;       // claim slot → reply text
export const callProvenance = (utterance) => utterance?.[0]?.const;  // token slot → {prompt, endpoint, model, transactionTime}

/**
 * @param {object|string} prompt  a prompt = claim (JSON Schema document, commonly {const:<text>}) or a URI
 * @param {{endpoint: string, model?: string}|string} model  the llm-model object (or a URI to one)
 * @param {{fetchImpl?: typeof fetch}} [options]
 * @returns {Promise<[object, object]>}  utterance [provenance-token, reply-claim]
 */
export default async function inferring(prompt, model, options = {}) {
  const p = loading(prompt, PROMPT);   // URI-or-inline prompt (validated as a claim)
  const m = loading(model, LLM_MODEL); // URI-or-inline model (validated)
  const config = ENDPOINTS[m.endpoint];
  if (!config) throw new Error(`inferring: unknown endpoint "${m.endpoint}". Known: ${Object.keys(ENDPOINTS).join(", ")}`);
  const apiKey = resolvingApiKey(m.endpoint, config.apiKeyEnvVars);
  if (apiKey === null) throw new Error(`inferring: no API key set for "${m.endpoint}"; tried env vars: ${config.apiKeyEnvVars.join(", ")}`);
  const modelName = m.model ?? config.defaultModel;
  const fetchImpl = options.fetchImpl ?? fetch;

  const content = packPromptText(p); // PACK the actual text
  const response = await fetchImpl(config.url, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey.value}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: modelName, messages: [{ role: "user", content }] })
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`inferring: HTTP ${response.status} from ${m.endpoint}: ${text}`);
  }
  const data = await response.json();
  const completion = data?.choices?.[0]?.message?.content;
  if (typeof completion !== "string" || completion.length === 0) {
    throw new Error(`inferring: no completion content in response from ${m.endpoint}`);
  }

  // The reply IS an utterance: token = provenance schema-doc, claim = reply schema-doc.
  const utterance = [
    { const: { kind: "llm-call", endpoint: m.endpoint, model: modelName, originatingPrompt: p, transactionTime: new Date().toISOString() } },
    { const: completion }
  ];
  return validating(utterance, UTTERANCE);
}

export { ENDPOINTS, packPromptText };
