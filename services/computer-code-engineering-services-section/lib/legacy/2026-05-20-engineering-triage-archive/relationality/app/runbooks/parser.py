"""YAML parser for runbook definitions.

Handles loading and parsing of YAML runbook files, converting them
to validated Pydantic models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml

from app.schemas.runbook import RunbookCreate, RunbookStep, StepInput, StepOutput


class RunbookParseError(Exception):
    """Raised when a runbook cannot be parsed."""
    
    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        if self.line is not None:
            if self.column is not None:
                return f"Parse error at line {self.line}, column {self.column}: {self.message}"
            return f"Parse error at line {self.line}: {self.message}"
        return f"Parse error: {self.message}"


def _parse_step_input(data: dict[str, Any]) -> StepInput:
    """Parse a step input specification."""
    return StepInput(
        name=data.get("name", ""),
        type=data.get("type", "any"),
        required=data.get("required", True),
        default=data.get("default"),
        from_step=data.get("from_step"),
    )


def _parse_step_output(data: dict[str, Any]) -> StepOutput:
    """Parse a step output specification."""
    return StepOutput(
        name=data.get("name", ""),
        type=data.get("type", "any"),
        description=data.get("description"),
    )


def _parse_step(data: dict[str, Any], index: int) -> RunbookStep:
    """Parse a single runbook step."""
    if "id" not in data:
        raise RunbookParseError(f"Step {index} missing required 'id' field")
    if "name" not in data:
        raise RunbookParseError(f"Step {index} missing required 'name' field")
    if "acts" not in data:
        raise RunbookParseError(f"Step {index} ('{data.get('id')}') missing required 'acts' field")
    
    acts = data["acts"]
    if isinstance(acts, str):
        acts = [acts]
    elif not isinstance(acts, list):
        raise RunbookParseError(f"Step {index}: 'acts' must be a string or list")
    
    depends_on = data.get("depends_on", [])
    if isinstance(depends_on, str):
        depends_on = [depends_on]
    
    inputs = [
        _parse_step_input(inp) if isinstance(inp, dict) else StepInput(name=str(inp))
        for inp in data.get("inputs", [])
    ]
    
    outputs = [
        _parse_step_output(out) if isinstance(out, dict) else StepOutput(name=str(out))
        for out in data.get("outputs", [])
    ]
    
    return RunbookStep(
        id=data["id"],
        name=data["name"],
        description=data.get("description"),
        acts=acts,
        depends_on=depends_on,
        inputs=inputs,
        outputs=outputs,
        condition=data.get("condition"),
        retry_count=data.get("retry_count", 0),
        timeout_seconds=data.get("timeout_seconds", 60),
    )


def parse_runbook_yaml(content: str) -> RunbookCreate:
    """Parse a YAML string into a RunbookCreate model.
    
    Args:
        content: YAML string containing the runbook definition.
    
    Returns:
        Validated RunbookCreate model.
    
    Raises:
        RunbookParseError: If parsing fails.
    """
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        if hasattr(e, "problem_mark"):
            mark = e.problem_mark
            raise RunbookParseError(str(e), line=mark.line + 1, column=mark.column + 1)
        raise RunbookParseError(str(e))
    
    if not isinstance(data, dict):
        raise RunbookParseError("Runbook must be a YAML mapping")
    
    if "name" not in data:
        raise RunbookParseError("Runbook missing required 'name' field")
    if "steps" not in data:
        raise RunbookParseError("Runbook missing required 'steps' field")
    
    steps_data = data["steps"]
    if not isinstance(steps_data, list):
        raise RunbookParseError("'steps' must be a list")
    if not steps_data:
        raise RunbookParseError("Runbook must have at least one step")
    
    steps = [_parse_step(step_data, i) for i, step_data in enumerate(steps_data)]
    
    tags = data.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    
    policy_requirements = data.get("policy_requirements", [])
    if isinstance(policy_requirements, str):
        policy_requirements = [policy_requirements]
    
    try:
        return RunbookCreate(
            name=data["name"],
            description=data.get("description"),
            version=data.get("version", "1.0.0"),
            steps=steps,
            tags=tags,
            policy_requirements=policy_requirements,
        )
    except Exception as e:
        raise RunbookParseError(f"Validation failed: {e}")


def parse_runbook_file(path: Path | str) -> RunbookCreate:
    """Parse a YAML file into a RunbookCreate model.
    
    Args:
        path: Path to the YAML file.
    
    Returns:
        Validated RunbookCreate model.
    
    Raises:
        RunbookParseError: If parsing fails.
        FileNotFoundError: If the file doesn't exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Runbook file not found: {path}")
    
    content = path.read_text(encoding="utf-8")
    try:
        return parse_runbook_yaml(content)
    except RunbookParseError as e:
        raise RunbookParseError(f"In file {path}: {e.message}", e.line, e.column)
