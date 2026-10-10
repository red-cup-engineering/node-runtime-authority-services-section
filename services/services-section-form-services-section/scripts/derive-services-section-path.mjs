#!/usr/bin/env node
// Derive a services section's path from its name, never by an agent's choice (rule
// placement-is-derived-from-the-name-by-script). A name ends in -services-section; its custody is read from the
// name (internal 561-group-*, external public-*, else its last word: engineering, science or operations), and the
// section nests under the existing section whose name it specializes most closely: the one whose words appear, in
// order, within its own words and in the same custody, the custody's root section being the least specific. A
// name that derives no custody, or that two sections specialize equally, is refused: a placement the script
// cannot derive is a defect of the name.
//
//   derive-services-section-path   reads one JSON value per input line, {name, sections} or {sections: [{name, path}]},
//                                  and writes one JSON value per output line: the derivation, or the placement check.
import { createInterface } from "node:readline";

const GROUP_SERVICES = "lib/emsenn/services/561-group/services";
const SUFFIX = "-services-section";
const HOUSES = ["engineering", "science", "operations"];

const words = (name) => name.slice(0, -SUFFIX.length).split("-");

/** The custody a section name declares and the root section of that custody, or null. */
export function servicesSectionCustody(name) {
  if (typeof name !== "string" || !name.endsWith(SUFFIX) || name.length === SUFFIX.length) return null;
  if (name === "561-group-services-section" || name.startsWith("561-group-")) return { custody: "561-group", root: "561-group-services-section" };
  if (name === "public-services-section" || name.startsWith("public-")) return { custody: "public", root: "public-services-section" };
  const last = words(name).at(-1);
  return HOUSES.includes(last) ? { custody: last, root: `${last}${SUFFIX}` } : null;
}

/** Whether `general`'s words appear, in order, within `specific`'s words (and are fewer). */
function specializes(specific, general) {
  const inner = words(specific), outer = words(general);
  if (outer.length >= inner.length) return false;
  let at = 0;
  for (const word of inner) if (word === outer[at]) at += 1;
  return at === outer.length;
}

/**
 * Derives a section's path from its name and the names of the sections that exist.
 * @param {{name: string, sections?: string[]}} request The section's name and the existing section names.
 * @returns {{name: string, custody: string, parent: string|null, chain: string[], path: string} | {refused: string, name: string, candidates?: string[]}}
 *   The derivation (chain from the custody root to the section), or a refusal: NOT_A_SECTION_NAME, NAME_DERIVES_NO_CUSTODY,
 *   NO_PARENT, or AMBIGUOUS_PARENT with the equally specific candidates.
 */
export function deriveServicesSectionPath(request) {
  const name = request?.name;
  if (typeof name !== "string" || !name.endsWith(SUFFIX) || name.length === SUFFIX.length) return { refused: "NOT_A_SECTION_NAME", name };
  const seat = servicesSectionCustody(name);
  if (!seat) return { refused: "NAME_DERIVES_NO_CUSTODY", name };
  const known = new Set([...(request.sections ?? []), seat.root]);
  const chain = [name];
  for (let current = name; current !== seat.root;) {
    const candidates = [...known].filter((other) => other !== current && servicesSectionCustody(other)?.custody === seat.custody && specializes(current, other));
    if (candidates.length === 0) return { refused: "NO_PARENT", name: current };
    const best = Math.max(...candidates.map((other) => words(other).length));
    const closest = candidates.filter((other) => words(other).length === best);
    if (closest.length !== 1) return { refused: "AMBIGUOUS_PARENT", name: current, candidates: closest.sort() };
    current = closest[0];
    chain.unshift(current);
  }
  return { name, custody: seat.custody, parent: chain.length > 1 ? chain.at(-2) : null, chain, path: `${GROUP_SERVICES}/${chain.join("/services/")}` };
}

/**
 * Checks where each section stands against where its name places it.
 * @param {{sections: {name: string, path: string}[]}} request The sections, each with its name and its actual repository-relative path.
 * @returns {{checked: number, placed: number, misplaced: {name: string, path: string, derived: string}[], refused: object[]}}
 */
export function checkServicesSectionPlacement(request) {
  const sections = request?.sections ?? [];
  const names = sections.map((section) => section.name);
  const misplaced = [], refused = [];
  for (const section of sections) {
    const derived = deriveServicesSectionPath({ name: section.name, sections: names });
    if (derived.refused) refused.push({ ...derived, path: section.path });
    else if (derived.path !== section.path) misplaced.push({ name: section.name, path: section.path, derived: derived.path });
  }
  return { checked: sections.length, placed: sections.length - misplaced.length - refused.length, misplaced, refused };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  for await (const line of createInterface({ input: process.stdin })) {
    if (!line.trim()) continue;
    const request = JSON.parse(line);
    const result = request.name ? deriveServicesSectionPath(request) : checkServicesSectionPlacement(request);
    process.stdout.write(`${JSON.stringify(result)}\n`);
  }
}
