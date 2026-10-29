// dreaming : EAVT rows → EAVT rows.  The settling arrow applied to MEMORY, as pure structure work.
//
// EAVT is EAVT: every row in and out is exactly {e, a, v, t} — no extra fields — and e/a/v/t are OUR
// actual structures (e = token, a = claim, v = token or charge-cell, t = transaction token), never
// strings. Dreaming PASSES structures around, WITNESSES them as datoms, and GENERATES new datoms by
// EXTENSION or RESTRICTION. Every output row is validated against the eavt-row schema.
//
// ONE morphism read on the bigraded KZ-diamond's two axes; the four named dreams are the diagonal
// cells (NOT a ladder), and per the arrow of time consolidation runs aperiodic→finite:
//   aperiodic (κ≥ω₁, base EXTENDS): raw experience-noise enters via the network (inferring); NEW
//     entity/predicate generators are channeled in.
//   transfinite (ω<κ<ω₁, fiber EXTENDS): co-occurring subjects related by an EXTENDED predicate
//     (the conjunction claim {allOf:[a, sharedValue]}).
//   scott-continuous (κ=ω, fixed fiber): accumulate evidence per (e,a) by the REAL knowledge-join
//     (directed supremum) over charge cells.
//   finite (κ<ω, fixed fiber): recombine to a fixed point — composition (RESTRICTION: transitive
//     close) and generalization (EXTENSION: subjects unioned into an anyOf-token).
// Variance: coincidence (declared). Per docs/GENEALOGY.md §5.

import { joinK } from "#script/positing";
import inferring, { replyText } from "#script/inferring";

const S = (x) => JSON.stringify(x);
const isChargeCell = (v) => Array.isArray(v) && v.length === 2 && Array.isArray(v[1]); // [carrier,[slot,slot]]
const isToken = (x) => x !== null && typeof x === "object" && !Array.isArray(x);       // a json-schema-doc
// t (transaction) as a token: a json-schema doc whose inhabitant is the transaction time.
const txn = (opts) => ({ const: opts.now || new Date().toISOString() });

// a witnessed predication: the SPOT row {e,a,v,t}. Not a special "thing" — a row in a trace; the
// charge lives in v, the trace persists it (M2 will witness it to the relevant thing's log).
const row = (e, a, v, t) => ({ e, a, v, t });

// --- finite corner: composition (RESTRICTION, transitive close) + generalization (EXTENSION, union) ---
export function finiteDream(rows, opts = {}) {
  const cells = (Array.isArray(rows) ? rows : []).filter((c) => c && c.e != null && c.a != null && c.v != null);
  const t = txn(opts);
  const have = new Set(cells.map((c) => S([c.e, c.a, c.v])));
  const out = [];
  const add = (e, a, v) => { const k = S([e, a, v]); if (!have.has(k)) { have.add(k); out.push(row(e, a, v, t)); } };
  // composition: e —a→ o, o —a→ o2  ⊢  e —a→ o2 (structure equality x.v == y.e)
  for (const x of cells) for (const y of cells)
    if (x !== y && S(x.a) === S(y.a) && S(x.v) === S(y.e)) add(x.e, x.a, y.v);
  // generalization: ≥2 distinct subjects sharing (a,v) → an anyOf-token unioning them (extension)
  const bySV = new Map();
  for (const c of cells) {
    const k = S([c.a, c.v]);
    if (!bySV.has(k)) bySV.set(k, { a: c.a, v: c.v, subs: [] });
    if (!bySV.get(k).subs.some((s) => S(s) === S(c.e))) bySV.get(k).subs.push(c.e);
  }
  for (const g of bySV.values()) if (g.subs.length >= 2) add({ anyOf: g.subs }, g.a, g.v);
  return out;
}

// --- scott-continuous corner: accumulate charge per (e,a) by the real knowledge-join (directed sup) ---
export function scottContinuousDream(rows, opts = {}) {
  const cells = (Array.isArray(rows) ? rows : []).filter((c) => c && c.e != null && c.a != null && isChargeCell(c.v));
  const t = txn(opts);
  const byEA = new Map();
  for (const c of cells) {
    const k = S([c.e, c.a]);
    if (!byEA.has(k)) byEA.set(k, { e: c.e, a: c.a, v: c.v });
    else byEA.get(k).v = joinK(byEA.get(k).v, c.v); // real knowledge-join over charge cells
  }
  return [...byEA.values()].map((g) => row(g.e, g.a, g.v, t));
}

// --- transfinite corner: co-occurring subjects related by an EXTENDED predicate {allOf:[a, v]} ---
export function transfiniteDream(rows, opts = {}) {
  const { limit = 24 } = opts;
  const cells = (Array.isArray(rows) ? rows : []).filter((c) => c && c.e != null && c.a != null && isToken(c.v));
  const t = txn(opts);
  const byAV = new Map();
  for (const c of cells) {
    const k = S([c.a, c.v]);
    if (!byAV.has(k)) byAV.set(k, { a: c.a, v: c.v, subs: [] });
    if (!byAV.get(k).subs.some((s) => S(s) === S(c.e))) byAV.get(k).subs.push(c.e);
  }
  const out = [];
  for (const { a, v, subs } of byAV.values()) {
    if (subs.length < 2) continue;
    const coPredicate = { allOf: [a, v] }; // the conjunction claim: a AND the shared value (extension)
    for (let i = 0; i < subs.length; i++) for (let j = i + 1; j < subs.length; j++) {
      if (out.length >= limit) return out;
      out.push(row(subs[i], coPredicate, subs[j], t));
    }
  }
  return out;
}

// --- aperiodic corner: channel NEW generators from experience-noise via inferring [NETWORK] ---
const DREAM_INSTRUCTION =
  "You are the subconscious of an AI agent, dreaming between sessions. You receive the agent's recent " +
  "EXPERIENCES (what the user said; what the agent built, learned, or was corrected on). Reflect, then " +
  "consolidate the DURABLE lessons the agent should carry into its next waking so it acts wiser. Output " +
  'ONLY a JSON array of {"subject":string,"predicate":string,"object":string} objects. JSON array only, no prose.';

export async function aperiodicDream(experiences, opts = {}) {
  const xs = (Array.isArray(experiences) ? experiences : [String(experiences)]).map(String);
  const claim = `${DREAM_INSTRUCTION}\n\nEXPERIENCES:\n${xs.map((e, i) => `${i + 1}. ${e}`).join("\n")}`;
  const model = { endpoint: opts.endpoint ?? "endpoint:groq", ...(opts.model ? { model: opts.model } : {}) };
  const utterance = await inferring({ const: claim }, model, { fetchImpl: opts.fetchImpl }); // raw noise in
  const text = replyText(utterance) ?? "";
  const start = text.indexOf("["), end = text.lastIndexOf("]");
  if (start < 0 || end < 0) return [];
  let parsed;
  try { parsed = JSON.parse(text.slice(start, end + 1)); } catch { return []; }
  const t = txn(opts);
  // each new fact is witnessed as an EAVT row; the subject/predicate/object become token/claim/token
  // structures (their literal text is the const-inhabitant of the slot — data inside a slot, not a leaf).
  return parsed
    .filter((c) => c && c.subject && c.predicate && c.object)
    .map((c) => row({ const: String(c.subject) }, { const: String(c.predicate) }, { const: String(c.object) }, t));
}

const CELLS = {
  finite: finiteDream,
  "scott-continuous": scottContinuousDream,
  transfinite: transfiniteDream,
  aperiodic: aperiodicDream
};

export default function dreaming(input, opts = {}) {
  const regime = opts.regime ?? "finite";
  const cell = CELLS[regime];
  if (!cell) throw new Error(`dreaming: unknown regime "${regime}". Known: ${Object.keys(CELLS).join(", ")}`);
  return cell(input, opts);
}
