/**
 * SignChain — contrariety and measurement: where evidence against comes from.
 *
 * Negation is not an operator on tellings. There is no denial: every telling is
 * for the cell it lands on. "Not-p" is a different predicate, the contrary
 * c(p), and contrariety is an involution, c(c(p)) = p. A cell's evidence against
 * is exactly the evidence for its contrary cell (same subject and object, the
 * contrary predicate). Measuring a body of tellings gives each told cell and its
 * contrary both sides this way, so the measure of a contrary cell is the
 * negation (sides swapped) of the measure of the cell — negation on values is
 * derived from contrariety, never told. (Obsmetrologia, Language/Positing/Measure:
 * `Contrary`, `measure`, `no_denial`, `contrary_contrary`.)
 *
 * A contrary codec is the involution on predicate terms. The default codec
 * marks contrariety structurally: c(p) = { not: p } and c({ not: p }) = p, so it
 * is an involution on every term with no parsing. Surface negations ("not p",
 * "¬p") belong to a language codec, which must canonicalize to this form.
 */
import { cell, cellSet, coincides, triple } from "@red-cup-engineering/computer-data-engineering-services-section/signcell/cell";

/** Whether a predicate term is a contrary under the default codec: exactly { not: p }. */
export const isContraryTerm = (term) => term !== null && typeof term === "object" && !Array.isArray(term)
  && Object.keys(term).length === 1 && Object.hasOwn(term, "not");

/** A predicate's canonical form under the default codec: a double contrary reduces, {not:{not:p}} = p. */
export function canonicalPredicate(predicate) {
  let term = predicate, flips = 0;
  while (isContraryTerm(term)) { term = term.not; flips += 1; }
  return flips % 2 === 0 ? term : Object.freeze({ not: term });
}

/** The default contrary codec on canonical predicates: c(p) = { not: p }, c({ not: p }) = p. It is an
 *  involution on canonical terms; a non-canonical term is canonicalized first. */
export const defaultContrary = Object.freeze({
  canonical: canonicalPredicate,
  c: (predicate) => { const p = canonicalPredicate(predicate); return isContraryTerm(p) ? p.not : Object.freeze({ not: p }); },
});

/** The contrary of a cell (as a triple): same subject and object, the contrary predicate. */
export const contraryCell = (at, codec = defaultContrary) => triple(cell(at.subject, codec.c(at.predicate), at.object));

/** A cell with its predicate canonical under a codec. */
export const canonicalCell = (at, codec = defaultContrary) => triple(cell(at.subject, codec.canonical(at.predicate), at.object));

/** Whether a codec is an involution on the given predicate terms, read canonically (it must be, everywhere). */
export const isInvolutionOn = (predicates, codec = defaultContrary) => predicates.every((p) => coincides(codec.c(codec.c(p)), codec.canonical(p)));

/**
 * Measure a body of tellings: for every cell told (and every contrary of one), its evidence for is what was
 * told for it, and its evidence against is what was told for its contrary. Evidence against on an input
 * cell is read as what it is — evidence for that cell's contrary — so measuring is lossless and idempotent.
 */
export function measure(tellings, codec = defaultContrary) {
  const told = cellSet(tellings.flatMap((value) => {
    const at = canonicalCell(value, codec), opposite = contraryCell(value, codec);
    return [cell(at.subject, at.predicate, at.object, { for: value.for ?? [] }), cell(opposite.subject, opposite.predicate, opposite.object, { for: value.against ?? [] })];
  }));
  const forOf = (at) => told.find((value) => coincides(triple(value), triple(at)))?.for ?? [];
  const cells = [];
  for (const value of told) { const opposite = contraryCell(value, codec); cells.push(value, cell(opposite.subject, opposite.predicate, opposite.object)); }
  return cellSet(cells.map((at) => cell(at.subject, at.predicate, at.object, { for: forOf(at), against: forOf(contraryCell(at, codec)) })));
}

/** One cell per contrary pair: the cell whose predicate is not a contrary under the default codec. */
export const representatives = (cells) => Object.freeze(cells.filter((value) => !isContraryTerm(value.predicate)));
