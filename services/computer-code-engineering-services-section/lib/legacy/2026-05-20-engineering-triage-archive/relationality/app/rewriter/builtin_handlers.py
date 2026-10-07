"""Built-in act handlers for common operations.

These handlers implement the core acts needed for intake,
observation, and basic trace operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from app.rewriter.handlers import (
    ActHandler,
    ExecutionContext,
    HandlerResult,
)


class ValidateRecognitionHandler(ActHandler):
    """Handler for validating recognitions against policies.
    
    Maps to: recognize-syntax, normalize-syntax, sound-syntax
    """
    
    acts = ["recognize-syntax", "normalize-syntax", "sound-syntax"]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        recognition = context.get_input("recognition")
        schema = context.get_input("schema")
        
        if recognition is None:
            return HandlerResult.fail("Missing required input: recognition")
        
        is_valid = True
        errors: list[str] = []
        
        if not isinstance(recognition, dict):
            is_valid = False
            errors.append("Recognition must be a mapping")
        
        if is_valid and "type" not in recognition:
            is_valid = False
            errors.append("Recognition missing required field: type")
        
        if is_valid and "acts" not in recognition:
            recognition["acts"] = []
        
        validation_result = {
            "is_valid": is_valid,
            "errors": errors,
            "validated_at": datetime.utcnow().isoformat(),
            "act": act,
        }
        
        return HandlerResult.ok(
            outputs={
                "is_valid": is_valid,
                "errors": errors,
                "validation_result": validation_result,
            },
            metadata={"act": act},
        )


class NormalizeObservationHandler(ActHandler):
    """Handler for normalizing observations.
    
    Maps to: normalize-observation, normalize-strongly
    """
    
    acts = ["normalize-observation", "normalize-strongly"]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        observation = context.get_input("observation")
        
        if observation is None:
            return HandlerResult.fail("Missing required input: observation")
        
        normalized = dict(observation)
        
        if "normalized_at" not in normalized:
            normalized["normalized_at"] = datetime.utcnow().isoformat()
        
        if "type" not in normalized:
            normalized["type"] = "observation"
        
        if "trace_id" not in normalized:
            normalized["trace_id"] = str(context.trace_id)
        
        if "metadata" not in normalized:
            normalized["metadata"] = {}
        
        normalized["metadata"]["normalization_act"] = act
        
        return HandlerResult.ok(
            outputs={"normalized": normalized},
            metadata={"act": act},
        )
