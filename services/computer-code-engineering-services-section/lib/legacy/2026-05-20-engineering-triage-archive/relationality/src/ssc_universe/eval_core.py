from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from .annterm import FAIL_BOTTOM, AnnTerm, FailureTerm
from .config import UniverseConfig
from .identity import IdentityGroupoid
from .ingest import Ingestor
from .repo import compute_repo_fingerprint
from .sscu_model import (
    ClosureTrace,
    Concept,
    Fragment,
    SemanticContribution,
    UniverseInstance,
)


@dataclass
class EvaluationOptions:
    mode: str
    sanitize_html: bool
    html_lang: str


class Evaluator:
    def __init__(self, config: UniverseConfig, options: EvaluationOptions):
        self.config = config
        self.options = options

    def evaluate(self, root: Path, reporter=None) -> UniverseInstance:
        sources_pattern = self.config.data["sources"]
        ingestor = Ingestor(sources_pattern)
        if reporter:
            reporter.section("Evaluation")
            reporter.info(f"Scanning sources pattern '{sources_pattern}'")
        ingest = ingestor.load(root)
        if reporter:
            reporter.success(
                f"Loaded {len(ingest.concepts)} concepts from {len(ingest.paths)} files"
            )
        groupoid = IdentityGroupoid.from_same_as(ingest.same_as)

        fragments: Dict[str, Fragment] = {}
        sem: Dict[str, SemanticContribution] = {}
        failures: Set[object] = set()
        unresolved: List[Tuple[str, str]] = []
        reference_graph: Dict[str, Set[str]] = {}

        concepts = ingest.concepts
        source_paths: Dict[str, str] = dict(ingest.paths)
        class_map: Dict[str, List[Concept]] = {}
        for concept in concepts.values():
            rep = groupoid.representative(concept.const)
            class_map.setdefault(rep, []).append(concept)

        canonical_concepts: Dict[str, Concept] = {}
        known_reps = set(class_map.keys())
        for rep, members in class_map.items():
            aggregated = self._aggregate_concepts(rep, members)
            canonical_concepts[rep] = aggregated
            fragment, closure, failure_elements, unresolved_refs, refs = self._evaluate_concept(
                aggregated, groupoid, known_reps
            )
            fragments[rep] = fragment
            sem[rep] = SemanticContribution(fragment=fragment, closure_trace=closure)
            failures.update(failure_elements)
            unresolved.extend(unresolved_refs)
            reference_graph[rep] = refs
            for member in members:
                chosen_path = ingest.paths.get(member.const)
                if chosen_path:
                    source_paths.setdefault(rep, chosen_path)
                    break

        # unresolved refs fail build in strict mode
        if unresolved and self.options.mode == "strict":
            if reporter:
                reporter.error("Unresolved references block strict mode")
                for src, target in unresolved:
                    path = source_paths.get(src) or source_paths.get(groupoid.representative(src))
                    detail = f"{src} -> {target}"
                    if path:
                        detail += f" (from {path})"
                    reporter.detail(detail)
            formatted = "; ".join(
                f"{src} -> {target}" + (
                    f" (from {source_paths.get(src) or source_paths.get(groupoid.representative(src))})"
                    if (source_paths.get(src) or source_paths.get(groupoid.representative(src)))
                    else ""
                )
                for src, target in unresolved
            )
            raise ValueError(
                f"Unresolved references in strict mode ({len(unresolved)}): {formatted}"
            )

        fingerprint = compute_repo_fingerprint(root)

        return UniverseInstance(
            concepts=concepts,
            canonical_concepts=canonical_concepts,
            equivalence_classes={rep: sorted(values) for rep, values in groupoid.classes.items()},
            groupoid_rep=groupoid.rep_for,
            fragments=fragments,
            sem=sem,
            failures=failures,
            unresolved=unresolved,
            reference_graph=reference_graph,
            config_hash=self.config.hash(),
            repo_fingerprint=fingerprint,
            sanitize_html=self.options.sanitize_html,
            html_lang=self.options.html_lang,
            source_paths=source_paths,
        )

    def _aggregate_concepts(self, representative: str, concepts: Iterable[Concept]) -> Concept:
        ordered = sorted(concepts, key=lambda c: (c.const != representative, c.const))
        primary = ordered[0]
        tags: Set[str] = set()
        ann_terms = []
        same_as: Set[str] = set()
        publish = primary.publish
        publish_to: Set[str] = set(primary.publish_to or [])
        status = primary.status
        for concept in ordered:
            tags.update(concept.tags)
            ann_terms.extend(concept.ann)
            same_as.update(concept.same_as)
            if publish is None:
                publish = concept.publish
            publish_to.update(concept.publish_to or [])
            if status is None:
                status = concept.status
        same_as.update(c.const for c in ordered)
        same_as.discard(representative)
        return Concept(
            const=representative,
            title=primary.title,
            tags=sorted(tags),
            ann=ann_terms,
            body=primary.body,
            same_as=sorted(same_as),
            publish=publish,
            publish_to=sorted(publish_to),
            status=status,
        )

    def _evaluate_concept(
        self,
        concept: Concept,
        groupoid: IdentityGroupoid,
        known_consts: Set[str],
    ) -> Tuple[Fragment, ClosureTrace, Set[object], List[Tuple[str, str]], Set[str]]:
        generators = []
        provenance_map = {}
        failure_elements: Set[object] = set()
        unresolved_refs: List[Tuple[str, str]] = []
        refs: Set[str] = set()

        for term in concept.ann:
            value, prov = term.interpret(groupoid.transport)
            generators.append((value, prov))
            provenance_map[value] = prov
            if isinstance(term, FailureTerm) or value == ("fail", "unparseable"):
                failure_elements.add(FAIL_BOTTOM)
            if isinstance(term, FailureTerm):
                continue
            if getattr(term, "target", None):
                rep = groupoid.transport(term.target)
                refs.add(rep)
                if rep not in known_consts:
                    unresolved_refs.append((concept.const, rep))
                    failure_elements.add(("ref-missing", rep))

        is_failure = bool(failure_elements) or any(val == FAIL_BOTTOM for val, _ in generators)
        elements = set()
        if is_failure:
            elements = {FAIL_BOTTOM}
        else:
            for val, _ in generators:
                elements.add(val)

        fragment = Fragment(generators=generators, elements=elements, is_failure=is_failure, provenance=provenance_map)
        closure_trace = ClosureTrace(steps=["S applied; v0 conservative closure (fixpoint)"])
        if is_failure:
            failure_elements.add(FAIL_BOTTOM)
        return fragment, closure_trace, failure_elements, unresolved_refs, refs
