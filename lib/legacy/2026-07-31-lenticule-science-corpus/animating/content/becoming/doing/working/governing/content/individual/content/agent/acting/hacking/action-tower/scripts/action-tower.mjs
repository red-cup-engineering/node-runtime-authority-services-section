// action-tower: the swarm's ACTION tower + study/consensus + the conductor's command verbs.
//
// Feature-parity port of the harness's remaining substrate, so the harness can hold none of its own
// (docs/GENEALOGY.md: study/consensus and the action tower are the swarm's). Faithful to the harness
// behavior; cross-$thing deps use #alias. The budget/attention governor is exported as `metabolizing`
// to avoid colliding with orchestration-algebra's `governing` (governance-theory selection) — the
// harness comment itself calls the budget "the organism's METABOLISM".
//
// Action tower (parallels the meaning tower): being → doing → working → metabolizing.
// Study/consensus: studying (settle a subject), delegating (reconcile N results by knowledge-meet),
// consolidating (gated transcript → memory rows). Composed thought: thinking. Conductor commands:
// daydreaming / inquiring / deriving (pure utterance emitters). Tool boundary: invoking.

import articulating from "#script/articulating";
import predicating from "#script/predicating";
import positing from "#script/positing";
import settling from "#script/settling";

const VALUES = ["bottom", "true", "false", "top"];
function meetK(a, b) {
  if (a === b) return a;
  if (a === "bottom" || b === "bottom") return "bottom";
  if (a === "top") return b;
  if (b === "top") return a;
  return "bottom"; // {true,false} disagree -> bottom (no shared committed evidence; H^1 obstruction)
}

// ---------- action tower ----------
// being: spec -> modeled-player (two hands: learning=inward, sensing=outward drone).
export function being(spec) {
  const id = spec?.id;
  if (typeof id !== "string" || id.length === 0) throw new TypeError("being: spec.id must be a non-empty string");
  const role = typeof spec?.role === "string" && spec.role ? spec.role : "swarm-member";
  const kind = spec?.kind === "sensing" ? "sensing" : "learning";
  const capability = Array.isArray(spec?.capability) ? spec.capability
    : (kind === "sensing" ? ["observe-external", "capture", "report"] : ["observe", "posit", "contribute"]);
  const handedness = {
    recv: spec?.recv ?? ["utterance"],
    send: spec?.send ?? ["claim"],
    actuate: spec?.actuate ?? (kind === "sensing" ? ["read-repo", "web-search"] : []),
    observe: spec?.observe ?? (kind === "sensing" ? ["repo", "web", "environment"] : ["shared-trace"])
  };
  return {
    id, role, kind, capability, handedness,
    governance: typeof spec?.governance === "string" ? spec.governance : "budget-bounded",
    inbox: `trace:inbox/${id}`, outbox: `trace:outbox/${id}`
  };
}

// doing: (agent, intent) -> act (an utterance entering the substrate). sense and effect share a language.
export function doing(agent, intent) {
  if (!agent || typeof agent.id !== "string" || !agent.id) throw new TypeError("doing: agent.id required");
  if (typeof intent !== "string" || intent.length === 0) throw new TypeError("doing: intent must be a non-empty string");
  return { agent: agent.id, intent, utterance: [`act:${agent.id}`, intent] };
}

// working: (agent, subject, read) -> claim-record (agent contributes by reading; read is injected).
export function working(agent, subject, read, opts = {}) {
  if (!agent || typeof agent.id !== "string" || !agent.id) throw new TypeError("working: agent.id required");
  if (typeof subject !== "string" || subject.length === 0) throw new TypeError("working: subject must be a non-empty string");
  const r = read ? read(agent, subject) : null;
  const value = VALUES.includes(r?.value) ? r.value : "bottom";
  const evidence = Array.isArray(r?.evidence) && r.evidence.length ? r.evidence : [`agent:${agent.id}`];
  return { agent: agent.id, subject, status: "contributed", claim: { observer: agent.id, value, evidence } };
}

// metabolizing (was harness `governing`): budget governor (metabolism) + attention to highest-dissent.
export function metabolizing(state, opts = {}) {
  const budget = Number.isFinite(state?.budget) ? state.budget : 0;
  const spent = Number.isFinite(state?.spent) ? state.spent : 0;
  const remaining = budget - spent;
  const allowed = remaining > 0;
  let attend = null;
  if (Array.isArray(state?.subjects) && state.subjects.length) {
    attend = [...state.subjects].sort((a, b) => (b.dissent ?? 0) - (a.dissent ?? 0))[0]?.subject ?? null;
  }
  return { allowed, remaining, attend, reason: allowed ? "within-budget" : "budget-exhausted" };
}

// ---------- study / consensus ----------
// delegating: (task, results[values]) -> consensus by knowledge-MEET (disagreement -> bottom).
export function delegating(task, results) {
  if (typeof task !== "string" || task.length === 0) throw new TypeError("delegating: task must be a non-empty string");
  if (!Array.isArray(results) || results.length === 0) throw new TypeError("delegating: results must be a non-empty array");
  for (const r of results) if (!VALUES.includes(r)) throw new TypeError(`delegating: each result must be one of ${VALUES.join(", ")}`);
  return { task, consensus: results.reduce(meetK, "top"), results };
}

const lean = (v) => (v === "true" ? 1 : v === "false" ? -1 : 0);
const meanLean = (vals) => (vals.length ? vals.map(lean).reduce((a, b) => a + b, 0) / vals.length : 0);
function dissent(vals) {
  const n = vals.length;
  if (n < 2) return 0;
  const x = vals.map(lean);
  let e = 0;
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) e += (x[i] - x[j]) ** 2;
  return e / (n * (n - 1) / 2);
}
// studying: settle a subject's claim-lattice; demand more from an injected swarm until confident.
// dissent is a crude dispersion STUB (the real measure is the sheaf Laplacian / moduli-descent).
export function studying(subject, claims, swarm, opts = {}) {
  if (typeof subject !== "string" || subject.length === 0) throw new TypeError("studying: subject must be a non-empty string");
  const { threshold = 0.6, maxRounds = 4 } = opts;
  let observers = Array.isArray(claims) ? [...claims] : [];
  const demands = [];
  let rounds = 0;
  while (rounds < maxRounds) {
    const vals = observers.map((c) => c.value);
    if (observers.length >= 1 && Math.abs(meanLean(vals)) >= threshold) break;
    const demand = { subject, reason: observers.length < 1 ? "no-evidence" : "below-confidence-threshold", confidence: Math.abs(meanLean(vals)), round: rounds };
    demands.push(demand);
    const added = swarm ? swarm(demand) : [];
    if (!Array.isArray(added) || added.length === 0) break;
    observers = observers.concat(added);
    rounds++;
  }
  const vals = observers.map((c) => c.value);
  const consensus = vals.length ? vals.reduce(meetK, "top") : "bottom";
  const ml = meanLean(vals);
  return {
    subject, consensus,
    truth: ml > 0 ? "true" : ml < 0 ? "false" : consensus,
    confidence: Math.abs(ml), dissent: dissent(vals),
    accepted: observers.length >= 1 && Math.abs(ml) >= threshold,
    rounds, claimCount: observers.length, demands
  };
}

// consolidating: (sessionTrace, enactor, {gate}) -> typed, gated memory rows. enactor is injected
// (e.g. the aperiodic dream); ungated candidates are dropped. PURE: returns rows, no durable write.
export function consolidating(sessionTrace, enactor, { gate, now } = {}) {
  if (!Array.isArray(sessionTrace) || sessionTrace.length === 0) throw new TypeError("consolidating: sessionTrace must be a non-empty array");
  const candidates = enactor(sessionTrace);
  if (!Array.isArray(candidates)) throw new TypeError("consolidating: enactor must return an array");
  const t = (now && now()) || new Date().toISOString();
  const rows = [];
  for (const c of candidates) {
    for (const [k, v] of [["e", c?.e], ["a", c?.a], ["v", c?.v], ["placement", c?.placement]])
      if (typeof v !== "string" || v.length === 0) throw new TypeError(`consolidating: candidate.${k} must be a non-empty string`);
    if (!Array.isArray(c.evidence) || c.evidence.length === 0) throw new TypeError("consolidating: candidate.evidence must be a non-empty array");
    const row = { e: c.e, a: c.a, v: c.v, t, evidence: c.evidence, placement: c.placement };
    if (gate && !gate(row)) continue;
    rows.push(row);
  }
  return rows;
}

// ---------- composed thought + commands + tool boundary ----------
// thinking: one descent of the meaning tower (articulate -> predicate -> posit -> settle).
export function thinking(utterance, decomposition, posit) {
  return settling(positing(predicating(articulating(utterance), decomposition), posit));
}

// conductor command emitters (pure utterances the MCP/entrypoint enacts).
export function daydreaming(context) {
  const focus = typeof context === "string" ? context : (context?.focus ?? "recent");
  return { utterance: [`daydream:${focus}`, "consolidate current context"], focus };
}
export function inquiring(subject) {
  if (typeof subject !== "string" || subject.length === 0) throw new TypeError("inquiring: subject must be a non-empty string");
  return { utterance: [`inquiry:${subject}`, "study this subject"], subject };
}
export function deriving(goal) {
  if (typeof goal !== "string" || goal.length === 0) throw new TypeError("deriving: goal must be a non-empty string");
  return { utterance: [`derive:${goal}`, "settle this claim"], goal };
}

// invoking: type a tool-call boundary; the effect is enacted outside and supplied as `output`.
export function invoking(envelope, output) {
  if (!envelope || typeof envelope.tool !== "string" || envelope.tool.length === 0) throw new TypeError("invoking: envelope.tool required");
  return { tool: envelope.tool, outcome: output && output.error ? "error" : "ok", output: output ?? null };
}

export default {
  being, doing, working, metabolizing,
  delegating, studying, consolidating,
  thinking, daydreaming, inquiring, deriving, invoking
};
