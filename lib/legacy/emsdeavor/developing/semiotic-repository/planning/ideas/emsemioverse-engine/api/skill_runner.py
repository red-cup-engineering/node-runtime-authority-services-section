"""Skill execution utilities shared across API surfaces."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from engine.api.app_state import LIBRARY_ROOT


class SkillExecutionRequest(BaseModel):
    """Request body for skill execution."""
    inputs: dict[str, Any] = {}
    dry_run: bool = False


class SkillExecutionResponse(BaseModel):
    """Response from skill execution."""
    success: bool
    skill_id: str
    outputs: dict[str, Any] | None = None
    error: str | None = None
    stdout: str | None = None
    stderr: str | None = None


def build_command(
    language: str,
    script_path: Path,
    skill: dict[str, Any],
    inputs: dict[str, Any],
) -> list[str]:
    """Build the command to execute a skill."""
    if language == "python":
        cmd = [sys.executable, str(script_path)]
    elif language == "bash":
        cmd = ["bash", str(script_path)]
    elif language == "node":
        cmd = ["node", str(script_path)]
    else:
        cmd = [str(script_path)]
    
    skill_inputs = skill.get("inputs", [])
    input_map = {inp["name"]: inp for inp in skill_inputs}
    
    for name, value in inputs.items():
        if name not in input_map:
            continue
        
        inp_def = input_map[name]
        inp_type = inp_def.get("type", "string")
        
        if inp_type == "boolean":
            if value:
                arg_name = name.replace("_", "-")
                cmd.append(f"--{arg_name}")
        else:
            arg_name = name.replace("_", "-")
            cmd.extend([f"--{arg_name}", str(value)])
    
    for inp_def in skill_inputs:
        name = inp_def["name"]
        if name in inputs:
            continue
        
        if inp_def.get("required"):
            continue
        
        default = inp_def.get("default")
        if default is not None and inp_def.get("type") != "boolean":
            arg_name = name.replace("_", "-")
            cmd.extend([f"--{arg_name}", str(default)])
    
    return cmd


def run_skill(skill: dict[str, Any], inputs: dict[str, Any]) -> SkillExecutionResponse:
    """Core skill execution logic (synchronous)."""
    skill_id = skill.get("id", "unknown")
    
    runtime = skill.get("runtime")
    if not runtime:
        raise HTTPException(
            status_code=400,
            detail=f"Skill {skill_id} has no runtime configuration",
        )
    
    entrypoint = runtime.get("entrypoint")
    language = runtime.get("language")
    
    if not entrypoint:
        raise HTTPException(
            status_code=400,
            detail=f"Skill {skill_id} has no entrypoint",
        )
    
    script_path = LIBRARY_ROOT / entrypoint
    if not script_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Script not found: {entrypoint}",
        )
    
    cmd = build_command(language, script_path, skill, inputs)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(LIBRARY_ROOT.parent),
        )
        
        outputs = None
        try:
            outputs = json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
        
        return SkillExecutionResponse(
            success=result.returncode == 0,
            skill_id=skill_id,
            outputs=outputs,
            stdout=result.stdout if not outputs else None,
            stderr=result.stderr if result.stderr else None,
            error=result.stderr if result.returncode != 0 else None,
        )
    except subprocess.TimeoutExpired:
        return SkillExecutionResponse(
            success=False,
            skill_id=skill_id,
            error="Skill execution timed out",
        )
    except Exception as e:
        return SkillExecutionResponse(
            success=False,
            skill_id=skill_id,
            error=str(e),
        )


async def execute_skill_internal(
    skill_id: str,
    arguments: dict[str, Any],
    state: Any,
) -> dict[str, Any]:
    """Execute a skill and return MCP-formatted result.
    """
    skill = state.get_skill_by_id(skill_id)
    if not skill:
        return {
            "content": [{"type": "text", "text": f"Skill not found: {skill_id}"}],
            "isError": True,
        }
    
    result = run_skill(skill, arguments)
    
    content = []
    if result.success:
        if result.outputs:
            content.append({
                "type": "text",
                "text": json.dumps(result.outputs, indent=2),
            })
        elif result.stdout:
            content.append({
                "type": "text",
                "text": result.stdout,
            })
        else:
            content.append({
                "type": "text",
                "text": "Skill executed successfully",
            })
        return {"content": content, "isError": False}
    else:
        content.append({
            "type": "text",
            "text": result.error or "Unknown error",
        })
        return {"content": content, "isError": True}
