// peano.mjs — Peano arithmetic built from the ONE morphism (successor), via iterated settling.
//
// ℕ is the successor settlement (the natural-number object). 0 is the seed; S is the step.
// Addition is iterated successor; multiplication is iterated addition — primitive recursion,
// nothing more. Every operation here bottoms out in `S`, the successor generator's step, so
// "arithmetic is the shadow of the successor orbit" is code, not slogan.

import successor from "#successor";

const gen = successor(0);
export const S = (n) => gen.step(BigInt(n)).next; // the one morphism: n ↦ n+1
export const ZERO = 0n;

// nat(k) = S applied k times to 0 — the k-th cell of the ℕ orbit.
export function nat(k) {
  let v = ZERO;
  for (let i = 0; i < Number(k); i++) v = S(v);
  return v;
}

// add(a,b) = b-fold successor from a.   a+0 = a ;  a+S(b) = S(a+b).
export function add(a, b) {
  let v = BigInt(a);
  for (let i = 0n; i < BigInt(b); i++) v = S(v);
  return v;
}

// mul(a,b) = b-fold (+a) from 0.        a·0 = 0 ;  a·S(b) = a·b + a.
export function mul(a, b) {
  let v = ZERO;
  for (let i = 0n; i < BigInt(b); i++) v = add(v, a);
  return v;
}

// pow(a,b) = b-fold (·a) from 1 — the next rung of the hyperoperation tower (iterated mul).
export function pow(a, b) {
  let v = 1n;
  for (let i = 0n; i < BigInt(b); i++) v = mul(v, a);
  return v;
}

// The defining (primitive-recursion) equations, as predicates — what a test checks.
export const addRecursion = (a, b) => add(a, S(b)) === S(add(a, b)) && add(a, 0n) === BigInt(a);
export const mulRecursion = (a, b) => mul(a, S(b)) === add(mul(a, b), BigInt(a)) && mul(a, 0n) === ZERO;
