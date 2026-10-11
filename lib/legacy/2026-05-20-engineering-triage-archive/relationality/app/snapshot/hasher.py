"""Baseline hash computation for snapshot semantics.

Implements deterministic hashing of recognitions and contexts
to ensure content integrity and enable incremental updates.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class HashResult:
    """Result of a hash computation."""
    
    hash: str
    input_count: int
    algorithm: str = "sha256"
    computed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class BaselineHasher:
    """Computes deterministic hashes for baseline tracking.
    
    Baseline hashes provide:
    - Content integrity verification
    - Change detection between snapshots
    - Merkle-tree-like composition for hierarchical structures
    """
    
    def __init__(self, algorithm: str = "sha256"):
        self.algorithm = algorithm
    
    def hash_recognition(self, recognition: dict[str, Any]) -> str:
        """Compute a hash for a single recognition.
        
        Uses type, title, content, and acts to produce a stable hash.
        """
        hash_data = {
            "type": recognition.get("type"),
            "title": recognition.get("title"),
            "content": recognition.get("content", {}),
            "acts": sorted(recognition.get("acts", [])),
        }
        return self._hash_data(hash_data)
    
    def hash_context(self, context: dict[str, Any]) -> str:
        """Compute a hash for a context.
        
        Includes bindings, depth, and parent context reference.
        """
        hash_data = {
            "context_type": context.get("context_type"),
            "bindings": context.get("bindings", {}),
            "depth": context.get("depth", 0),
            "parent_context": context.get("parent_context"),
        }
        return self._hash_data(hash_data)
    
    def hash_trace(self, trace: dict[str, Any]) -> str:
        """Compute a hash for a trace.
        
        Includes steps and current position for execution state.
        """
        steps = trace.get("steps", [])
        step_hashes = [self._hash_data(step) for step in steps]
        
        hash_data = {
            "step_hashes": step_hashes,
            "current_position": trace.get("current_position", 0),
            "status": trace.get("status"),
        }
        return self._hash_data(hash_data)
    
    def hash_collection(self, items: list[dict[str, Any]]) -> HashResult:
        """Compute a Merkle-like hash for a collection of items.
        
        Hashes each item individually, then computes a root hash.
        """
        item_hashes = []
        for item in items:
            item_type = item.get("type", "unknown")
            if item_type == "context":
                item_hashes.append(self.hash_context(item))
            elif item_type == "trace":
                item_hashes.append(self.hash_trace(item))
            else:
                item_hashes.append(self.hash_recognition(item))
        
        item_hashes.sort()
        
        root_hash = self._hash_data({"item_hashes": item_hashes})
        
        return HashResult(
            hash=root_hash,
            input_count=len(items),
            algorithm=self.algorithm,
        )
    
    def hash_snapshot(
        self,
        recognitions: list[dict[str, Any]],
        contexts: Optional[list[dict[str, Any]]] = None,
        traces: Optional[list[dict[str, Any]]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> HashResult:
        """Compute a comprehensive hash for a snapshot.
        
        Includes recognitions, contexts, traces, and metadata.
        """
        all_items = list(recognitions)
        if contexts:
            all_items.extend(contexts)
        if traces:
            all_items.extend(traces)
        
        collection_result = self.hash_collection(all_items)
        
        metadata_hash = self._hash_data(metadata or {})
        
        final_hash = self._hash_data({
            "collection_hash": collection_result.hash,
            "metadata_hash": metadata_hash,
            "item_count": len(all_items),
        })
        
        return HashResult(
            hash=final_hash,
            input_count=len(all_items),
            algorithm=self.algorithm,
        )
    
    def compute_diff_hash(
        self,
        old_hash: str,
        new_hash: str,
        added_hashes: list[str],
        removed_hashes: list[str],
    ) -> str:
        """Compute a hash representing the difference between snapshots.
        
        Used for incremental update tracking.
        """
        diff_data = {
            "old_hash": old_hash,
            "new_hash": new_hash,
            "added": sorted(added_hashes),
            "removed": sorted(removed_hashes),
            "added_count": len(added_hashes),
            "removed_count": len(removed_hashes),
        }
        return self._hash_data(diff_data)
    
    def _hash_data(self, data: Any) -> str:
        """Hash arbitrary data using the configured algorithm."""
        json_str = json.dumps(data, sort_keys=True, default=str)
        
        if self.algorithm == "sha256":
            return hashlib.sha256(json_str.encode()).hexdigest()[:32]
        elif self.algorithm == "sha512":
            return hashlib.sha512(json_str.encode()).hexdigest()[:64]
        elif self.algorithm == "md5":
            return hashlib.md5(json_str.encode()).hexdigest()
        else:
            return hashlib.sha256(json_str.encode()).hexdigest()[:32]
    
    def verify_hash(self, data: dict[str, Any], expected_hash: str) -> bool:
        """Verify that data matches an expected hash."""
        item_type = data.get("type", "recognition")
        
        if item_type == "context":
            computed = self.hash_context(data)
        elif item_type == "trace":
            computed = self.hash_trace(data)
        else:
            computed = self.hash_recognition(data)
        
        return computed == expected_hash
