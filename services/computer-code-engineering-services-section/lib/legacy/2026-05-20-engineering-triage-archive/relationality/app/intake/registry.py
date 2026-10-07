"""Schema Registry for the intake stack.

The schema registry manages registered schemas for different recognition types
and validates incoming recognitions against their declared schemas.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
from uuid import UUID, uuid4


@dataclass
class SchemaDefinition:
    """A registered schema for validating recognitions."""
    
    id: str
    name: str
    version: str
    recognition_type: str
    required_fields: list[str] = field(default_factory=list)
    optional_fields: list[str] = field(default_factory=list)
    field_validators: dict[str, Callable[[Any], bool]] = field(default_factory=dict)
    content_schema: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def compute_hash(self) -> str:
        """Compute a deterministic hash of this schema definition."""
        data = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "recognition_type": self.recognition_type,
            "required_fields": sorted(self.required_fields),
            "optional_fields": sorted(self.optional_fields),
            "content_schema": self.content_schema,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]


@dataclass
class ValidationResult:
    """Result of schema validation."""
    
    valid: bool
    schema_id: Optional[str] = None
    schema_version: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    normalized_content: Optional[dict[str, Any]] = None


class SchemaRegistry:
    """Registry for recognition schemas.
    
    Provides:
    - Schema registration and versioning
    - Schema validation for incoming recognitions
    - Schema migration helpers
    - Default schemas for core recognition types
    """
    
    _instance: Optional["SchemaRegistry"] = None
    
    def __init__(self):
        self._schemas: dict[str, SchemaDefinition] = {}
        self._schemas_by_type: dict[str, list[str]] = {}
        self._register_default_schemas()
    
    @classmethod
    def get_instance(cls) -> "SchemaRegistry":
        """Get the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None
    
    def register(self, schema: SchemaDefinition) -> str:
        """Register a schema definition.
        
        Returns the schema hash for reference.
        """
        schema_hash = schema.compute_hash()
        full_id = f"{schema.id}:{schema.version}"
        
        self._schemas[full_id] = schema
        
        if schema.recognition_type not in self._schemas_by_type:
            self._schemas_by_type[schema.recognition_type] = []
        
        if full_id not in self._schemas_by_type[schema.recognition_type]:
            self._schemas_by_type[schema.recognition_type].append(full_id)
        
        return schema_hash
    
    def get_schema(self, schema_id: str, version: Optional[str] = None) -> Optional[SchemaDefinition]:
        """Get a schema by ID and optional version.
        
        If version is not specified, returns the latest version.
        """
        if version:
            full_id = f"{schema_id}:{version}"
            return self._schemas.get(full_id)
        
        matching = [k for k in self._schemas.keys() if k.startswith(f"{schema_id}:")]
        if not matching:
            return None
        
        matching.sort(key=lambda x: x.split(":")[-1], reverse=True)
        return self._schemas.get(matching[0])
    
    def get_schemas_for_type(self, recognition_type: str) -> list[SchemaDefinition]:
        """Get all schemas registered for a recognition type."""
        schema_ids = self._schemas_by_type.get(recognition_type, [])
        return [self._schemas[sid] for sid in schema_ids if sid in self._schemas]
    
    def validate(self, recognition: dict[str, Any]) -> ValidationResult:
        """Validate a recognition against its schema.
        
        Uses the schema_id from metadata if present, otherwise tries to
        find a matching schema for the recognition type.
        """
        errors = []
        warnings = []
        
        recognition_type = recognition.get("type")
        if not recognition_type:
            return ValidationResult(
                valid=False,
                errors=["Recognition must have a type"]
            )
        
        metadata = recognition.get("metadata", {})
        schema_id = metadata.get("schema_id")
        schema_version = metadata.get("schema_version")
        
        schema = None
        if schema_id:
            schema = self.get_schema(schema_id, schema_version)
            if not schema:
                warnings.append(f"Schema {schema_id}:{schema_version or 'latest'} not found, using type default")
        
        if not schema:
            schemas = self.get_schemas_for_type(recognition_type)
            if schemas:
                schema = schemas[0]
        
        if not schema:
            return ValidationResult(
                valid=True,
                warnings=["No schema found for this recognition type, skipping schema validation"],
            )
        
        content = recognition.get("content", {})
        
        for required_field in schema.required_fields:
            if required_field not in content:
                errors.append(f"Missing required field in content: {required_field}")
        
        for field_name, validator in schema.field_validators.items():
            if field_name in content:
                try:
                    if not validator(content[field_name]):
                        errors.append(f"Field '{field_name}' failed validation")
                except Exception as e:
                    errors.append(f"Field '{field_name}' validation error: {str(e)}")
        
        if schema.content_schema:
            content_errors = self._validate_content_schema(content, schema.content_schema)
            errors.extend(content_errors)
        
        return ValidationResult(
            valid=len(errors) == 0,
            schema_id=schema.id,
            schema_version=schema.version,
            errors=errors,
            warnings=warnings,
            normalized_content=content,
        )
    
    def _validate_content_schema(
        self,
        content: dict[str, Any],
        schema: dict[str, Any],
    ) -> list[str]:
        """Validate content against a JSON-like schema definition."""
        errors = []
        
        for field_name, field_spec in schema.items():
            if isinstance(field_spec, dict):
                field_type = field_spec.get("type")
                required = field_spec.get("required", False)
                
                if required and field_name not in content:
                    errors.append(f"Required field '{field_name}' missing from content")
                    continue
                
                if field_name in content:
                    value = content[field_name]
                    if not self._check_type(value, field_type):
                        errors.append(f"Field '{field_name}' has wrong type, expected {field_type}")
        
        return errors
    
    def _check_type(self, value: Any, expected_type: Optional[str]) -> bool:
        """Check if a value matches the expected type."""
        if expected_type is None:
            return True
        
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        
        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return True
        
        return isinstance(value, expected_python_type)
    
    def list_schemas(self) -> list[dict[str, Any]]:
        """List all registered schemas with summary info."""
        result = []
        for full_id, schema in self._schemas.items():
            result.append({
                "id": schema.id,
                "name": schema.name,
                "version": schema.version,
                "recognition_type": schema.recognition_type,
                "required_fields": schema.required_fields,
                "hash": schema.compute_hash(),
            })
        return result
    
    def _register_default_schemas(self) -> None:
        """Register default schemas for core recognition types."""
        
        observation_schema = SchemaDefinition(
            id="observation-schema",
            name="Observation Schema",
            version="1.0.0",
            recognition_type="observation",
            required_fields=[],
            optional_fields=["value", "source", "timestamp", "metadata"],
            content_schema={
                "source": {"type": "string", "required": False},
            },
        )
        self.register(observation_schema)
        
        judgement_schema = SchemaDefinition(
            id="judgement-schema",
            name="Judgement Schema",
            version="1.0.0",
            recognition_type="judgement",
            required_fields=["assertion"],
            optional_fields=["confidence", "evidence", "reasoning"],
            content_schema={
                "assertion": {"type": "string", "required": True},
                "confidence": {"type": "number", "required": False},
                "evidence": {"type": "array", "required": False},
            },
        )
        self.register(judgement_schema)
        
        witness_schema = SchemaDefinition(
            id="witness-schema",
            name="Witness Schema",
            version="1.0.0",
            recognition_type="witness",
            required_fields=["witnessed_id"],
            optional_fields=["attestation", "signature"],
            content_schema={
                "witnessed_id": {"type": "string", "required": True},
                "attestation": {"type": "object", "required": False},
            },
        )
        self.register(witness_schema)
        
        context_schema = SchemaDefinition(
            id="context-schema",
            name="Context Schema",
            version="1.0.0",
            recognition_type="context",
            required_fields=[],
            optional_fields=["bindings", "parent_context", "depth"],
            content_schema={
                "bindings": {"type": "object", "required": False},
                "parent_context": {"type": "string", "required": False},
                "depth": {"type": "integer", "required": False},
            },
        )
        self.register(context_schema)
        
        trace_schema = SchemaDefinition(
            id="trace-schema",
            name="Trace Schema",
            version="1.0.0",
            recognition_type="trace",
            required_fields=[],
            optional_fields=["steps", "current_position", "status"],
            content_schema={
                "steps": {"type": "array", "required": False},
                "current_position": {"type": "integer", "required": False},
                "status": {"type": "string", "required": False},
            },
        )
        self.register(trace_schema)
