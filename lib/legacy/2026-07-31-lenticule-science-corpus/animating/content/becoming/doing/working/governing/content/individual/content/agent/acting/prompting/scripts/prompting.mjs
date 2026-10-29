// prompting: utterance → user-prompt
// Variance: restriction of articulating-class morphism to human-typing enactor.
// Codomain: user-prompt (aperiodic-articulation-cell variant).
//
// Pure morphism: validates input shape, wraps utterance with enactor identity
// and transaction time. No filesystem or network effects.

/**
 * @param {[string, string]} utterance
 * @param {{enactor: string, transactionTime: string}} options
 * @returns {{utterance: [string, string], enactor: string, transactionTime: string}}
 */
export default function prompting(utterance, options) {
  if (!Array.isArray(utterance) || utterance.length !== 2) {
    throw new Error("prompting: utterance must be [token, claim] array of length 2");
  }
  const [token, claim] = utterance;
  if (typeof token !== "string" || token.length === 0) {
    throw new Error("prompting: utterance[0] (token) must be non-empty string");
  }
  if (typeof claim !== "string" || claim.length === 0) {
    throw new Error("prompting: utterance[1] (claim) must be non-empty string");
  }
  const enactor = options?.enactor;
  const transactionTime = options?.transactionTime;
  if (typeof enactor !== "string" || enactor.length === 0) {
    throw new Error("prompting: options.enactor must be non-empty string");
  }
  if (typeof transactionTime !== "string" || transactionTime.length === 0) {
    throw new Error("prompting: options.transactionTime must be non-empty string");
  }
  return { utterance, enactor, transactionTime };
}
