from ritm_core import *

# 1. Make a tiny universe
E = Universe([0, 1, 2])
print("Universe:", E.U)

# 2. Build Heyting implication and negation
impl = heyting_implication(E)
neg = heyting_negation(E)

# 3. Define a simple preorder ≤ on the universe
leq = lambda x, y: x <= y

# 4. Build forward/backward closure nuclei from that preorder
cf = E.up_closure(leq)     # upward closure
cb = E.down_closure(leq)   # downward closure

# 5. Get their interiors
i_f, i_b = interiors_forward_backward(cf, cb, E)

# 6. Compose the modalities C = i_f ∘ c_b, M = i_b ∘ c_f
C = C_composite(i_f, cb)
M = M_composite(i_b, cf)

# 7. Make the KZ-comonad G = i_f ∘ c_f
G = KZComonad(cf, i_f)

# 8. Grab all subsets of the universe (the powerset)
subsets = E.power_set()

# 9. Check if the forward/backward nuclei commute
print("Do c_f and c_b commute?", commute(cf, cb, subsets))

# 10. Run the closure tower to see where it stabilizes
tower, idx = closure_tower([cf, cb], subsets)
print("Tower stabilized after", idx, "iterations.")
print("Fixpoint families sequence:")
for step, fam in enumerate(tower):
    print(f" Step {step}: {len(fam)} elements")

# 11. Factorization example: pick two subsets
A = frozenset([0])
B = frozenset([1,2])
x, mid, y, cstab, mstab = factorize_CM(A, B, C, M)
print("Factorization CM:")
print(" x =", x, "mid =", mid, "y =", y)
print("  C-stable?", cstab, "M-stable?", mstab)

# 12. Try the toy presheaf cell
P = PCell(["a","b"], ["x","y"], {"x":"a","y":"b"})
print("PCell X0:", P.X0, "X1:", P.X1)
Pa = pcell_a_f(P)
Pb = pcell_a_b(P)
print("a_f -> new X0:", Pa.X0)
print("a_b -> new X1:", Pb.X1)
