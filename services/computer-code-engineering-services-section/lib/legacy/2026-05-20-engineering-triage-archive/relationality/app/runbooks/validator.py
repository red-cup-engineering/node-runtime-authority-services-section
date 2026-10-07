"""Runbook validation against the runtime instruction set.

Ensures all acts referenced in a runbook exist in the live
rewriter/act bindings and validates basic structural properties.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional, Set

from app.schemas.runbook import RunbookCreate, RunbookStep
from app.rewriter.act_bindings import ACT_BINDINGS, ActBinding
from app.rewriter.handlers import HandlerRegistry


@dataclass
class ValidationResult:
    """Result of runbook validation."""
    
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    referenced_acts: set[str] = field(default_factory=set)
    missing_acts: set[str] = field(default_factory=set)
    
    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        self.warnings.append(message)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "referenced_acts": sorted(self.referenced_acts),
            "missing_acts": sorted(self.missing_acts),
        }


class RunbookValidator:
    """Validates runbooks against the live instruction set (acts/handlers)."""

    def __init__(self) -> None:
        self._known_acts: Optional[set[str]] = None
    
    @property
    def known_acts(self) -> set[str]:
        """Get the set of known act slugs (from handlers + bindings)."""
        if self._known_acts is None:
            registry = HandlerRegistry.get_instance()
            handled = set(registry.list_handled_acts())
            bound = set(ACT_BINDINGS.keys())
            self._known_acts = handled | bound
        return self._known_acts
    
    def get_act_info(self, slug: str) -> Optional[dict]:
        """Get basic information about an act by slug.

        Currently returns a minimal record derived from bindings;
        this method is kept for backwards compatibility.
        """
        if slug not in self.known_acts:
            return None
        binding = ACT_BINDINGS.get(slug)
        return {
            "id": f"act:{slug}",
            "type": "act",
            "input_schema": getattr(binding.input_schema, "__name__", None)
            if binding and binding.input_schema
            else None,
            "output_schema": getattr(binding.output_schema, "__name__", None)
            if binding and binding.output_schema
            else None,
        }
    
    def validate(self, runbook: RunbookCreate) -> ValidationResult:
        """Validate a runbook against the knowledge graph.
        
        Args:
            runbook: The runbook to validate.
        
        Returns:
            ValidationResult with detailed information.
        """
        result = ValidationResult(is_valid=True)
        
        for step in runbook.steps:
            for act in step.acts:
                result.referenced_acts.add(act)
                if act not in self.known_acts:
                    result.missing_acts.add(act)
        
        if result.missing_acts:
            result.add_error(
                f"Unknown acts referenced: {sorted(result.missing_acts)}"
            )
        
        step_ids = set()
        for step in runbook.steps:
            if step.id in step_ids:
                result.add_error(f"Duplicate step ID: '{step.id}'")
            step_ids.add(step.id)
        
        for step in runbook.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    result.add_error(
                        f"Step '{step.id}' depends on unknown step: '{dep}'"
                    )
        
        if self._has_cycle(runbook.steps):
            result.add_error("Circular dependency detected in step graph")
        
        for step in runbook.steps:
            for inp in step.inputs:
                if inp.from_step:
                    parts = inp.from_step.split(".", 1)
                    if len(parts) != 2:
                        result.add_error(
                            f"Step '{step.id}' input '{inp.name}' has invalid "
                            f"from_step reference: '{inp.from_step}' (expected 'step_id.output_name')"
                        )
                    elif parts[0] not in step_ids:
                        result.add_error(
                            f"Step '{step.id}' input '{inp.name}' references "
                            f"unknown step: '{parts[0]}'"
                        )
        
        if not runbook.policy_requirements:
            result.add_warning("Runbook has no policy requirements defined")
        
        for step in runbook.steps:
            if len(step.acts) > 1:
                result.add_warning(
                    f"Step '{step.id}' maps to multiple acts - consider splitting"
                )
            # Static type hints from ACT_BINDINGS: if a step declares
            # inputs from previous steps, check that the bound output
            # schemas are compatible with bound input schemas where
            # both are known.
            bound_input_schemas: list[type] = []
            bound_output_schemas: dict[str, type] = {}

            for act in step.acts:
                binding: Optional[ActBinding] = ACT_BINDINGS.get(act)
                if binding and binding.input_schema:
                    bound_input_schemas.append(binding.input_schema)

            # Build a map of output schemas for all previous steps.
            for prev in runbook.steps:
                for act in prev.acts:
                    binding = ACT_BINDINGS.get(act)
                    if binding and binding.output_schema:
                        # Each output name is step-specific in practice;
                        # here we only note that the step yields this type.
                        bound_output_schemas[prev.id] = binding.output_schema

            for inp in step.inputs:
                if inp.from_step:
                    parts = inp.from_step.split(".", 1)
                    if len(parts) == 2:
                        from_step_id, _ = parts
                        out_schema = bound_output_schemas.get(from_step_id)
                        for in_schema in bound_input_schemas:
                            if out_schema and out_schema is not in_schema:
                                result.add_warning(
                                    f"Step '{step.id}' input '{inp.name}' expects {in_schema.__name__} "
                                    f"but step '{from_step_id}' is bound to {out_schema.__name__}"
                                )
        
        return result
    
    def _has_cycle(self, steps: list[RunbookStep]) -> bool:
        """Check if the step dependency graph has a cycle."""
        step_map = {s.id: s for s in steps}
        visited: set[str] = set()
        rec_stack: set[str] = set()
        
        def dfs(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)
            
            step = step_map.get(step_id)
            if step:
                for dep in step.depends_on:
                    if dep not in visited:
                        if dfs(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            
            rec_stack.remove(step_id)
            return False
        
        for step in steps:
            if step.id not in visited:
                if dfs(step.id):
                    return True
        
        return False
    
    def get_act_dependencies(self, act_slug: str) -> list[str]:
        """Get the acts that a given act depends on.

        Currently returns an empty list; this hook can be enriched later
        from runtime introspection or earned dependency theorems.
        """
        return []
