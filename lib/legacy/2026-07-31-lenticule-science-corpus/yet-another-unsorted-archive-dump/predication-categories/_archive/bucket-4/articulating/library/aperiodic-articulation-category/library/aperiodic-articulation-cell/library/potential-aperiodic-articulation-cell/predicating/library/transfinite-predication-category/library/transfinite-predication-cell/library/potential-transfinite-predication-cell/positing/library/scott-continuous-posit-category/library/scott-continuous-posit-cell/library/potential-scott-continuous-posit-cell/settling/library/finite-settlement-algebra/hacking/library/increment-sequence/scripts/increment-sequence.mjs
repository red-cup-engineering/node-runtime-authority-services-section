// increment-sequence.mjs — the plug-in interface, made runnable.
//
// An increment-sequence U = (u_τ) is "the input data driving a settlement". Here it is a
// finite endo-map turned into a generator the settling-endofunctor can iterate. A family
// (Collatz, affine, successor, modular) is exactly such a generator — that is what "affines
// are just a part of that" means: they are increment-sequences, nothing more.
//
// Generator shape consumed by #settling-endofunctor:
//   { name, seed, key(v)→string, step(v)→{ next, move, nucleusShadow } }

export function fromEndoMap(rawStep, { seed, name = "increment", key = (v) => String(v) } = {}) {
  const step = (v) => {
    const r = rawStep(v);
    return r && typeof r === "object" && "next" in r
      ? { move: "step", nucleusShadow: "—", ...r }
      : { next: r, move: "step", nucleusShadow: "—" };
  };
  return { name, seed, key, step };
}

// Helper for parity-branched integer maps (the shape Collatz and the affine family share):
//   even v → contract(v)  [saturating-shadow],  odd v → expand(v)  [transferring-shadow].
export function parityBranched({ seed, name, expand, contract, expandLabel, contractLabel }) {
  return {
    name, seed, key: (v) => String(v),
    step: (v) =>
      v % 2n === 0n
        ? { next: contract(v), move: contractLabel, nucleusShadow: "saturating-shadow" }
        : { next: expand(v), move: expandLabel, nucleusShadow: "transferring-shadow" },
  };
}
