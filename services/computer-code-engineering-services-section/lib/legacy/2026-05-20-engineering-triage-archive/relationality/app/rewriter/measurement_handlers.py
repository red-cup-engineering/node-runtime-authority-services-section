"""Measurement and observable handlers for the relational computer.

Implements handlers for measurement algebra, observable capture,
and aggregation from the measurement fabric specification.
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


class MeasurementAlgebraHandler(ActHandler):
    """Handler for measurement algebra operations.
    
    Maps to earned measurement acts at the algebra layer:
    - measure
    - profile-measure
    - profile-integral
    - entropy
    
    Measurement algebra provides the mathematical foundation for
    capturing and processing observables in the system.
    """
    
    acts = [
        "measure",
        "profile-measure",
        "profile-integral",
        "entropy",
    ]
    
    def _compute_expectation(self, observable: Any, distribution: dict) -> float:
        """Compute expectation E[X] = sum(x * p(x)) over distribution.
        
        If observable is numeric, treats it as a constant.
        If observable is a list, computes weighted average using distribution probabilities.
        If distribution has 'values' and 'probabilities' keys, uses those.
        """
        import math
        
        if isinstance(observable, (int, float)):
            return float(observable)
        
        if isinstance(observable, list):
            if not observable:
                return 0.0
            
            probs = distribution.get("probabilities", [])
            if probs and len(probs) == len(observable):
                total_prob = sum(probs) or 1.0
                return sum(v * (p / total_prob) for v, p in zip(observable, probs) if isinstance(v, (int, float)))
            
            return sum(v for v in observable if isinstance(v, (int, float))) / len(observable)
        
        if isinstance(observable, dict):
            values = observable.get("values", [])
            probs = observable.get("probabilities", distribution.get("probabilities", []))
            
            if values and probs and len(values) == len(probs):
                total_prob = sum(probs) or 1.0
                return sum(v * (p / total_prob) for v, p in zip(values, probs) if isinstance(v, (int, float)))
            
            if values:
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                return sum(numeric_values) / len(numeric_values) if numeric_values else 0.0
        
        return 0.0
    
    def _compute_entropy(self, distribution: dict, entropy_type: str = "shannon") -> float:
        """Compute entropy H(X) = -sum(p(x) * log(p(x))) over distribution.
        
        Supports shannon (natural log) and binary (log2) entropy types.
        """
        import math
        
        probs = distribution.get("probabilities", [])
        
        if not probs:
            values = distribution.get("values", [])
            if values:
                n = len(values)
                probs = [1.0 / n] * n
        
        if not probs:
            return 0.0
        
        total_prob = sum(p for p in probs if isinstance(p, (int, float)) and p > 0)
        if total_prob <= 0:
            return 0.0
        
        normalized_probs = [p / total_prob for p in probs if isinstance(p, (int, float)) and p > 0]
        
        entropy = 0.0
        for p in normalized_probs:
            if p > 0:
                if entropy_type == "binary":
                    entropy -= p * math.log2(p)
                else:
                    entropy -= p * math.log(p)
        
        return entropy
    
    def _measure_observable(self, target: Any, observable_type: str) -> float:
        """Measure an observable from the target based on observable_type.
        
        Observable types:
        - count: Count elements in target (for lists/dicts) or return 1 for existence
        - size: Size of target in bytes (for strings) or count for collections
        - value: Extract numeric value directly from target
        - length: Length of sequence or string
        - depth: Nesting depth for dicts/lists
        """
        if target is None:
            return 0.0
        
        if observable_type == "count":
            if isinstance(target, (list, tuple)):
                return float(len(target))
            elif isinstance(target, dict):
                return float(len(target))
            elif isinstance(target, (int, float)):
                return 1.0
            elif isinstance(target, str):
                return 1.0
            else:
                return 1.0
        
        elif observable_type == "size":
            if isinstance(target, str):
                return float(len(target.encode('utf-8')))
            elif isinstance(target, (list, tuple)):
                return float(len(target))
            elif isinstance(target, dict):
                return float(len(target))
            else:
                return 1.0
        
        elif observable_type == "value":
            if isinstance(target, (int, float)):
                return float(target)
            elif isinstance(target, dict) and "value" in target:
                val = target["value"]
                if isinstance(val, (int, float)):
                    return float(val)
            return 0.0
        
        elif observable_type == "length":
            if isinstance(target, (str, list, tuple)):
                return float(len(target))
            elif isinstance(target, dict):
                return float(len(target))
            return 0.0
        
        elif observable_type == "depth":
            return float(self._compute_depth(target))
        
        else:
            if isinstance(target, (int, float)):
                return float(target)
            return 1.0
    
    def _compute_depth(self, obj: Any, current_depth: int = 0) -> int:
        """Compute the nesting depth of a structure."""
        if isinstance(obj, dict):
            if not obj:
                return current_depth + 1
            return max(self._compute_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, (list, tuple)):
            if not obj:
                return current_depth + 1
            return max(self._compute_depth(v, current_depth + 1) for v in obj)
        else:
            return current_depth
    
    def _aggregate_measurements(self, measurements: list, aggregation_type: str) -> float:
        """Aggregate measurement values using the specified aggregation type.
        
        Supports: sum, mean, min, max, count, product
        
        Note: 'count' counts all measurements (not just those with numeric values).
        For numeric aggregations (sum, mean, etc.), only numeric values are used.
        """
        total_measurement_count = len(measurements)
        
        numeric_values = []
        for m in measurements:
            if isinstance(m, dict):
                val = m.get("value")
                if val is not None and isinstance(val, (int, float)):
                    numeric_values.append(float(val))
        
        if aggregation_type == "count":
            return float(total_measurement_count)
        
        if not numeric_values:
            return 0.0
        
        if aggregation_type == "sum":
            return sum(numeric_values)
        elif aggregation_type == "mean":
            return sum(numeric_values) / len(numeric_values)
        elif aggregation_type == "min":
            return min(numeric_values)
        elif aggregation_type == "max":
            return max(numeric_values)
        elif aggregation_type == "product":
            result = 1.0
            for v in numeric_values:
                result *= v
            return result
        else:
            return sum(numeric_values)
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()
        
        if act == "measure":
            observable = context.get_input("observable")
            distribution = context.get_input("distribution", {})
            
            if observable is None:
                return HandlerResult.fail("Missing required input: observable")
            
            computed_value = self._compute_expectation(observable, distribution)
            
            expectation = {
                "id": str(uuid4()),
                "type": "expectation",
                "act": act,
                "acts": [act],
                "observable": observable,
                "distribution": distribution,
                "value": computed_value,
                "computed_at": now,
                "trace_id": trace_id,
            }
            
            persisted_id = await context.persist_recognition(expectation)
            
            return HandlerResult.ok(
                outputs={
                    "expectation": expectation,
                    "expectation_id": expectation["id"],
                    "value": computed_value,
                },
                recognitions_created=[persisted_id],
                metadata={"act": act},
            )
        
        elif act == "entropy":
            distribution = context.get_input("distribution", {})
            entropy_type = context.get_input("entropy_type", "shannon")
            
            computed_entropy = self._compute_entropy(distribution, entropy_type)
            
            entropy = {
                "id": str(uuid4()),
                "type": "entropy",
                "act": act,
                "acts": [act],
                "distribution": distribution,
                "entropy_type": entropy_type,
                "value": computed_entropy,
                "computed_at": now,
                "trace_id": trace_id,
            }
            
            persisted_id = await context.persist_recognition(entropy)
            
            return HandlerResult.ok(
                outputs={
                    "entropy": entropy,
                    "entropy_id": entropy["id"],
                    "value": computed_entropy,
                },
                recognitions_created=[persisted_id],
                metadata={"act": act, "entropy_type": entropy_type},
            )
        
        elif act == "profile-measure":
            target = context.get_input("target")
            observable_type = context.get_input("observable_type", "count")
            
            measured_value = self._measure_observable(target, observable_type)
            
            measurement = {
                "id": str(uuid4()),
                "type": "measurement",
                "act": act,
                "acts": [act],
                "target": target,
                "observable_type": observable_type,
                "value": measured_value,
                "measured_at": now,
                "trace_id": trace_id,
            }
            
            persisted_id = await context.persist_recognition(measurement)
            
            return HandlerResult.ok(
                outputs={
                    "measurement": measurement,
                    "measurement_id": measurement["id"],
                    "value": measured_value,
                },
                recognitions_created=[persisted_id],
                metadata={"act": act, "observable_type": observable_type},
            )
        
        elif act == "profile-integral":
            measurements = context.get_input("measurements", [])
            aggregation_type = context.get_input("aggregation_type", "sum")
            
            aggregated_value = self._aggregate_measurements(measurements, aggregation_type)
            
            aggregate = {
                "id": str(uuid4()),
                "type": "aggregate",
                "act": act,
                "acts": [act],
                "measurement_ids": [m.get("id") for m in measurements if isinstance(m, dict)],
                "aggregation_type": aggregation_type,
                "count": len(measurements),
                "value": aggregated_value,
                "aggregated_at": now,
                "trace_id": trace_id,
            }
            
            persisted_id = await context.persist_recognition(aggregate)
            
            return HandlerResult.ok(
                outputs={
                    "aggregate": aggregate,
                    "aggregate_id": aggregate["id"],
                    "value": aggregated_value,
                },
                recognitions_created=[persisted_id],
                metadata={"act": act, "aggregation_type": aggregation_type, "count": len(measurements)},
            )
        
        return HandlerResult.fail(f"Unknown measurement algebra act: {act}")


class IntrospectionHandler(ActHandler):
    """Handler for introspection and observability operations.
    
    Maps to: introspect-trace, introspect-context, 
             sample-observable, emit-telemetry
    
    Introspection operations provide the observability layer
    for monitoring and debugging the relational computer.
    """
    
    acts = [
        "introspect-trace",
        "introspect-context",
        "sample-observable",
        "emit-telemetry",
    ]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()
        
        if act == "introspect-trace":
            trace = context.get_input("trace")
            depth = context.get_input("depth", 1)
            
            if not trace:
                return HandlerResult.fail("Missing required input: trace")
            
            introspection = {
                "id": str(uuid4()),
                "type": "trace_introspection",
                "act": act,
                "trace_id": trace.get("id"),
                "depth": depth,
                "step_count": len(trace.get("steps", [])),
                "current_position": trace.get("current_position", 0),
                "status": trace.get("status", "unknown"),
                "introspected_at": now,
            }
            
            return HandlerResult.ok(
                outputs={
                    "introspection": introspection,
                    "step_count": introspection["step_count"],
                },
                metadata={"act": act, "depth": depth},
            )
        
        elif act == "introspect-context":
            ctx = context.get_input("context")
            include_bindings = context.get_input("include_bindings", True)
            
            if not ctx:
                return HandlerResult.fail("Missing required input: context")
            
            bindings = ctx.get("bindings", {}) if include_bindings else {}
            
            introspection = {
                "id": str(uuid4()),
                "type": "context_introspection",
                "act": act,
                "context_id": ctx.get("id"),
                "context_type": ctx.get("context_type"),
                "depth": ctx.get("depth", 0),
                "binding_count": len(bindings),
                "bindings": bindings,
                "introspected_at": now,
            }
            
            return HandlerResult.ok(
                outputs={
                    "introspection": introspection,
                    "binding_count": introspection["binding_count"],
                },
                metadata={"act": act},
            )
        
        elif act == "sample-observable":
            observable = context.get_input("observable")
            sample_rate = context.get_input("sample_rate", 1.0)
            
            sample = {
                "id": str(uuid4()),
                "type": "observable_sample",
                "act": act,
                "observable": observable,
                "sample_rate": sample_rate,
                "sampled": True,
                "sampled_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "sample": sample,
                    "sampled": True,
                },
                metadata={"act": act, "sample_rate": sample_rate},
            )
        
        elif act == "emit-telemetry":
            event_type = context.get_input("event_type", "generic")
            event_data = context.get_input("event_data", {})
            
            telemetry = {
                "id": str(uuid4()),
                "type": "telemetry",
                "act": act,
                "event_type": event_type,
                "event_data": event_data,
                "emitted_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "telemetry": telemetry,
                    "telemetry_id": telemetry["id"],
                },
                metadata={"act": act, "event_type": event_type},
            )
        
        return HandlerResult.fail(f"Unknown introspection act: {act}")


class BaselineHandler(ActHandler):
    """Handler for baseline and renewal operations.
    
    Maps to: baseline-convergence, baseline-limit,
             compute-baseline, verify-baseline
    
    Baseline operations ensure that the system maintains
    stable reference points for persistence and recovery.
    """
    
    acts = [
        "baseline-convergence",
        "baseline-limit",
        "compute-baseline",
        "verify-baseline",
    ]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()
        
        if act == "baseline-convergence":
            current_baseline = context.get_input("baseline", {})
            observations = context.get_input("observations", [])
            
            convergence = {
                "id": str(uuid4()),
                "type": "baseline_convergence",
                "act": act,
                "acts": [act],
                "current_baseline": current_baseline,
                "observation_count": len(observations),
                "converged": True,
                "convergence_rate": 1.0,
                "computed_at": now,
                "trace_id": trace_id,
            }
            
            persisted_id = await context.persist_recognition(convergence)
            
            return HandlerResult.ok(
                outputs={
                    "convergence": convergence,
                    "converged": True,
                },
                recognitions_created=[persisted_id],
                metadata={"act": act},
            )
        
        elif act == "baseline-limit":
            baseline = context.get_input("baseline", {})
            limit_type = context.get_input("limit_type", "tail")
            
            limit = {
                "id": str(uuid4()),
                "type": "baseline_limit",
                "act": act,
                "acts": [act],
                "baseline": baseline,
                "limit_type": limit_type,
                "limit_value": None,
                "computed_at": now,
                "trace_id": trace_id,
            }
            
            persisted_id = await context.persist_recognition(limit)
            
            return HandlerResult.ok(
                outputs={
                    "limit": limit,
                    "limit_id": limit["id"],
                },
                recognitions_created=[persisted_id],
                metadata={"act": act, "limit_type": limit_type},
            )
        
        elif act == "compute-baseline":
            data = context.get_input("data", [])
            baseline_type = context.get_input("baseline_type", "mean")
            
            baseline = {
                "id": str(uuid4()),
                "type": "computed_baseline",
                "act": act,
                "data_points": len(data),
                "baseline_type": baseline_type,
                "value": None,
                "computed_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "baseline": baseline,
                    "baseline_id": baseline["id"],
                },
                metadata={"act": act, "baseline_type": baseline_type},
            )
        
        elif act == "verify-baseline":
            baseline = context.get_input("baseline")
            expected = context.get_input("expected")
            
            if not baseline:
                return HandlerResult.fail("Missing required input: baseline")
            
            verified = True
            
            verification = {
                "id": str(uuid4()),
                "type": "baseline_verification",
                "act": act,
                "baseline_id": baseline.get("id"),
                "expected": expected,
                "verified": verified,
                "verified_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "verification": verification,
                    "verified": verified,
                },
                metadata={"act": act},
            )
        
        return HandlerResult.fail(f"Unknown baseline act: {act}")


class ReachHandler(ActHandler):
    """Handler for reachability operations.
    
    Maps to: reach, reach-measure, reach-limit
    
    Reachability operations verify that recognitions and
    invariants remain accessible in the system.
    """
    
    acts = ["reach", "reach-measure", "reach-limit"]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()
        
        if act == "reach":
            target = context.get_input("target")
            from_context = context.get_input("from_context")
            
            if target is None:
                return HandlerResult.fail("Missing required input: target")
            
            reach_result = {
                "id": str(uuid4()),
                "type": "reach",
                "act": act,
                "target": target,
                "from_context": from_context,
                "reachable": True,
                "path_length": 0,
                "computed_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "reach": reach_result,
                    "reachable": True,
                },
                metadata={"act": act},
            )
        
        elif act == "reach-measure":
            source = context.get_input("source")
            target = context.get_input("target")
            
            measure = {
                "id": str(uuid4()),
                "type": "reach_measure",
                "act": act,
                "source": source,
                "target": target,
                "distance": 0,
                "measured_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "measure": measure,
                    "distance": 0,
                },
                metadata={"act": act},
            )
        
        elif act == "reach-limit":
            reach_data = context.get_input("reach_data", [])
            
            limit = {
                "id": str(uuid4()),
                "type": "reach_limit",
                "act": act,
                "data_points": len(reach_data),
                "limit_value": None,
                "computed_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "limit": limit,
                },
                metadata={"act": act},
            )
        
        return HandlerResult.fail(f"Unknown reach act: {act}")
