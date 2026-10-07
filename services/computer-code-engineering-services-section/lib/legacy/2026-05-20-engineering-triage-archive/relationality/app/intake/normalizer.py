"""Recognition Normalizer for the intake stack.

The normalizer applies canonical transformations to recognitions before
they are persisted, ensuring consistent data formats and traceability.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4


@dataclass
class NormalizationResult:
    """Result of normalizing a recognition."""
    
    success: bool
    normalized: dict[str, Any]
    transformations: list[str] = field(default_factory=list)
    hash: Optional[str] = None
    errors: list[str] = field(default_factory=list)


class RecognitionNormalizer:
    """Normalizes recognitions for consistent persistence.
    
    Applies:
    - Content hash computation
    - Timestamp normalization
    - Metadata enrichment
    - Field canonicalization
    """
    
    def __init__(self):
        self._transformations: list[str] = []
    
    def normalize(self, recognition: dict[str, Any]) -> NormalizationResult:
        """Normalize a recognition for persistence.
        
        Applies all standard transformations and computes the content hash.
        """
        transformations = []
        errors = []
        
        normalized = dict(recognition)
        
        if "type" in normalized and isinstance(normalized["type"], str):
            normalized["type"] = normalized["type"].lower()
            transformations.append("lowercase_type")
        
        if "acts" in normalized:
            acts = normalized["acts"]
            if isinstance(acts, list):
                normalized["acts"] = sorted(set(act.lower() for act in acts if isinstance(act, str)))
                if normalized["acts"] != acts:
                    transformations.append("canonicalize_acts")
        
        if "tags" in normalized:
            tags = normalized["tags"]
            if isinstance(tags, list):
                normalized["tags"] = sorted(set(tag.lower() for tag in tags if isinstance(tag, str)))
                if normalized["tags"] != tags:
                    transformations.append("canonicalize_tags")
        
        if "content" not in normalized:
            normalized["content"] = {}
            transformations.append("add_empty_content")
        elif not isinstance(normalized["content"], dict):
            try:
                normalized["content"] = {"value": normalized["content"]}
                transformations.append("wrap_content")
            except Exception:
                errors.append("Content must be a dict or convertible to dict")
                return NormalizationResult(
                    success=False,
                    normalized=normalized,
                    errors=errors,
                )
        
        if "metadata" not in normalized:
            normalized["metadata"] = {}
            transformations.append("add_empty_metadata")
        
        metadata = normalized["metadata"]
        if not isinstance(metadata, dict):
            metadata = {}
            normalized["metadata"] = metadata
        
        now = datetime.utcnow().isoformat() + "Z"
        
        if "created_at" not in metadata:
            metadata["created_at"] = now
            transformations.append("add_created_timestamp")
        
        metadata["normalized_at"] = now
        transformations.append("add_normalized_timestamp")
        
        if "trace_id" not in metadata:
            metadata["trace_id"] = str(uuid4())
            transformations.append("generate_trace_id")
        
        content_hash = self._compute_content_hash(normalized)
        metadata["content_hash"] = content_hash
        transformations.append("compute_content_hash")
        
        if "title" in normalized and isinstance(normalized["title"], str):
            normalized["title"] = " ".join(normalized["title"].split())
            transformations.append("normalize_title_whitespace")
        
        return NormalizationResult(
            success=True,
            normalized=normalized,
            transformations=transformations,
            hash=content_hash,
        )
    
    def _compute_content_hash(self, recognition: dict[str, Any]) -> str:
        """Compute a deterministic hash of the recognition content.
        
        Uses type, title, content, and acts to produce a stable hash.
        """
        hash_data = {
            "type": recognition.get("type"),
            "title": recognition.get("title"),
            "content": recognition.get("content", {}),
            "acts": recognition.get("acts", []),
        }
        
        json_str = json.dumps(hash_data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()[:32]
    
    def compute_hash(self, data: dict[str, Any]) -> str:
        """Compute a hash for arbitrary data."""
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()[:32]
    
    def deep_normalize(self, recognition: dict[str, Any]) -> NormalizationResult:
        """Apply deep normalization including content field cleaning."""
        result = self.normalize(recognition)
        if not result.success:
            return result
        
        normalized = result.normalized
        content = normalized.get("content", {})
        
        if isinstance(content, dict):
            cleaned_content = self._clean_content(content)
            if cleaned_content != content:
                normalized["content"] = cleaned_content
                result.transformations.append("deep_clean_content")
        
        return result
    
    def _clean_content(self, content: dict[str, Any]) -> dict[str, Any]:
        """Remove None values and empty strings from content recursively."""
        cleaned = {}
        
        for key, value in content.items():
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            if isinstance(value, dict):
                cleaned_value = self._clean_content(value)
                if cleaned_value:
                    cleaned[key] = cleaned_value
            elif isinstance(value, list):
                cleaned_list = [
                    self._clean_content(v) if isinstance(v, dict) else v
                    for v in value
                    if v is not None and not (isinstance(v, str) and v.strip() == "")
                ]
                if cleaned_list:
                    cleaned[key] = cleaned_list
            else:
                cleaned[key] = value
        
        return cleaned
