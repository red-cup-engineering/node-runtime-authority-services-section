"""Rewriter engine for executing runbooks.

The engine orchestrates runbook execution, managing the execution plan,
handler dispatch, and result aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Type
from uuid import UUID, uuid4

from app.schemas.runbook import RunbookCreate, RunbookStep, StepStatus
from app.runbooks.resolver import DependencyResolver, ExecutionPlan
from app.rewriter.handlers import (
    ActHandler,
    ExecutionContext,
    HandlerRegistry,
    HandlerResult,
)
from app.rewriter.act_bindings import ACT_BINDINGS, ActBinding


@dataclass
class StepResult:
    """Result of executing a single runbook step."""
    
    step_id: str
    status: StepStatus
    outputs: dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    executed_acts: list[str] = field(default_factory=list)
    recognitions_created: list[UUID] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "outputs": self.outputs,
            "error_message": self.error_message,
            "executed_acts": self.executed_acts,
            "recognitions_created": [str(r) for r in self.recognitions_created],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ExecutionResult:
    """Result of executing an entire runbook."""
    
    runbook_name: str
    execution_id: UUID
    trace_id: UUID
    status: str
    step_results: dict[str, StepResult] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def is_success(self) -> bool:
        return self.status == "completed"
    
    def failed_steps(self) -> list[str]:
        return [
            step_id for step_id, result in self.step_results.items()
            if result.status == StepStatus.FAILED
        ]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "runbook_name": self.runbook_name,
            "execution_id": str(self.execution_id),
            "trace_id": str(self.trace_id),
            "status": self.status,
            "step_results": {
                step_id: result.to_dict()
                for step_id, result in self.step_results.items()
            },
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


class RewriterEngine:
    """Engine for executing runbooks."""
    
    def __init__(
        self,
        registry: Optional[HandlerRegistry] = None,
        db: Any = None,
        measurement_fabric: Any = None,
        known_acts: Optional[set[str]] = None,
        persist_recognitions: bool = True,
        recognition_repo: Any = None,
    ):
        self.registry = registry or HandlerRegistry.get_instance()
        self.db = db
        self.measurement_fabric = measurement_fabric
        self.known_acts = known_acts or set()
        self.persist_recognitions = persist_recognitions
        self.recognition_repo = recognition_repo
    
    async def execute(
        self,
        runbook: RunbookCreate,
        inputs: Optional[dict[str, Any]] = None,
        trace_id: Optional[UUID] = None,
    ) -> ExecutionResult:
        """Execute a runbook.
        
        Args:
            runbook: The runbook to execute.
            inputs: Input parameters for the runbook.
            trace_id: Optional trace ID for distributed tracing.
        
        Returns:
            ExecutionResult with step results and status.
        """
        execution_id = uuid4()
        trace_id = trace_id or uuid4()
        inputs = inputs or {}
        
        result = ExecutionResult(
            runbook_name=runbook.name,
            execution_id=execution_id,
            trace_id=trace_id,
            status="running",
            started_at=datetime.utcnow(),
        )
        
        try:
            resolver = DependencyResolver(runbook)
            plan = resolver.resolve()
        except ValueError as e:
            result.status = "failed"
            result.error_message = f"Dependency resolution failed: {e}"
            result.completed_at = datetime.utcnow()
            return result
        
        step_outputs: dict[str, dict[str, Any]] = {}
        
        for stage in plan.stages:
            stage_results = await self._execute_stage(
                stage.step_ids,
                plan,
                inputs,
                step_outputs,
                trace_id,
            )
            
            for step_id, step_result in stage_results.items():
                result.step_results[step_id] = step_result
                if step_result.status == StepStatus.COMPLETED:
                    step_outputs[step_id] = step_result.outputs
            
            failed = [
                sid for sid, sr in stage_results.items()
                if sr.status == StepStatus.FAILED
            ]
            if failed:
                result.status = "failed"
                result.error_message = f"Steps failed: {failed}"
                result.completed_at = datetime.utcnow()
                return result
        
        result.status = "completed"
        result.completed_at = datetime.utcnow()
        return result
    
    async def _execute_stage(
        self,
        step_ids: list[str],
        plan: ExecutionPlan,
        inputs: dict[str, Any],
        step_outputs: dict[str, dict[str, Any]],
        trace_id: UUID,
    ) -> dict[str, StepResult]:
        """Execute a stage of steps (potentially in parallel)."""
        results: dict[str, StepResult] = {}
        
        for step_id in step_ids:
            step = plan.get_step(step_id)
            if not step:
                results[step_id] = StepResult(
                    step_id=step_id,
                    status=StepStatus.FAILED,
                    error_message=f"Step not found: {step_id}",
                )
                continue
            
            step_inputs = self._resolve_inputs(step, inputs, step_outputs)
            
            if step.condition:
                if not self._evaluate_condition(step.condition, step_inputs):
                    results[step_id] = StepResult(
                        step_id=step_id,
                        status=StepStatus.SKIPPED,
                    )
                    continue
            
            results[step_id] = await self._execute_step(
                step, step_inputs, trace_id
            )
        
        return results
    
    async def _execute_step(
        self,
        step: RunbookStep,
        inputs: dict[str, Any],
        trace_id: UUID,
    ) -> StepResult:
        """Execute a single step."""
        result = StepResult(
            step_id=step.id,
            status=StepStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        context = ExecutionContext(
            trace_id=trace_id,
            step_id=step.id,
            inputs=inputs,
            db=self.db,
            measurement_fabric=self.measurement_fabric,
            known_acts=self.known_acts,
            recognition_repo=self.recognition_repo,
            persist_recognitions=self.persist_recognitions,
        )
        
        all_outputs: dict[str, Any] = {}
        all_recognitions: list[UUID] = []
        
        for act in step.acts:
            handler = self.registry.get_handler(act)
            
            if handler is None:
                result.status = StepStatus.FAILED
                result.error_message = f"No handler registered for act: {act}"
                result.completed_at = datetime.utcnow()
                return result
            
            validation_error = handler.validate_inputs(context)
            if validation_error:
                result.status = StepStatus.FAILED
                result.error_message = f"Input validation failed for {act}: {validation_error}"
                result.completed_at = datetime.utcnow()
                return result
            
            # Enforce any declared input schema for this act.
            binding: Optional[ActBinding] = ACT_BINDINGS.get(act)
            if binding and binding.input_schema:
                # Validate all inputs against the expected schema if they
                # are passed as a single payload named after the schema.
                # This is intentionally conservative: if the schema does
                # not match, the handler will still see raw inputs.
                schema: Type = binding.input_schema
                for value in inputs.values():
                    # Only attempt validation for dict-like payloads
                    # to avoid surprising behaviour on primitives.
                    if isinstance(value, dict):
                        try:
                            schema.model_validate(value)  # type: ignore[attr-defined]
                        except Exception as e:
                            result.status = StepStatus.FAILED
                            result.error_message = (
                                f"Input schema validation failed for act '{act}': {e}"
                            )
                            result.completed_at = datetime.utcnow()
                            return result
            
            handler_result = await handler.execute(act, context)
            result.executed_acts.append(act)
            
            if not handler_result.success:
                result.status = StepStatus.FAILED
                result.error_message = handler_result.error_message
                result.completed_at = datetime.utcnow()
                return result
            
            all_outputs.update(handler_result.outputs)
            all_recognitions.extend(handler_result.recognitions_created)
            
            for name, value in handler_result.outputs.items():
                context.set_output(step.id, name, value)
        
        result.status = StepStatus.COMPLETED
        result.outputs = all_outputs
        result.recognitions_created = all_recognitions
        result.completed_at = datetime.utcnow()
        
        if result.started_at and result.completed_at:
            delta = result.completed_at - result.started_at
            result.duration_ms = delta.total_seconds() * 1000
        
        return result
    
    def _resolve_inputs(
        self,
        step: RunbookStep,
        global_inputs: dict[str, Any],
        step_outputs: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Resolve inputs for a step from global inputs and previous outputs."""
        resolved: dict[str, Any] = dict(global_inputs)
        
        for inp in step.inputs:
            if inp.from_step:
                # Support nested paths like "step_id.output.payload.field"
                parts = inp.from_step.split(".")
                if len(parts) >= 2:
                    step_id, *path = parts
                    if step_id in step_outputs:
                        value: Any = step_outputs[step_id]
                        for key in path:
                            if isinstance(value, dict):
                                value = value.get(key)
                            else:
                                value = None
                                break
                        # If the resolved value is not None, use it directly.
                        # If the resolved value is a dict and the input is marked
                        # as list-typed (convention: name ends with 's'), wrap it
                        # in a singleton list so handlers expecting a list of
                        # payloads (e.g. compose-discipline, compose-filter)
                        # receive the right shape.
                        if value is not None:
                            if isinstance(value, dict) and inp.name.endswith("s"):
                                resolved[inp.name] = [value]
                            else:
                                resolved[inp.name] = value
                        elif inp.default is not None:
                            resolved[inp.name] = inp.default
                elif inp.default is not None:
                    resolved[inp.name] = inp.default
            elif inp.name not in resolved and inp.default is not None:
                resolved[inp.name] = inp.default
        
        return resolved
    
    def _evaluate_condition(
        self,
        condition: str,
        inputs: dict[str, Any],
    ) -> bool:
        """Evaluate a condition expression.
        
        Note: This is a simplified implementation. Production code
        should use a proper expression evaluator.
        """
        try:
            safe_names = {
                k: v for k, v in inputs.items()
                if isinstance(k, str) and k.isidentifier()
            }
            return bool(eval(condition, {"__builtins__": {}}, safe_names))
        except Exception:
            return True
