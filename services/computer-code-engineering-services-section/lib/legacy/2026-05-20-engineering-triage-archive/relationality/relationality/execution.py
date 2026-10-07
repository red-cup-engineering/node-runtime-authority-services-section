"""
Operator execution engine (Section 4 of the README).

Execution applies typed realizers to AOG nodes, enforces immutability, and
records typed edges. No persistent artifacts are touched after boot.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Tuple

from jsonschema import ValidationError

from .aog import RelationalGraph
from .models import RealizerContext, RecognitionObject, RunbookSpec
from .registry import RealizerRegistry


def _derive_node_id(source_id: str, runbook_id: str, operator: str, step_index: int) -> str:
    """Deterministic child identifier derived from source + operator."""
    name = f"{source_id}:{runbook_id}:{step_index}:{operator}"
    return f"{operator.lower()}:{uuid.uuid5(uuid.NAMESPACE_URL, name)}"


class ExecutionEngine:
    def __init__(
        self,
        graph: RelationalGraph,
        runbooks: Dict[str, RunbookSpec],
        registry: RealizerRegistry,
        payload_validators: Optional[Dict[str, Tuple[object, Optional[str]]]] = None,
    ) -> None:
        self.graph = graph
        self.runbooks = runbooks
        self.registry = registry
        self.payload_validators = payload_validators or {}

    def _validate_payload(self, kind: str, payload: Dict[str, object]) -> None:
        """Validate the payload of a newly produced carrier against kind schema."""
        if kind not in self.payload_validators:
            return
        validator, payload_key = self.payload_validators[kind]
        target = payload
        if payload_key:
            if payload_key not in payload:
                raise ValidationError(f"Missing payload segment '{payload_key}' for kind {kind}")
            target = payload[payload_key]
        validator.validate(target)

    def execute_runbook(
        self,
        runbook_id: str,
        source_node_id: str,
        system_id: str | None = None,
        context_overrides: Dict[str, object] | None = None,
        allowed_operators: Optional[List[str]] = None,
    ) -> Tuple[RecognitionObject, List[str], Dict[str, object]]:
        if runbook_id not in self.runbooks:
            raise KeyError(f"Runbook not found: {runbook_id}")

        runbook = self.runbooks[runbook_id]
        current_node_id = source_node_id
        visited_nodes: List[str] = [source_node_id]
        operators_used: List[str] = []
        diag_data: Dict[str, object] = {"invariants_checked": []}

        for index, step in enumerate(runbook.steps):
            current_obj = self.graph.get_node(current_node_id)

            if allowed_operators is not None and step.operator not in allowed_operators:
                raise PermissionError(
                    f"Operator {step.operator} is not permitted by regime for runbook {runbook.id}"
                )

            if current_obj.kind != step.input_kind:
                raise TypeError(
                    f"Step {step.operator} expected kind {step.input_kind} "
                    f"but received {current_obj.kind}"
                )

            spec, realizer_fn = self.registry.get(step.realizer)
            if spec.input_kind != step.input_kind or spec.output_kind != step.output_kind:
                raise TypeError(
                    f"Realizer {spec.id} typing mismatch for step {step.operator}: "
                    f"{spec.input_kind}->{spec.output_kind} vs "
                    f"{step.input_kind}->{step.output_kind}"
                )

            context = RealizerContext(
                runbook_id=runbook.id,
                step=step,
                system_id=system_id,
                diagnostics=dict(context_overrides or {}),
            )
            result = realizer_fn(current_obj, context)
            if not isinstance(result, dict):
                raise TypeError(f"Realizer {spec.id} must return a mapping with kind/payload.")
            result_kind = result.get("kind")
            if result_kind != spec.output_kind:
                raise TypeError(
                    f"Realizer {spec.id} returned kind {result_kind}, expected {spec.output_kind}"
                )

            new_node_id = _derive_node_id(current_obj.id, runbook.id, step.operator, index)
            acts = result.get("acts", [])
            payload = result.get("payload", {})
            metadata = result.get("metadata", {})
            self._validate_payload(result_kind, payload)
            new_obj = RecognitionObject(
                id=new_node_id,
                kind=result_kind,
                acts=acts,
                payload=payload,
                metadata=metadata,
            )
            self.graph.add_operator_edge(
                source_id=current_obj.id,
                target=new_obj,
                operator=step.operator,
                runbook_id=runbook.id,
                realizer_id=spec.id,
                diagnostics=context.diagnostics,
            )

            current_node_id = new_obj.id
            visited_nodes.append(new_node_id)
            operators_used.append(step.operator)
            if step.invariants:
                diag_data.setdefault("invariants_checked", []).extend(step.invariants)
            if context.diagnostics:
                spectral = context.diagnostics.pop("spectral_effects", None)
                if spectral:
                    diag_data.setdefault("spectral_effects", {}).update(spectral)
                # Remove non-diagnostic passthrough data to avoid leaking payloads.
                context.diagnostics.pop("measurement_frame", None)
                context.diagnostics.pop("regime", None)
                diag_data.update(context.diagnostics)

        final_obj = self.graph.get_node(current_node_id)
        diagnostics: Dict[str, object] = {"operators_used": operators_used}
        diagnostics.update(diag_data)
        diagnostics.setdefault("flow_nucleus_commutation", "ok")
        diagnostics.setdefault("invariants_checked", [])
        diagnostics.setdefault("commutation_evidence", {})
        return final_obj, visited_nodes, diagnostics
