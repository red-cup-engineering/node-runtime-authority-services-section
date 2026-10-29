// mutation: (memory, mutationSpec) → memory'
// create: adds a recall-record. remove: sets its relevance to bottom (substrate
// monotonicity preserves the record; bottom = no evidence held). Per lab/.../memory/mutation/.

/**
 * @param {{agent: string, recallRecords: Array<object>, scope: string}} memory
 * @param {{kind: "create"|"remove", entity: string, relevance?: string, at?: string}} mutationSpec
 * @returns {object}
 */
export default function mutation(memory, mutationSpec) {
  if (!memory || !Array.isArray(memory.recallRecords)) {
    throw new Error("mutation: memory must be a memory object with recallRecords array");
  }
  const { kind, entity, relevance, at } = mutationSpec ?? {};
  if (kind !== "create" && kind !== "remove") {
    throw new Error('mutation: mutationSpec.kind must be "create" or "remove"');
  }
  if (typeof entity !== "string" || entity.length === 0) {
    throw new Error("mutation: mutationSpec.entity must be non-empty string");
  }
  if (kind === "create") {
    const r = relevance ?? "true";
    return {
      ...memory,
      recallRecords: [
        ...memory.recallRecords,
        { entity, relevance: r, lastTouched: at ?? new Date().toISOString() }
      ]
    };
  }
  // remove → set relevance to the carrier's bottom (Q: 0; value-string: "bottom"). Monotonicity preserved.
  return {
    ...memory,
    recallRecords: memory.recallRecords.map((r) =>
      r.entity === entity
        ? { ...r, relevance: typeof r.relevance === "number" ? 0 : "bottom", lastTouched: at ?? r.lastTouched }
        : r
    )
  };
}
