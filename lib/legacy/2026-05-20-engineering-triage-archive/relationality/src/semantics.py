from __future__ import annotations

"""
Semantic operations and annotation interpretation.

This module contains the core j/G‑closure machinery, evaluation logic,
and the annotation interpreter registry used when constructing concept
feature sets.
"""

from typing import Any, Callable, Dict, List, Set

from .model import AnnotationTerm, Atom, AtomId, Concept, FeatureSet, Universe

# ----------------------------
# Semiotic core
# ----------------------------


def intern_atom(universe: Universe, kind: str, value: str) -> AtomId:
    """Intern (kind,value) → atom id, constructing atoms as needed."""
    key = (kind, value)
    if key in universe.atom_index:
        return universe.atom_index[key]
    atom_id = universe.next_atom_id
    universe.next_atom_id += 1
    universe.atom_index[key] = atom_id
    universe.atoms[atom_id] = Atom(id=atom_id, kind=kind, value=value)
    return atom_id


def j_closure(universe: Universe, features: FeatureSet) -> FeatureSet:
    """Compute j-closure (graph reachability) ensuring extensivity, monotonicity, idempotence."""
    closure: Set[int] = set(features)
    frontier: List[int] = list(features)
    while frontier:
        aid = frontier.pop()
        for nxt in universe.j_relations.get(aid, set()):
            if nxt not in closure:
                closure.add(nxt)
                frontier.append(nxt)
    return frozenset(closure)


def temporal_atoms(universe: Universe, concept: Concept) -> FeatureSet:
    """Derive temporal/provenance atoms from created/updated metadata (Heyting trace witness)."""
    atoms: Set[int] = set()
    if concept.created:
        atoms.add(intern_atom(universe, "created", concept.created))
        atoms.add(intern_atom(universe, "created_year", concept.created[:4]))
    if concept.updated:
        atoms.add(intern_atom(universe, "updated", concept.updated))
        atoms.add(intern_atom(universe, "updated_year", concept.updated[:4]))
    return frozenset(atoms)


def G_trace(universe: Universe, concept: Concept, features: FeatureSet) -> FeatureSet:
    """Trace comonad G: enrich features with temporal atoms to approximate provenance semantics."""
    enriched = set(features)
    enriched.update(temporal_atoms(universe, concept))
    return frozenset(enriched)


def closure_with_jG(universe: Universe, concept: Concept, seed: FeatureSet) -> FeatureSet:
    """Iteratively apply G then j to reach a fixed point (fragment/semantic closure)."""
    current = set(seed)
    changed = True
    while changed:
        before = frozenset(current)
        after = j_closure(universe, G_trace(universe, concept, frozenset(current)))
        current = set(after)
        changed = before != after
    return frozenset(current)


def build_concept_fragment(universe: Universe, concept: Concept) -> FeatureSet:
    """Compute fragment F_{k,X} as least j,G-closed feature set containing annotations."""
    concept.fragment = closure_with_jG(universe, concept, concept.base_features)
    return concept.fragment


def build_concept_semantics(universe: Universe, concept: Concept) -> FeatureSet:
    """Compute semantic contribution Sem_X(k) as one more closure step over fragment."""
    concept.semantic = closure_with_jG(universe, concept, concept.fragment)
    return concept.semantic


def semantic_delta(a: Concept, b: Concept) -> FeatureSet:
    """Delta_sem(k,k') = semantics(b) \\ semantics(a)."""
    return frozenset(b.semantic - a.semantic)


def evaluate_concept(universe: Universe, concept: Concept) -> float:
    """Evaluate concept via simple monoid score (#tags + 0.5 * #links)."""
    tags = 0
    links = 0
    facts = 0
    temporal = 0
    for aid in concept.semantic:
        atom = universe.atoms[aid]
        if atom.kind == "tag":
            tags += 1
        elif atom.kind == "link":
            links += 1
        elif atom.kind == "fact":
            facts += 1
        elif atom.kind in {"created_year", "updated_year"}:
            temporal += 1
    score = float(tags + 0.5 * links + 0.3 * facts + 0.1 * temporal)
    concept.evaluation_score = score
    return score


def evaluation_components(universe: Universe, concept: Concept) -> Dict[str, Any]:
    """Recover evaluation components used for a concept's score."""
    tags = 0
    links = 0
    facts = 0
    temporal = 0
    for aid in concept.semantic:
        atom = universe.atoms[aid]
        if atom.kind == "tag":
            tags += 1
        elif atom.kind == "link":
            links += 1
        elif atom.kind == "fact":
            facts += 1
        elif atom.kind in {"created_year", "updated_year"}:
            temporal += 1
    score = float(tags + 0.5 * links + 0.3 * facts + 0.1 * temporal)
    return {
        "tags": tags,
        "links": links,
        "facts": facts,
        "temporal_years": temporal,
        "score": score,
    }


def evaluation_label(score: float) -> str:
    """Qualitative label for evaluation score bands."""
    if score <= 1.0:
        return "sparsely connected"
    if score <= 3.0:
        return "moderately connected"
    return "densely connected"


# ----------------------------
# Annotation interpretation
# ----------------------------

ANNOTATION_INTERPRETERS: Dict[str, Callable[[Universe, Concept, AnnotationTerm], FeatureSet]] = {}


def register_annotation(op: str):
    """Decorator to register annotation interpreter."""

    def wrapper(func: Callable[[Universe, Concept, AnnotationTerm], FeatureSet]):
        ANNOTATION_INTERPRETERS[op] = func
        return func

    return wrapper


@register_annotation("HasTag")
def interpret_tag(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    atom_id = intern_atom(universe, "tag", term.args[0])
    return frozenset({atom_id})


@register_annotation("InFolder")
def interpret_folder(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    atom_id = intern_atom(universe, "folder", term.args[0])
    return frozenset({atom_id})


@register_annotation("LinksTo")
def interpret_link(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    atom_id = intern_atom(universe, "link", term.args[0])
    return frozenset({atom_id})


@register_annotation("HasStatus")
def interpret_status(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    atom_id = intern_atom(universe, "status", term.args[0])
    return frozenset({atom_id})


@register_annotation("HasType")
def interpret_type(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    atom_id = intern_atom(universe, "type", term.args[0])
    return frozenset({atom_id})


@register_annotation("AliasFor")
def interpret_alias(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    atom_id = intern_atom(universe, "alias", term.args[0])
    return frozenset({atom_id})


@register_annotation("Fact")
def interpret_fact(universe: Universe, concept: Concept, term: AnnotationTerm) -> FeatureSet:
    """Interpret predicate(subject, object) as a fact atom."""
    predicate, subject_id, object_id = term.args
    atom_value = f"{predicate}:{subject_id}->{object_id}"
    atom_id = intern_atom(universe, "fact", atom_value)
    return frozenset({atom_id})


def interpret_annotations(universe: Universe, concept: Concept) -> FeatureSet:
    """Interpret annotation terms into base feature set."""
    features: Set[int] = set()
    for term in concept.annotations:
        interpreter = ANNOTATION_INTERPRETERS.get(term.op)
        if interpreter:
            features.update(interpreter(universe, concept, term))
    concept.base_features = frozenset(features)
    return concept.base_features


__all__ = [
    "intern_atom",
    "j_closure",
    "temporal_atoms",
    "G_trace",
    "closure_with_jG",
    "build_concept_fragment",
    "build_concept_semantics",
    "semantic_delta",
    "evaluate_concept",
    "evaluation_components",
    "evaluation_label",
    "ANNOTATION_INTERPRETERS",
    "register_annotation",
    "interpret_annotations",
]

