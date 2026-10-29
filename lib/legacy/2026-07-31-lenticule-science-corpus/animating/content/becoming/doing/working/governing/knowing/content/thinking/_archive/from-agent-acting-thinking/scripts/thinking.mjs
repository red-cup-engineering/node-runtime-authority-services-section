// thinking: one descent of the meaning tower — the arrow of time, aperiodic → finite.
//   articulating (aperiodic: open the utterance) → predicating (transfinite: fiber it into a
//   predication-cell) → positing+settling (scott→finite: charge it and fold the settling orbit to the
//   Knaster–Tarski apex). All real-cell; the legacy string composition is retired.
//
// thinking(utterance, decomposition, posit): utterance = [token, claim] schema-docs; decomposition =
// the value-free predication-cell {subject, predicate, object} of real schema-docs; posit = a
// bilattice-value charge cell. Returns the settled valuation + regime (strict-finite when the orbit
// reaches its apex). Per docs/GENEALOGY.md and the aperiodic→finite arrow.

import articulating from "#script/articulating";
import predicating from "#script/predicating";
import settling from "#script/settling";

export default function thinking(utterance, decomposition, posit) {
  const potential = articulating(utterance);                 // aperiodic: open
  const cell = predicating(potential, decomposition);        // transfinite: fiber
  return settling({                                          // scott → finite: charge + settle to apex
    valuation: { entries: [] },
    increments: [{ cell, posit }],
    fuel: 8
  });
}
