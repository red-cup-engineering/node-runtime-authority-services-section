"""Dependency resolution for runbook execution.

Produces an execution plan that respects step dependencies
and enables parallel execution where possible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.schemas.runbook import RunbookCreate, RunbookStep


@dataclass
class ExecutionStage:
    """A stage of execution containing steps that can run in parallel."""
    
    stage_number: int
    step_ids: list[str]
    
    def __repr__(self) -> str:
        return f"Stage({self.stage_number}: {self.step_ids})"


@dataclass
class ExecutionPlan:
    """An ordered execution plan for a runbook."""
    
    runbook_name: str
    stages: list[ExecutionStage] = field(default_factory=list)
    step_order: list[str] = field(default_factory=list)
    step_map: dict[str, RunbookStep] = field(default_factory=dict)
    
    def total_steps(self) -> int:
        return len(self.step_order)
    
    def max_parallelism(self) -> int:
        if not self.stages:
            return 0
        return max(len(stage.step_ids) for stage in self.stages)
    
    def get_step(self, step_id: str) -> Optional[RunbookStep]:
        return self.step_map.get(step_id)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "runbook_name": self.runbook_name,
            "total_steps": self.total_steps(),
            "total_stages": len(self.stages),
            "max_parallelism": self.max_parallelism(),
            "stages": [
                {
                    "stage": stage.stage_number,
                    "steps": stage.step_ids,
                }
                for stage in self.stages
            ],
            "execution_order": self.step_order,
        }


class DependencyResolver:
    """Resolves step dependencies into an execution plan."""
    
    def __init__(self, runbook: RunbookCreate):
        self.runbook = runbook
        self.step_map = {step.id: step for step in runbook.steps}
        self._dependents: dict[str, set[str]] = {}
        self._dependency_count: dict[str, int] = {}
        
        self._build_dependency_graph()
    
    def _build_dependency_graph(self) -> None:
        """Build internal dependency tracking structures."""
        for step in self.runbook.steps:
            self._dependents[step.id] = set()
            self._dependency_count[step.id] = len(step.depends_on)
        
        for step in self.runbook.steps:
            for dep in step.depends_on:
                if dep in self._dependents:
                    self._dependents[dep].add(step.id)
    
    def resolve(self) -> ExecutionPlan:
        """Resolve dependencies into an execution plan.
        
        Uses Kahn's algorithm for topological sorting,
        grouping independent steps into parallel stages.
        
        Returns:
            ExecutionPlan with stages for parallel execution.
        
        Raises:
            ValueError: If a circular dependency is detected.
        """
        plan = ExecutionPlan(
            runbook_name=self.runbook.name,
            step_map=self.step_map.copy(),
        )
        
        remaining_deps = self._dependency_count.copy()
        
        ready = [
            step_id for step_id, count in remaining_deps.items()
            if count == 0
        ]
        
        stage_num = 0
        processed = set()
        
        while ready:
            stage = ExecutionStage(
                stage_number=stage_num,
                step_ids=sorted(ready),
            )
            plan.stages.append(stage)
            
            next_ready = []
            
            for step_id in ready:
                plan.step_order.append(step_id)
                processed.add(step_id)
                
                for dependent in self._dependents.get(step_id, set()):
                    remaining_deps[dependent] -= 1
                    if remaining_deps[dependent] == 0:
                        next_ready.append(dependent)
            
            ready = next_ready
            stage_num += 1
        
        if len(processed) != len(self.step_map):
            unprocessed = set(self.step_map.keys()) - processed
            raise ValueError(
                f"Circular dependency detected. Unable to schedule: {unprocessed}"
            )
        
        return plan
    
    def get_predecessors(self, step_id: str) -> list[str]:
        """Get all steps that must complete before the given step."""
        step = self.step_map.get(step_id)
        if not step:
            return []
        
        predecessors = set()
        to_visit = list(step.depends_on)
        
        while to_visit:
            dep = to_visit.pop()
            if dep not in predecessors and dep in self.step_map:
                predecessors.add(dep)
                dep_step = self.step_map[dep]
                to_visit.extend(dep_step.depends_on)
        
        return sorted(predecessors)
    
    def get_successors(self, step_id: str) -> list[str]:
        """Get all steps that depend on the given step."""
        successors = set()
        to_visit = list(self._dependents.get(step_id, set()))
        
        while to_visit:
            dep = to_visit.pop()
            if dep not in successors:
                successors.add(dep)
                to_visit.extend(self._dependents.get(dep, set()))
        
        return sorted(successors)


def resolve_dependencies(runbook: RunbookCreate) -> ExecutionPlan:
    """Convenience function to resolve a runbook's dependencies.
    
    Args:
        runbook: The runbook to resolve.
    
    Returns:
        ExecutionPlan with stages for parallel execution.
    """
    resolver = DependencyResolver(runbook)
    return resolver.resolve()
