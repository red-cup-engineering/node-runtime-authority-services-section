"""Trace infrastructure handlers for the relational computer.

Implements the trace-building acts from the Trace Infrastructure theorem:
- Sequencing: start-trace, advance-trace, continue-trace, trace-step
- Head/tail control: head-trace, tail-trace, bind-trace
- Renewal: renew-trace, restep-trace
- Context bridging: seed-first-context, extend-context, retrace-context
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


class TraceSequencingHandler(ActHandler):
    """Handler for trace sequencing operations.
    
    Maps to: start-trace, advance-trace, continue-trace, trace-step
    
    These acts assemble the trace spine - the ordered backbone for all
    subsequent operations (terms, observations, etc.).
    """
    
    acts = ["start-trace", "advance-trace", "continue-trace", "trace-step"]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()
        
        if act == "start-trace":
            parent_trace = context.get_input("parent_trace")
            initial_data = context.get_input("initial_data", {})
            
            new_trace = {
                "id": str(uuid4()),
                "type": "trace",
                "act": act,
                "acts": [act],
                "parent_trace": parent_trace,
                "root_trace_id": trace_id,
                "started_at": now,
                "steps": [],
                "current_position": 0,
                "status": "active",
                "initial_data": initial_data,
            }
            
            persisted_id = await context.persist_recognition(new_trace)
            
            return HandlerResult.ok(
                outputs={
                    "trace": new_trace,
                    "trace_id": new_trace["id"],
                    "position": 0,
                },
                recognitions_created=[persisted_id],
                metadata={"act": act},
            )
        
        elif act == "advance-trace":
            current_trace = context.get_input("trace")
            step_data = context.get_input("step_data", {})
            
            if not current_trace:
                return HandlerResult.fail("Missing required input: trace")
            
            position = current_trace.get("current_position", 0) + 1
            step = {
                "position": position,
                "data": step_data,
                "advanced_at": now,
                "witness": str(uuid4()),
            }
            
            steps = list(current_trace.get("steps", []))
            steps.append(step)
            
            advanced_trace = dict(current_trace)
            advanced_trace["steps"] = steps
            advanced_trace["current_position"] = position
            advanced_trace["last_advanced"] = now
            
            return HandlerResult.ok(
                outputs={
                    "trace": advanced_trace,
                    "step": step,
                    "position": position,
                },
                metadata={"act": act, "position": position},
            )
        
        elif act == "continue-trace":
            current_trace = context.get_input("trace")
            continuation_data = context.get_input("continuation_data", {})
            
            if not current_trace:
                return HandlerResult.fail("Missing required input: trace")
            
            continuation = {
                "id": str(uuid4()),
                "type": "continuation",
                "parent_trace_id": current_trace.get("id"),
                "continued_from_position": current_trace.get("current_position", 0),
                "continuation_data": continuation_data,
                "continued_at": now,
            }
            
            continued_trace = dict(current_trace)
            continued_trace["continued_at"] = now
            continued_trace["status"] = "continued"
            
            return HandlerResult.ok(
                outputs={
                    "trace": continued_trace,
                    "continuation": continuation,
                },
                metadata={"act": act},
            )
        
        elif act == "trace-step":
            current_trace = context.get_input("trace")
            step_operation = context.get_input("operation")
            step_payload = context.get_input("payload", {})
            
            if not current_trace:
                return HandlerResult.fail("Missing required input: trace")
            
            position = current_trace.get("current_position", 0) + 1
            step = {
                "position": position,
                "operation": step_operation,
                "payload": step_payload,
                "stepped_at": now,
                "witness": str(uuid4()),
            }
            
            steps = list(current_trace.get("steps", []))
            steps.append(step)
            
            updated_trace = dict(current_trace)
            updated_trace["steps"] = steps
            updated_trace["current_position"] = position
            
            return HandlerResult.ok(
                outputs={
                    "trace": updated_trace,
                    "step": step,
                    "position": position,
                },
                metadata={"act": act, "position": position},
            )
        
        return HandlerResult.fail(f"Unknown trace sequencing act: {act}")


class TraceHeadTailHandler(ActHandler):
    """Handler for trace head/tail control.
    
    Maps to: head-trace, tail-trace, bind-trace
    
    These acts let us focus on subsections of the trace while tracking witnesses.
    """
    
    acts = ["head-trace", "tail-trace", "bind-trace"]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace = context.get_input("trace")
        
        if not trace:
            return HandlerResult.fail("Missing required input: trace")
        
        now = datetime.utcnow().isoformat()
        steps = trace.get("steps", [])
        
        if act == "head-trace":
            count = context.get_input("count", 1)
            
            head_steps = steps[:count]
            head = {
                "id": str(uuid4()),
                "type": "trace_head",
                "source_trace_id": trace.get("id"),
                "head_count": count,
                "steps": head_steps,
                "extracted_at": now,
            }
            
            return HandlerResult.ok(
                outputs={
                    "head": head,
                    "steps": head_steps,
                    "count": len(head_steps),
                },
                metadata={"act": act},
            )
        
        elif act == "tail-trace":
            count = context.get_input("count", 1)
            
            tail_steps = steps[-count:] if count <= len(steps) else steps
            tail = {
                "id": str(uuid4()),
                "type": "trace_tail",
                "source_trace_id": trace.get("id"),
                "tail_count": count,
                "steps": tail_steps,
                "extracted_at": now,
            }
            
            return HandlerResult.ok(
                outputs={
                    "tail": tail,
                    "steps": tail_steps,
                    "count": len(tail_steps),
                },
                metadata={"act": act},
            )
        
        elif act == "bind-trace":
            binding_name = context.get_input("name")
            binding_value = context.get_input("value")
            
            if not binding_name:
                return HandlerResult.fail("Missing required input: name")
            
            bindings = dict(trace.get("bindings", {}))
            bindings[binding_name] = {
                "value": binding_value,
                "bound_at": now,
                "witness": str(uuid4()),
            }
            
            bound_trace = dict(trace)
            bound_trace["bindings"] = bindings
            
            return HandlerResult.ok(
                outputs={
                    "trace": bound_trace,
                    "binding": bindings[binding_name],
                },
                metadata={"act": act, "binding_name": binding_name},
            )
        
        return HandlerResult.fail(f"Unknown head/tail act: {act}")


class TraceRenewalHandler(ActHandler):
    """Handler for trace renewal operations.
    
    Maps to: renew-trace, restep-trace
    
    These acts reintroduce stabilized tails, ensuring that persistent
    remnants can be reattached.
    """
    
    acts = ["renew-trace", "restep-trace"]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace = context.get_input("trace")
        
        if not trace:
            return HandlerResult.fail("Missing required input: trace")
        
        now = datetime.utcnow().isoformat()
        
        if act == "renew-trace":
            baseline = context.get_input("baseline", {})
            
            renewal_id = str(uuid4())
            renewed_trace = dict(trace)
            renewed_trace["renewal_id"] = renewal_id
            renewed_trace["renewed_at"] = now
            renewed_trace["baseline"] = baseline
            renewed_trace["status"] = "renewed"
            
            renewal_record = {
                "id": renewal_id,
                "type": "renewal",
                "trace_id": trace.get("id"),
                "baseline": baseline,
                "renewed_at": now,
                "position_at_renewal": trace.get("current_position", 0),
            }
            
            return HandlerResult.ok(
                outputs={
                    "trace": renewed_trace,
                    "renewal": renewal_record,
                    "renewal_id": renewal_id,
                },
                metadata={"act": act},
            )
        
        elif act == "restep-trace":
            from_position = context.get_input("from_position", 0)
            
            steps = trace.get("steps", [])
            restep_id = str(uuid4())
            
            restep_record = {
                "id": restep_id,
                "type": "restep",
                "trace_id": trace.get("id"),
                "from_position": from_position,
                "to_position": trace.get("current_position", 0),
                "steps_replayed": len([s for s in steps if s.get("position", 0) >= from_position]),
                "restepped_at": now,
            }
            
            restepped_trace = dict(trace)
            restepped_trace["restep_id"] = restep_id
            restepped_trace["restepped_at"] = now
            
            return HandlerResult.ok(
                outputs={
                    "trace": restepped_trace,
                    "restep": restep_record,
                },
                metadata={"act": act, "from_position": from_position},
            )
        
        return HandlerResult.fail(f"Unknown renewal act: {act}")


class ContextBridgingHandler(ActHandler):
    """Handler for context bridging operations.
    
    Maps to: seed-first-context, extend-context, retrace-context
    
    These acts show how traces and contexts interlock, which is essential
    for evaluation and tower-building.
    """
    
    acts = ["seed-first-context", "extend-context", "retrace-context"]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        now = datetime.utcnow().isoformat()
        trace_id = str(context.trace_id)
        
        if act == "seed-first-context":
            initial_bindings = context.get_input("bindings", {})
            context_type = context.get_input("context_type", "evaluation")
            
            first_context = {
                "id": str(uuid4()),
                "type": "context",
                "context_type": context_type,
                "act": act,
                "acts": [act],
                "bindings": initial_bindings,
                "parent_context": None,
                "depth": 0,
                "trace_id": trace_id,
                "seeded_at": now,
            }
            
            persisted_id = await context.persist_recognition(first_context)
            
            return HandlerResult.ok(
                outputs={
                    "context": first_context,
                    "context_id": first_context["id"],
                },
                recognitions_created=[persisted_id],
                metadata={"act": act},
            )
        
        elif act == "extend-context":
            parent_context = context.get_input("context")
            extension_bindings = context.get_input("bindings", {})
            
            if not parent_context:
                return HandlerResult.fail("Missing required input: context")
            
            parent_bindings = parent_context.get("bindings", {})
            merged_bindings = {**parent_bindings, **extension_bindings}
            
            extended_context = {
                "id": str(uuid4()),
                "type": "context",
                "context_type": parent_context.get("context_type", "evaluation"),
                "act": act,
                "acts": [act],
                "bindings": merged_bindings,
                "parent_context": parent_context.get("id"),
                "depth": parent_context.get("depth", 0) + 1,
                "trace_id": trace_id,
                "extended_at": now,
            }
            
            persisted_id = await context.persist_recognition(extended_context)
            
            return HandlerResult.ok(
                outputs={
                    "context": extended_context,
                    "context_id": extended_context["id"],
                    "depth": extended_context["depth"],
                },
                recognitions_created=[persisted_id],
                metadata={"act": act, "depth": extended_context["depth"]},
            )
        
        elif act == "retrace-context":
            target_context = context.get_input("context")
            trace_to_replay = context.get_input("trace")
            
            if not target_context:
                return HandlerResult.fail("Missing required input: context")
            
            retrace_id = str(uuid4())
            retrace_record = {
                "id": retrace_id,
                "type": "retrace",
                "context_id": target_context.get("id"),
                "trace_id": trace_to_replay.get("id") if trace_to_replay else None,
                "retraced_at": now,
                "steps_considered": len(trace_to_replay.get("steps", [])) if trace_to_replay else 0,
            }
            
            retraced_context = dict(target_context)
            retraced_context["retrace_id"] = retrace_id
            retraced_context["retraced_at"] = now
            
            return HandlerResult.ok(
                outputs={
                    "context": retraced_context,
                    "retrace": retrace_record,
                },
                metadata={"act": act},
            )
        
        return HandlerResult.fail(f"Unknown context bridging act: {act}")


class AssignTraceHandler(ActHandler):
    """Handler for trace assignment operations.
    
    Maps to: assign-trace
    """
    
    acts = ["assign-trace"]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace = context.get_input("trace")
        name = context.get_input("name")
        value = context.get_input("value")
        
        if not trace:
            return HandlerResult.fail("Missing required input: trace")
        if not name:
            return HandlerResult.fail("Missing required input: name")
        
        now = datetime.utcnow().isoformat()
        
        assignments = dict(trace.get("assignments", {}))
        assignments[name] = {
            "value": value,
            "assigned_at": now,
            "witness": str(uuid4()),
        }
        
        assigned_trace = dict(trace)
        assigned_trace["assignments"] = assignments
        
        return HandlerResult.ok(
            outputs={
                "trace": assigned_trace,
                "assignment": assignments[name],
            },
            metadata={"act": act, "name": name},
        )
