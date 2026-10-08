/**
 * realization — what SEN realizes of Obsmetrologia's λ fragment (Predicating.CurryHowardLambek, with
 * normal order in Language/Predicating/NormalOrder): a term's one-step reducts, its complete
 * development and its normal form from this section's evaluator, and the substitution and shift its
 * β-rule is built on from the notation's statics in the data layer. lean-system's sen-lambda suite
 * judges these bindings against golden vectors read off the specification, so every dialect of SEN
 * that comes to rest here keeps the specification's rows.
 */
import { instantiateSen, shiftSen } from "@red-cup-engineering/computer-data-services-section/semiotic-expression-notation";
import { dev, normalize, step } from "./eval.mjs";

const lambek = "Obsmetrologia.Predicating.CurryHowardLambek.";

/** Each Obsmetrologia declaration SEN realizes, bound to its realizer. */
export const obsmetrologiaRealization = Object.freeze({
  [`${lambek}Tm.reducts`]: (term) => step(term),
  [`${lambek}dev`]: (term) => dev(term),
  // The specification's normalizer takes fuel; normal order here runs to the normal form the
  // vectors' terms have, so the fuel bound is the specification's concern, not the realizer's.
  [`${lambek}Tm.normalize`]: (_fuel, term) => normalize(term),
  [`${lambek}Tm.inst`]: (body, value) => instantiateSen(body, value),
  [`${lambek}Tm.lift`]: (by, term) => shiftSen(by, 0, term),
});
