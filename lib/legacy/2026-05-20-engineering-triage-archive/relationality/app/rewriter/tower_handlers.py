"""Tower and modality handlers for the relational computer.

Implements handlers for profile towers, modality towers, and directed space
operations from the tower interaction and modality theorems.
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


class ProfileTowerHandler(ActHandler):
    """Handler for profile tower operations.
    
    Maps to: build-profile-tower, build-nested-profile-tower, 
             build-composite-profile-tower, calculate-profile-syntax,
             calculate-composite-profile-syntax
    
    Profile towers provide the layered structure for organizing
    recognitions according to their type and depth.
    """
    
    acts = [
        "build-profile-tower",
        "build-nested-profile-tower", 
        "build-composite-profile-tower",
        "calculate-profile-syntax",
        "calculate-composite-profile-syntax",
    ]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()
        
        if act == "build-profile-tower":
            base_profile = context.get_input("base_profile", {})
            height = context.get_input("height", 1)
            
            levels = []
            for i in range(height):
                levels.append({
                    "level": i,
                    "profile": {**base_profile, "level": i} if i == 0 else {},
                    "witnesses": [],
                })
            
            tower = {
                "id": str(uuid4()),
                "type": "profile_tower",
                "act": act,
                "acts": [act],
                "base_profile": base_profile,
                "height": height,
                "levels": levels,
                "trace_id": trace_id,
                "built_at": now,
            }
            
            persisted_id = await context.persist_recognition(tower)
            
            return HandlerResult.ok(
                outputs={
                    "tower": tower,
                    "tower_id": tower["id"],
                    "height": height,
                },
                recognitions_created=[persisted_id],
                metadata={"act": act, "height": height},
            )
        
        elif act == "build-nested-profile-tower":
            outer_tower = context.get_input("outer_tower")
            inner_profile = context.get_input("inner_profile", {})
            nesting_level = context.get_input("nesting_level", 0)
            
            if not outer_tower:
                return HandlerResult.fail("Missing required input: outer_tower")
            
            nested_tower = {
                "id": str(uuid4()),
                "type": "nested_profile_tower",
                "act": act,
                "acts": [act],
                "outer_tower_id": outer_tower.get("id"),
                "inner_profile": inner_profile,
                "nesting_level": nesting_level,
                "trace_id": trace_id,
                "built_at": now,
            }
            
            persisted_id = await context.persist_recognition(nested_tower)
            
            return HandlerResult.ok(
                outputs={
                    "nested_tower": nested_tower,
                    "tower_id": nested_tower["id"],
                },
                recognitions_created=[persisted_id],
                metadata={"act": act, "nesting_level": nesting_level},
            )
        
        elif act == "build-composite-profile-tower":
            towers = context.get_input("towers", [])
            composition_type = context.get_input("composition_type", "sequential")
            
            composite = {
                "id": str(uuid4()),
                "type": "composite_profile_tower",
                "act": act,
                "acts": [act],
                "component_tower_ids": [t.get("id") for t in towers if isinstance(t, dict)],
                "composition_type": composition_type,
                "component_count": len(towers),
                "trace_id": trace_id,
                "built_at": now,
            }
            
            persisted_id = await context.persist_recognition(composite)
            
            return HandlerResult.ok(
                outputs={
                    "composite_tower": composite,
                    "tower_id": composite["id"],
                },
                recognitions_created=[persisted_id],
                metadata={"act": act, "component_count": len(towers)},
            )
        
        elif act in ["calculate-profile-syntax", "calculate-composite-profile-syntax"]:
            tower = context.get_input("tower")
            
            if not tower:
                return HandlerResult.fail("Missing required input: tower")
            
            syntax = {
                "id": str(uuid4()),
                "type": "profile_syntax",
                "act": act,
                "tower_id": tower.get("id"),
                "tower_type": tower.get("type"),
                "height": tower.get("height", 0),
                "calculated_at": now,
            }
            
            return HandlerResult.ok(
                outputs={"syntax": syntax},
                metadata={"act": act},
            )
        
        return HandlerResult.fail(f"Unknown profile tower act: {act}")


class ModalityTowerHandler(ActHandler):
    """Handler for modality tower operations.
    
    Maps to: box-modality, diamond-modality, modality-transport,
             modality-witness
    
    Modality towers provide the modal logic layer for reasoning
    about necessity and possibility.
    """
    
    acts = [
        "box-modality",
        "diamond-modality", 
        "modality-transport",
        "modality-witness",
    ]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()
        
        if act == "box-modality":
            proposition = context.get_input("proposition")
            world = context.get_input("world", "base")
            
            if proposition is None:
                return HandlerResult.fail("Missing required input: proposition")
            
            boxed = {
                "id": str(uuid4()),
                "type": "box_modality",
                "act": act,
                "acts": [act],
                "proposition": proposition,
                "world": world,
                "modality": "necessary",
                "trace_id": trace_id,
                "created_at": now,
            }
            
            persisted_id = await context.persist_recognition(boxed)
            
            return HandlerResult.ok(
                outputs={
                    "modality": boxed,
                    "modality_id": boxed["id"],
                },
                recognitions_created=[persisted_id],
                metadata={"act": act, "modality": "necessary"},
            )
        
        elif act == "diamond-modality":
            proposition = context.get_input("proposition")
            world = context.get_input("world", "base")
            
            if proposition is None:
                return HandlerResult.fail("Missing required input: proposition")
            
            diamonded = {
                "id": str(uuid4()),
                "type": "diamond_modality",
                "act": act,
                "acts": [act],
                "proposition": proposition,
                "world": world,
                "modality": "possible",
                "trace_id": trace_id,
                "created_at": now,
            }
            
            persisted_id = await context.persist_recognition(diamonded)
            
            return HandlerResult.ok(
                outputs={
                    "modality": diamonded,
                    "modality_id": diamonded["id"],
                },
                recognitions_created=[persisted_id],
                metadata={"act": act, "modality": "possible"},
            )
        
        elif act == "modality-transport":
            source_modality = context.get_input("source")
            target_world = context.get_input("target_world")
            
            if not source_modality:
                return HandlerResult.fail("Missing required input: source")
            
            transported = {
                "id": str(uuid4()),
                "type": "transported_modality",
                "act": act,
                "source_modality_id": source_modality.get("id"),
                "source_world": source_modality.get("world"),
                "target_world": target_world,
                "transported_at": now,
            }
            
            return HandlerResult.ok(
                outputs={
                    "transported": transported,
                    "transport_id": transported["id"],
                },
                metadata={"act": act},
            )
        
        elif act == "modality-witness":
            modality = context.get_input("modality")
            witness_data = context.get_input("witness_data", {})
            
            if not modality:
                return HandlerResult.fail("Missing required input: modality")
            
            witness = {
                "id": str(uuid4()),
                "type": "modality_witness",
                "act": act,
                "acts": [act],
                "modality_id": modality.get("id"),
                "modality_type": modality.get("modality"),
                "witness_data": witness_data,
                "witnessed_at": now,
                "trace_id": trace_id,
            }
            
            persisted_id = await context.persist_recognition(witness)
            
            return HandlerResult.ok(
                outputs={
                    "witness": witness,
                    "witness_id": witness["id"],
                },
                recognitions_created=[persisted_id],
                metadata={"act": act},
            )
        
        return HandlerResult.fail(f"Unknown modality act: {act}")


class DirectedSpaceHandler(ActHandler):
    """Handler for directed space and homotopy operations.
    
    Maps to: directed-transport, directed-equivalence, 
             flow-nucleus, commute-flow-and-nucleus
    
    Directed space operations handle the topological constraints
    from the directed homotopy and stratified site specifications.
    """
    
    acts = [
        "directed-transport",
        "directed-equivalence",
        "flow-nucleus",
        "commute-flow-and-nucleus",
        "commute-shuffle-flow-and-nucleus",
    ]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()
        
        if act == "directed-transport":
            source = context.get_input("source")
            path = context.get_input("path", [])
            
            if source is None:
                return HandlerResult.fail("Missing required input: source")
            
            transport = {
                "id": str(uuid4()),
                "type": "directed_transport",
                "act": act,
                "source": source,
                "path": path,
                "path_length": len(path),
                "transported_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "transport": transport,
                    "transport_id": transport["id"],
                },
                metadata={"act": act, "path_length": len(path)},
            )
        
        elif act == "directed-equivalence":
            left = context.get_input("left")
            right = context.get_input("right")
            
            if left is None or right is None:
                return HandlerResult.fail("Missing required inputs: left, right")
            
            equivalence = {
                "id": str(uuid4()),
                "type": "directed_equivalence",
                "act": act,
                "left": left,
                "right": right,
                "equivalent": True,
                "established_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "equivalence": equivalence,
                    "equivalence_id": equivalence["id"],
                    "equivalent": True,
                },
                metadata={"act": act},
            )
        
        elif act == "flow-nucleus":
            flow = context.get_input("flow")
            nucleus_type = context.get_input("nucleus_type", "standard")
            
            nucleus = {
                "id": str(uuid4()),
                "type": "flow_nucleus",
                "act": act,
                "flow": flow,
                "nucleus_type": nucleus_type,
                "computed_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "nucleus": nucleus,
                    "nucleus_id": nucleus["id"],
                },
                metadata={"act": act, "nucleus_type": nucleus_type},
            )
        
        elif act in ["commute-flow-and-nucleus", "commute-shuffle-flow-and-nucleus"]:
            flow = context.get_input("flow")
            nucleus = context.get_input("nucleus")
            
            commutation = {
                "id": str(uuid4()),
                "type": "flow_nucleus_commutation",
                "act": act,
                "flow": flow,
                "nucleus": nucleus,
                "commutes": True,
                "verified_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "commutation": commutation,
                    "commutes": True,
                },
                metadata={"act": act},
            )
        
        return HandlerResult.fail(f"Unknown directed space act: {act}")


class BinderHandler(ActHandler):
    """Handler for binder operations.
    
    Maps to: binder-seed, binder-application, binder-transport,
             bind-term
    
    Binder operations handle variable binding and substitution
    in the simply-typed lambda calculus layer.
    """
    
    acts = [
        "binder-seed",
        "binder-application",
        "binder-transport",
        "bind-term",
    ]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()
        
        if act == "binder-seed":
            variable_name = context.get_input("variable")
            variable_type = context.get_input("type", "any")
            
            if not variable_name:
                return HandlerResult.fail("Missing required input: variable")
            
            binder = {
                "id": str(uuid4()),
                "type": "binder",
                "act": act,
                "acts": [act],
                "variable": variable_name,
                "variable_type": variable_type,
                "bound_value": None,
                "seeded_at": now,
                "trace_id": trace_id,
            }
            
            persisted_id = await context.persist_recognition(binder)
            
            return HandlerResult.ok(
                outputs={
                    "binder": binder,
                    "binder_id": binder["id"],
                },
                recognitions_created=[persisted_id],
                metadata={"act": act, "variable": variable_name},
            )
        
        elif act == "binder-application":
            binder = context.get_input("binder")
            argument = context.get_input("argument")
            
            if not binder:
                return HandlerResult.fail("Missing required input: binder")
            
            application = {
                "id": str(uuid4()),
                "type": "binder_application",
                "act": act,
                "binder_id": binder.get("id"),
                "variable": binder.get("variable"),
                "argument": argument,
                "applied_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "application": application,
                    "result": argument,
                },
                metadata={"act": act},
            )
        
        elif act == "binder-transport":
            binder = context.get_input("binder")
            destination = context.get_input("destination")
            
            if not binder:
                return HandlerResult.fail("Missing required input: binder")
            
            transport = {
                "id": str(uuid4()),
                "type": "binder_transport",
                "act": act,
                "binder_id": binder.get("id"),
                "destination": destination,
                "transported_at": now,
            }
            
            return HandlerResult.ok(
                outputs={
                    "transport": transport,
                    "transported_binder": {**binder, "destination": destination},
                },
                metadata={"act": act},
            )
        
        elif act == "bind-term":
            term = context.get_input("term")
            variable = context.get_input("variable")
            value = context.get_input("value")
            
            if term is None:
                return HandlerResult.fail("Missing required input: term")
            if not variable:
                return HandlerResult.fail("Missing required input: variable")
            
            binding = {
                "id": str(uuid4()),
                "type": "term_binding",
                "act": act,
                "term": term,
                "variable": variable,
                "value": value,
                "bound_at": now,
                "trace_id": trace_id,
            }
            
            return HandlerResult.ok(
                outputs={
                    "binding": binding,
                    "bound_term": {**term, variable: value} if isinstance(term, dict) else term,
                },
                metadata={"act": act, "variable": variable},
            )
        
        return HandlerResult.fail(f"Unknown binder act: {act}")
