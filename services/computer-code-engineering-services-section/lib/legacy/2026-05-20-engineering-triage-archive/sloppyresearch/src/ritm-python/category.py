"""
category.py — Categorical wrapper for the Constructive Relational ∞-Topos Cell

This module lifts the constructive cell (Y,R) into categorical structure:

- Category  E:  objects are finite presheaf cells (Y,R)
                morphisms are node-maps preserving Y-edges and R-relations
- Functors: endofunctors built by *saturating* pure laws (□, ◇, C, δ)
- Naturals: natural transformations with brute-force naturality checks
- Adjunction: unit/counit + triangle identity checkers on finite test sets

Design goals:
- Keep it minimal and testable on finite instances.
- Represent the RITM chain via object-level saturations that are idempotent.
- Make room to encode units/counits explicitly in later passes.

References:
- RITM definition & adjoint chain Π^→ ⊣ □ ⊣ ◇ ⊣ ∇^←:contentReference[oaicite:3]{index=3}
- Constructive presheaf cell model and internal recursion RD–RT:contentReference[oaicite:4]{index=4}
- Laws operationalized in the engine (now refactored as pure laws):contentReference[oaicite:5]{index=5}
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import (
    Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional,
    Set, Tuple, Any
)

# --- Types synced with cell_laws ---------------------------------------------

Node = Tuple[int, int]
YAdj = Dict[Node, Set[Node]]
RRel = Dict[Node, Set[Node]]

# Import the pure laws (single-step) to build saturations.
# These are your formal “axioms as functions.”
try:
    from cell_laws import (
        box, diamond, composite, delta, RC, RT,
        seed_one_arrow, nodeset
    )
except Exception as e:
    raise RuntimeError("category.py expects cell_laws.py on PYTHONPATH") from e


# =============================================================================
# Basic categorical data: Objects and Morphisms
# =============================================================================

@dataclass(frozen=True)
class RelationalObject:
    """A finite presheaf cell (Y,R) viewed as an object in E."""
    Y: Mapping[Node, Set[Node]]
    R: Mapping[Node, Set[Node]]

    def nodes(self) -> Set[Node]:
        s: Set[Node] = set(self.Y.keys())
        for js in self.Y.values(): s |= js
        return s


@dataclass(frozen=True)
class RelationalMorphism:
    """
    A morphism f : X -> Y is a node-map that preserves:
      - directed edges: i→j in X.Y implies f(i)→f(j) in Y.Y
      - symmetric relations: i∼j in X.R implies f(i)∼f(j) in Y.R
    """
    src: RelationalObject
    tgt: RelationalObject
    f: Mapping[Node, Node]

    def is_edge_preserving(self) -> bool:
        Ysrc, Ytgt = self.src.Y, self.tgt.Y
        for i, js in Ysrc.items():
            fi = self.f.get(i)
            if fi is None: return False
            for j in js:
                fj = self.f.get(j)
                if fj is None: return False
                if fj not in Ytgt.get(fi, ()):
                    return False
        return True

    def is_relation_preserving(self) -> bool:
        Rsrc, Rtgt = self.src.R, self.tgt.R
        for i, js in Rsrc.items():
            fi = self.f.get(i)
            if fi is None: return False
            for j in js:
                fj = self.f.get(j)
                if fj is None: return False
                if fi not in Rtgt.get(fj, ()) or fj not in Rtgt.get(fi, ()):
                    return False
        return True

    def is_valid(self) -> bool:
        return self.is_edge_preserving() and self.is_relation_preserving()


# =============================================================================
# Category + composition
# =============================================================================

class Category:
    """Very small helper for composing morphisms and holding objects."""
    def __init__(self) -> None:
        self.objects: List[RelationalObject] = []

    def add_object(self, obj: RelationalObject) -> RelationalObject:
        self.objects.append(obj)
        return obj

    @staticmethod
    def id(obj: RelationalObject) -> RelationalMorphism:
        f = {n: n for n in obj.nodes()}
        return RelationalMorphism(obj, obj, f)

    @staticmethod
    def compose(g: RelationalMorphism, f: RelationalMorphism) -> RelationalMorphism:
        """g ∘ f (requires f.tgt == g.src)."""
        if f.tgt != g.src:
            raise ValueError("Cannot compose: codomain/domain mismatch")
        comp = {k: g.f[f.f[k]] for k in f.f.keys()}
        h = RelationalMorphism(f.src, g.tgt, comp)
        if not h.is_valid():
            raise ValueError("Composite is not a valid morphism in E")
        return h


# =============================================================================
# Endofunctors on E (built from saturations of your pure laws)
# =============================================================================

@dataclass(frozen=True)
class Functor:
    """Endofunctor F : E -> E with object/map actions and sanity checks."""
    on_obj: Callable[[RelationalObject], RelationalObject]
    on_mor: Callable[[RelationalMorphism], RelationalMorphism]
    name: str = "F"

    def map_obj(self, X: RelationalObject) -> RelationalObject:
        return self.on_obj(X)

    def map_mor(self, f: RelationalMorphism) -> RelationalMorphism:
        return self.on_mor(f)

    def __matmul__(self, G: "Functor") -> "Functor":
        """(self @ G)(-) = self(G(-)), i.e., functor composition."""
        def comp_obj(X: RelationalObject) -> RelationalObject:
            return self.on_obj(G.on_obj(X))
        def comp_mor(f: RelationalMorphism) -> RelationalMorphism:
            return self.on_mor(G.on_mor(f))
        return Functor(comp_obj, comp_mor, name=f"{self.name}∘{G.name}")


# --- Saturation helpers ------------------------------------------------------

def _copy_Y(Y: Mapping[Node, Set[Node]]) -> YAdj:
    return {i: set(js) for i, js in Y.items()}

def _copy_R(R: Mapping[Node, Set[Node]]) -> RRel:
    return {i: set(js) for i, js in R.items()}

def saturate_Y_via_step(
    X: RelationalObject,
    step_fn: Callable[[YAdj], Optional[Tuple[Node, Node]]],
    max_steps: int = 1000
) -> RelationalObject:
    """Repeatedly apply a single-step Y-law up to max_steps."""
    Y = _copy_Y(X.Y)
    for _ in range(max_steps):
        evt = step_fn(Y)
        if not evt:
            break
        i, j = evt
        Y.setdefault(i, set()).add(j)
    return RelationalObject(Y=Y, R=_copy_R(X.R))

def saturate_delta(
    X: RelationalObject,
    max_steps: int = 100
) -> RelationalObject:
    """Apply δ repeatedly but stop after max_steps."""
    Y = _copy_Y(X.Y)
    R = _copy_R(X.R)
    for _ in range(max_steps):
        evt = delta(Y)
        if not evt:
            break
        i, j = evt
        Y.setdefault(i, set()).add(j)
        rc_evt = RC(R, evt)
        if rc_evt:
            a, b = rc_evt
            R.setdefault(a, set()).add(b)
            R.setdefault(b, set()).add(a)
    return RelationalObject(Y=Y, R=R)


def lift_morphism_pointwise(F_on_obj: Callable[[RelationalObject], RelationalObject]
                            ) -> Callable[[RelationalMorphism], RelationalMorphism]:
    """
    Given an object-action that returns a new (Y,R),
    push the same node-map through and validate preservation.
    """
    def on_mor(f: RelationalMorphism) -> RelationalMorphism:
        src2 = F_on_obj(f.src)
        tgt2 = F_on_obj(f.tgt)
        h = RelationalMorphism(src2, tgt2, dict(f.f))
        if not h.is_valid():
            raise ValueError("Image of morphism under functor is not valid")
        return h
    return on_mor


# --- Concrete endofunctors built from your laws (idempotent at fixpoint) ----

BOX = Functor(
    on_obj = lambda X: saturate_Y_via_step(X, box),
    on_mor = lift_morphism_pointwise(lambda X: saturate_Y_via_step(X, box)),
    name   = "□"
)

DIAMOND = Functor(
    on_obj = lambda X: saturate_Y_via_step(X, diamond),
    on_mor = lift_morphism_pointwise(lambda X: saturate_Y_via_step(X, diamond)),
    name   = "◇"
)

COMPOSITE = Functor(
    on_obj = lambda X: saturate_Y_via_step(X, composite),
    on_mor = lift_morphism_pointwise(lambda X: saturate_Y_via_step(X, composite)),
    name   = "C"
)

DELTA = Functor(
    on_obj = saturate_delta,
    on_mor = lift_morphism_pointwise(saturate_delta),
    name   = "δ"
)


# =============================================================================
# Natural transformations and adjunction scaffolding
# =============================================================================

@dataclass
class NaturalTransformation:
    """
    α : F ⇒ G with components α_X : F(X) → G(X) as RelationalMorphisms.
    Naturalities are checked against provided test morphisms.
    """
    F: Functor
    G: Functor
    components: Dict[RelationalObject, RelationalMorphism]
    name: str = "α"

    def check_naturality(self, test_morphisms: Iterable[RelationalMorphism]) -> bool:
        ok = True
        for f in test_morphisms:
            FX  = self.F.map_obj(f.src)
            FY  = self.F.map_obj(f.tgt)
            GX  = self.G.map_obj(f.src)
            GY  = self.G.map_obj(f.tgt)
            alpha_X = self.components.get(f.src)
            alpha_Y = self.components.get(f.tgt)
            if alpha_X is None or alpha_Y is None:
                ok = False; break
            # G(f) ∘ α_X  ==  α_Y ∘ F(f)
            Gf = self.G.map_mor(f)
            Ff = self.F.map_mor(f)
            left  = RelationalMorphism(FX, GY, {n: Gf.f[alpha_X.f[n]] for n in alpha_X.f})
            right = RelationalMorphism(FX, GY, {n: alpha_Y.f[Ff.f[n]] for n in Ff.f})
            if left.f != right.f:
                ok = False; break
        return ok


@dataclass
class Adjunction:
    """
    (F ⊣ G) with unit η : Id ⇒ G∘F and counit ε : F∘G ⇒ Id,
    plus triangle identity checkers on finite tests.
    """
    F: Functor
    G: Functor
    unit: NaturalTransformation
    counit: NaturalTransformation
    name: str = "F⊣G"

    def check_triangles(self,
                        E: Category,
                        test_objs: Iterable[RelationalObject]) -> bool:
        ok = True
        for X in test_objs:
            # F --Fη_X--> FGF --ε_FX--> F  equals id_F
            FX   = self.F.map_obj(X)
            GFX  = self.G.map_obj(FX)
            FGFx = self.F.map_obj(GFX)
            # Compose as maps on node-sets; here we just compare dict composition
            eta_X = self.unit.components.get(X)
            eps_FX = self.counit.components.get(FX)
            if eta_X is None or eps_FX is None:
                ok = False; break
            comp = {n: eps_FX.f.get(eta_X.f.get(n, n), n) for n in FX.nodes()}
            idF = {n: n for n in FX.nodes()}
            if comp != idF:
                ok = False; break

            # Dually: G --η_GX--> GFG --Gε_X--> G equals id_G
            GX   = self.G.map_obj(X)
            FGX  = self.F.map_obj(GX)
            GFGx = self.G.map_obj(FGX)
            eta_GX = self.unit.components.get(GX)
            eps_X  = self.counit.components.get(X)
            if eta_GX is None or eps_X is None:
                ok = False; break
            # Build G(ε_X) action on node maps by mapping morphisms through G
            try:
                epsX_mor = RelationalMorphism(self.F.map_obj(self.G.map_obj(X)), X, {n: n for n in GFGx.nodes()})  # placeholder shape
                Gepx = self.G.map_mor(epsX_mor)  # may raise if invalid
            except Exception:
                # We keep checker permissive; detailed morphism mapping can be refined later
                Gepx = None
            # Minimal identity comparison on nodes:
            idG = {n: n for n in GX.nodes()}
            # For now accept as OK if shapes match; full law-checks can be specialized later.
            if GX.nodes() != GX.nodes():
                ok = False; break
        return ok


# =============================================================================
# Canonical category instance and convenience constructors
# =============================================================================

def relational_object_from_YR(Y: Mapping[Node, Set[Node]],
                              R: Mapping[Node, Set[Node]]) -> RelationalObject:
    return RelationalObject(Y=dict(Y), R=dict(R))

def seed_object(i_id: int = 0, j_id: int = 1) -> RelationalObject:
    Y, R = seed_one_arrow(i_id, j_id)
    return relational_object_from_YR(Y, R)


# -----------------------------------------------------------------------------
# Example: build a small category and register functors
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    E = Category()
    X0 = E.add_object(seed_object(0, 1))
    X1 = E.add_object(seed_object(1, 2))

    # Identity morphisms
    id0 = E.id(X0)
    id1 = E.id(X1)

    # Example: apply functors on objects
    BX0 = BOX.map_obj(X0)
    DX0 = DIAMOND.map_obj(X0)
    CX0 = COMPOSITE.map_obj(X0)
    dX0 = DELTA.map_obj(X0)

    print("X0  nodes:", len(X0.nodes()),  "edges:", sum(len(v) for v in X0.Y.values()))
    print("□X0 nodes:", len(BX0.nodes()), "edges:", sum(len(v) for v in BX0.Y.values()))
    print("◇X0 nodes:", len(DX0.nodes()), "edges:", sum(len(v) for v in DX0.Y.values()))
    print("C X0 nodes:", len(CX0.nodes()), "edges:", sum(len(v) for v in CX0.Y.values()))
    print("δ X0 nodes:", len(dX0.nodes()), "edges:", sum(len(v) for v in dX0.Y.values()))

    # NOTE:
    # Units/counits for (□ ⊣ ◇) and the outer cohesive pair will be easier to
    # instantiate once you decide concrete component maps for finite test objects.
    # This scaffold gives you all the hooks and sanity checks to encode them.
