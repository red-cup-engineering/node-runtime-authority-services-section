/**
 * EAVT rows as SignCells: a row (e, a, v, t) tells the cell (e, a, v), its time
 * t the witness for it. A cell gives back one row per for-witness. An EAVT row
 * is an assertion and has no side, so evidence against a cell has no EAVT row.
 */
import { row as admitRow } from "@red-cup-engineering/eavt";
import { cell } from "@red-cup-engineering/computer-data-engineering-services-section/signcell/cell";

/** The cell one admitted EAVT row tells, its time the for-witness. */
export function eavtToCell(row) {
  admitRow(row);
  return cell(row.e, row.a, row.v, { for: [row.t] });
}

/** A cell's EAVT rows, one per for-witness. */
export function cellToEavt(told) {
  return told.for.map((t) => admitRow({ e: told.subject, a: told.predicate, v: told.object, t }));
}
