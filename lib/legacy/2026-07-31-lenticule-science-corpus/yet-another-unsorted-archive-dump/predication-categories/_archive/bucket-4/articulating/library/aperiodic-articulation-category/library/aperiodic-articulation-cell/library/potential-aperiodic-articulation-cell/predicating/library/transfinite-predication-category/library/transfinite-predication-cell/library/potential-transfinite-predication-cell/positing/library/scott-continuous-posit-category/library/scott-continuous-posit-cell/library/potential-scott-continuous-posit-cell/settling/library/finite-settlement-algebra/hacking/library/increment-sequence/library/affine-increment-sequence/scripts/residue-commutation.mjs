// residue-commutation.mjs — the cream of the old `affine.py`: does the parity-commutation of
// the affine family's residue relation vanish (Δ_m), and does that track instant residue
// stabilization (τ_m)?
//
// Δ_m is the finite shadow of the commutating square σ∘Δ = Δ∘σ, restricted to Z/m. This module
// is self-contained (the small relation-closure it needs is inlined — no comonad engine), and
// is plugged into by parity-shadows-commute-on-residues.test.mjs with the affine (a,b,d) sweep.

const gcd = (a, b) => (b === 0 ? a : gcd(b, a % b));
function modInverse(a, m) {
  let [r0, r] = [((a % m) + m) % m, m], [s0, s] = [1, 0];
  while (r !== 0) { const q = Math.floor(r0 / r); [r0, r] = [r, r0 - q * r]; [s0, s] = [s, s0 - q * s]; }
  return ((s0 % m) + m) % m;
}
export function solveLinearCongruence(d, r, m) {
  const g = gcd(d, m);
  if (r % g !== 0) return [];
  const d1 = d / g, r1 = r / g, m1 = m / g;
  const t0 = (modInverse(((d1 % m1) + m1) % m1, m1) * (((r1 % m1) + m1) % m1)) % m1;
  return Array.from({ length: g }, (_, k) => (t0 + k * m1) % m);
}

const zeros = (n) => Array.from({ length: n }, () => Array(n).fill(0));
const matMul = (A, B) => A.map((row, i) => B[0].map((_, j) => (row.some((_, k) => A[i][k] && B[k][j]) ? 1 : 0)));
const transpose = (A) => A[0].map((_, j) => A.map((r) => r[j]));
const matXor = (A, B) => A.map((r, i) => r.map((x, j) => x ^ B[i][j]));
const countOnes = (A) => A.reduce((s, r) => s + r.reduce((a, b) => a + b, 0), 0);
function boxStep(A) { // one-hop forward closure + reflexivity
  const n = A.length, C = matMul(A, A).map((r, i) => r.map((x, j) => (x || A[i][j] ? 1 : 0)));
  for (let i = 0; i < n; i++) C[i][i] = 1;
  return C;
}
const cGraph = (Y) => boxStep(transpose(boxStep(transpose(Y)))); // C = □∘◇

export function residueRelationCollatzLike(a, b, d, m) {
  const R = zeros(m);
  for (let r = 0; r < m; r++) {
    if (r % 2 === 1) R[r][(((a * r + b) % m) + m) % m] = 1;
    else for (const t of solveLinearCongruence(d, r, m)) R[r][t] = 1;
  }
  return R;
}

const extract = (R, idxs) => idxs.map((i) => idxs.map((j) => R[i][j]));
function embed(B, idxs, m) { const O = zeros(m); idxs.forEach((i, a) => idxs.forEach((j, b) => { O[i][j] = B[a][b]; })); return O; }
const nucleusBlock = (R, idxs, m) => embed(cGraph(extract(R, idxs)), idxs, m);

export function parityCommutationDefect(R, m) {
  const E = [...Array(m).keys()].filter((i) => i % 2 === 0);
  const O = [...Array(m).keys()].filter((i) => i % 2 === 1);
  const A = nucleusBlock(nucleusBlock(R, O, m), E, m); // N_E(N_O(R))
  const B = nucleusBlock(nucleusBlock(R, E, m), O, m); // N_O(N_E(R))
  return countOnes(matXor(A, B));
}

export function stabilizationDepth(R, maxSteps = 6) {
  let cur = R;
  for (let t = 0; t <= maxSteps; t++) { if (countOnes(matXor(cur, cGraph(cur))) === 0) return t; cur = cGraph(cur); }
  return null;
}

export function testEquivalence(aVals, bVals, d = 2, m = 6) {
  const cm = { "Δ=0,τ=0": 0, "Δ=0,τ>0": 0, "Δ>0,τ=0": 0, "Δ>0,τ>0": 0 };
  const rows = [];
  for (const a of aVals) for (const b of bVals) {
    const R = residueRelationCollatzLike(a, b, d, m);
    const delta = parityCommutationDefect(R, m), tau = stabilizationDepth(R);
    cm[`${delta === 0 ? "Δ=0" : "Δ>0"},${tau === 0 ? "τ=0" : "τ>0"}`]++;
    rows.push({ a, b, delta, tau });
  }
  return { cm, rows };
}
