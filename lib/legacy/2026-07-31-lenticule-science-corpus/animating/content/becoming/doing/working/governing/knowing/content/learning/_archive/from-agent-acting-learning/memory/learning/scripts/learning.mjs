// learning: (memory, evidence) → memory'
// Updates recall-record relevance per closure rules. Positive evidence raises
// relevance via joinK; negative evidence lowers it via meetK with decay.
// Per spotcomp/CONTINUOUS-LEARNING.md and lab/.../memory/learning/.
//
// Q-ENRICHED: when a record's relevance is a NUMBER it lives in the quantale Q
// (hacking/q-relevance) and the closure rules become quantale ops -- promotion = qJoin, decay =
// qTensor by a factor (persistence = factor 1, e.g. sense), dismissal = qMeet 0. When relevance is a
// value corner string the original value path runs unchanged (bare value corners ⊂ Q on the presence reading,
// docs/GENEALOGY.md §6). evidence MAY carry {tier} (provenance) or {value}/{factor} for the Q path.

import { joinK } from "#script/positing";
import { meetK } from "#script/finite-meeting-knowledge";
import { qJoin, qDecay, qMeet, qFromProvenance } from "#script/q-relevance";

const RULES = new Set(["relevance-promotion", "relevance-decay", "explicit-dismissal"]);

/**
 * @param {{agent: string, recallRecords: Array<{entity: string, relevance: string, lastTouched: string}>, scope: string}} memory
 * @param {{entity: string, signal: "promotion"|"decay"|"dismissal", at: string}} evidence
 * @returns {{outputMemory: object, ruleApplied: string}}
 */
export default function learning(memory, evidence) {
  if (!memory || !Array.isArray(memory.recallRecords)) {
    throw new Error("learning: memory must be a memory object with recallRecords array");
  }
  if (!evidence || typeof evidence.entity !== "string" || typeof evidence.signal !== "string") {
    throw new Error("learning: evidence must have entity and signal");
  }
  const ruleMap = {
    promotion: "relevance-promotion",
    decay: "relevance-decay",
    dismissal: "explicit-dismissal"
  };
  const ruleApplied = ruleMap[evidence.signal];
  if (!ruleApplied || !RULES.has(ruleApplied)) {
    throw new Error(`learning: signal must be promotion/decay/dismissal; got "${evidence.signal}"`);
  }
  const updated = memory.recallRecords.map((r) => {
    if (r.entity !== evidence.entity) return r;
    const qPath = typeof r.relevance === "number";
    let newRelevance;
    if (ruleApplied === "relevance-promotion") {
      const raise = evidence.value ?? (evidence.tier ? qFromProvenance(evidence.tier).value : 1);
      newRelevance = qPath ? qJoin(r.relevance, raise) : joinK(r.relevance, "true");
    } else if (ruleApplied === "relevance-decay") {
      const factor = evidence.factor ?? (evidence.tier ? qFromProvenance(evidence.tier).decay : 0.7);
      newRelevance = qPath ? qDecay(r.relevance, factor) : meetK(r.relevance, "top");
    } else {
      newRelevance = qPath ? qMeet(r.relevance, 0) : meetK(r.relevance, "bottom");
    }
    return { ...r, relevance: newRelevance, lastTouched: evidence.at ?? r.lastTouched };
  });
  return {
    outputMemory: { ...memory, recallRecords: updated },
    ruleApplied
  };
}
