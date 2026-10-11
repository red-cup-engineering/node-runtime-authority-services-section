"""Intake Pipeline for processing recognitions.

The pipeline coordinates schema validation, policy enforcement, 
and normalization into a single processing flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from app.intake.registry import SchemaRegistry, ValidationResult
from app.intake.normalizer import RecognitionNormalizer, NormalizationResult
from app.policy.engine import PolicyEngine, PolicyDecisionResult
from app.policy.defaults import create_default_policies
from app.schemas.policy import PolicyScope


_policy_engine_instance: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get or create the global policy engine instance."""
    global _policy_engine_instance
    if _policy_engine_instance is None:
        _policy_engine_instance = PolicyEngine()
        for policy in create_default_policies():
            _policy_engine_instance.register_policy(policy)
    return _policy_engine_instance


@dataclass
class IntakeResult:
    """Result of processing a recognition through the intake pipeline."""
    
    success: bool
    recognition: Optional[dict[str, Any]] = None
    validation_result: Optional[ValidationResult] = None
    policy_result: Optional[PolicyDecisionResult] = None
    normalization_result: Optional[NormalizationResult] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trace_id: Optional[str] = None
    processed_at: Optional[str] = None


class IntakePipeline:
    """Pipeline for processing incoming recognitions.
    
    The pipeline applies:
    1. Schema validation - Ensures recognition matches its declared schema
    2. Policy evaluation - Applies discipline and filter rules
    3. Normalization - Canonicalizes data for persistence
    4. Audit logging - Records the intake decision
    
    This implements the intake-stack simulation specification from
    the mathematical foundation.
    """
    
    def __init__(
        self,
        schema_registry: Optional[SchemaRegistry] = None,
        policy_engine: Optional[PolicyEngine] = None,
        normalizer: Optional[RecognitionNormalizer] = None,
    ):
        self.schema_registry = schema_registry or SchemaRegistry.get_instance()
        self.policy_engine = policy_engine or get_policy_engine()
        self.normalizer = normalizer or RecognitionNormalizer()
    
    async def process(
        self,
        recognition: dict[str, Any],
        known_acts: set[str],
        user_id: Optional[str] = None,
    ) -> IntakeResult:
        """Process a recognition through the full intake pipeline.
        
        Args:
            recognition: The recognition data to process
            known_acts: Set of valid act slugs from the graph
            user_id: Optional user ID for audit logging
        
        Returns:
            IntakeResult with success/failure and processed recognition
        """
        trace_id = str(uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        errors = []
        warnings = []
        
        acts = recognition.get("acts", [])
        if not acts:
            errors.append("Recognition must reference at least one act")
        else:
            unknown_acts = set(acts) - known_acts
            if unknown_acts:
                errors.append(f"Unknown acts referenced: {sorted(unknown_acts)}")
        
        if errors:
            return IntakeResult(
                success=False,
                errors=errors,
                trace_id=trace_id,
                processed_at=now,
            )
        
        validation_result = self.schema_registry.validate(recognition)
        
        if not validation_result.valid:
            errors.extend(validation_result.errors)
            return IntakeResult(
                success=False,
                validation_result=validation_result,
                errors=errors,
                warnings=validation_result.warnings,
                trace_id=trace_id,
                processed_at=now,
            )
        
        warnings.extend(validation_result.warnings)
        
        policy_result = self.policy_engine.evaluate(
            scope=PolicyScope.RECOGNITION,
            target=recognition,
        )
        
        if not policy_result.allowed:
            errors.append(f"Policy denied: {policy_result.reasoning}")
            return IntakeResult(
                success=False,
                validation_result=validation_result,
                policy_result=policy_result,
                errors=errors,
                warnings=warnings,
                trace_id=trace_id,
                processed_at=now,
            )
        
        normalization_result = self.normalizer.normalize(recognition)
        
        if not normalization_result.success:
            errors.extend(normalization_result.errors)
            return IntakeResult(
                success=False,
                validation_result=validation_result,
                policy_result=policy_result,
                normalization_result=normalization_result,
                errors=errors,
                warnings=warnings,
                trace_id=trace_id,
                processed_at=now,
            )
        
        normalized = normalization_result.normalized
        
        if "metadata" not in normalized:
            normalized["metadata"] = {}
        
        normalized["metadata"]["intake_trace_id"] = trace_id
        normalized["metadata"]["intake_user_id"] = user_id
        normalized["metadata"]["intake_timestamp"] = now
        normalized["metadata"]["schema_id"] = validation_result.schema_id
        normalized["metadata"]["schema_version"] = validation_result.schema_version
        
        return IntakeResult(
            success=True,
            recognition=normalized,
            validation_result=validation_result,
            policy_result=policy_result,
            normalization_result=normalization_result,
            errors=[],
            warnings=warnings,
            trace_id=trace_id,
            processed_at=now,
        )
    
    def validate_only(self, recognition: dict[str, Any]) -> ValidationResult:
        """Validate a recognition without processing it.
        
        Useful for checking if a recognition would be accepted.
        """
        return self.schema_registry.validate(recognition)
    
    def normalize_only(self, recognition: dict[str, Any]) -> NormalizationResult:
        """Normalize a recognition without full pipeline processing.
        
        Useful for previewing normalization transformations.
        """
        return self.normalizer.normalize(recognition)


class IntakeStack:
    """High-level interface for the intake stack.
    
    Provides methods for:
    - Registering custom schemas
    - Processing recognitions
    - Querying intake history
    """
    
    def __init__(self):
        self.pipeline = IntakePipeline()
        self._intake_history: list[IntakeResult] = []
    
    def register_schema(
        self,
        schema_id: str,
        name: str,
        version: str,
        recognition_type: str,
        required_fields: Optional[list[str]] = None,
        content_schema: Optional[dict[str, Any]] = None,
    ) -> str:
        """Register a custom schema for validation."""
        from app.intake.registry import SchemaDefinition
        
        schema = SchemaDefinition(
            id=schema_id,
            name=name,
            version=version,
            recognition_type=recognition_type,
            required_fields=required_fields or [],
            content_schema=content_schema or {},
        )
        
        return self.pipeline.schema_registry.register(schema)
    
    async def intake(
        self,
        recognition: dict[str, Any],
        known_acts: set[str],
        user_id: Optional[str] = None,
    ) -> IntakeResult:
        """Process a recognition through the intake stack."""
        result = await self.pipeline.process(recognition, known_acts, user_id)
        
        self._intake_history.append(result)
        
        if len(self._intake_history) > 1000:
            self._intake_history = self._intake_history[-500:]
        
        return result
    
    def get_intake_history(
        self,
        limit: int = 100,
        success_only: bool = False,
    ) -> list[IntakeResult]:
        """Get recent intake history."""
        history = self._intake_history
        
        if success_only:
            history = [r for r in history if r.success]
        
        return history[-limit:]
    
    def list_schemas(self) -> list[dict[str, Any]]:
        """List all registered schemas."""
        return self.pipeline.schema_registry.list_schemas()
