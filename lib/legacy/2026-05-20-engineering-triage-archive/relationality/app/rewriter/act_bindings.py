"""Act → handler → datatype bindings.

This module declares, in one place, how earned acts are realised by
Python handlers and which datatypes those handlers expect/produce.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from app.rewriter.handlers import ActHandler
from app.rewriter.acts.measure import MeasureHandler
from app.rewriter.acts.entropy import EntropyHandler
from app.rewriter.acts.profile_measure import ProfileMeasureHandler
from app.rewriter.acts.profile_integral import ProfileIntegralHandler
from app.rewriter.acts.physics_state import PhysicsStateHandler
from app.rewriter.acts.flow_measure_step import FlowMeasureStepHandler
from app.rewriter.acts.introspect_trace import IntrospectTraceHandler
from app.rewriter.acts.introspect_context import IntrospectContextHandler
from app.rewriter.acts.sample_observable import SampleObservableHandler
from app.rewriter.acts.emit_telemetry import EmitTelemetryHandler
from app.rewriter.acts.baseline_convergence import BaselineConvergenceHandler
from app.rewriter.acts.baseline_limit import BaselineLimitHandler
from app.rewriter.acts.reach import ReachHandler as ReachActHandler
from app.rewriter.acts.build_profile_tower import BuildProfileTowerHandler
from app.rewriter.acts.build_nested_profile_tower import (
    BuildNestedProfileTowerHandler,
)
from app.rewriter.acts.build_composite_profile_tower import (
    BuildCompositeProfileTowerHandler,
)
from app.rewriter.acts.box_modality import BoxModalityHandler
from app.rewriter.acts.diamond_modality import DiamondModalityHandler
from app.rewriter.parametric_handlers import ParametricRuntimeHandler
from app.rewriter.acts.build_context import BuildContextHandler
from app.rewriter.acts.govern_regime import GovernRegimeHandler
from app.schemas.measurement import MeasurementEvent
from app.schemas.physics import PhysicsState, PhysicsScenario, SimulationRun
from app.schemas.tower import ProfileTower, NestedProfileTower, CompositeProfileTower
from app.schemas.modality import ModalEvaluation
from app.schemas.context import ParametricContext
from app.schemas.stlc import TermAST, TypingContext, TypeAST


class ActBinding:
    """Binding between an act, its handler, and data schemas."""

    def __init__(
        self,
        handler: Type[ActHandler],
        input_schema: Optional[type] = None,
        output_schema: Optional[type] = None,
    ) -> None:
        self.handler = handler
        self.input_schema = input_schema
        self.output_schema = output_schema


ACT_BINDINGS: Dict[str, ActBinding] = {
    # Measurement algebra acts (from Measurement Stack)
    # 'measure' operates on generic observables/measures at the algebra level.
    "measure": ActBinding(
        handler=MeasureHandler,
        input_schema=None,
        output_schema=None,
    ),
    # 'entropy' over distributions / observables.
    "entropy": ActBinding(
        handler=EntropyHandler,
        input_schema=None,
        output_schema=None,
    ),
    "profile-measure": ActBinding(
        handler=ProfileMeasureHandler,
        input_schema=None,
        output_schema=None,
    ),
    "profile-integral": ActBinding(
        handler=ProfileIntegralHandler,
        input_schema=None,
        output_schema=None,
    ),

    # Parametric context runtime acts
    "build-evaluation-context": ActBinding(
        handler=BuildContextHandler,
        input_schema=None,
        output_schema=ParametricContext,
    ),

    # Policy stack bridge: govern-regime realises a policy regime
    # in the runtime policy engine.
    "govern-regime": ActBinding(
        handler=GovernRegimeHandler,
        input_schema=None,
        output_schema=None,
    ),
    "context-flow": ActBinding(
        handler=ParametricRuntimeHandler,
        input_schema=ParametricContext,
        output_schema=ParametricContext,
    ),
    "context-nucleus": ActBinding(
        handler=ParametricRuntimeHandler,
        input_schema=ParametricContext,
        output_schema=ParametricContext,
    ),
    "context-dynamics": ActBinding(
        handler=ParametricRuntimeHandler,
        input_schema=ParametricContext,
        output_schema=ParametricContext,
    ),

    # STLC typing / evaluation simulation
    "judge-typing": ActBinding(
        handler=None,  # handler is registered via HandlerRegistry; schema hints only
        input_schema=None,          # term/context are passed as separate fields
        output_schema=TypeAST,      # returns an inferred type when successful
    ),
    "evaluate-observation": ActBinding(
        handler=None,   # per-act handler registered via HandlerRegistry
        input_schema=None,          # observation is passed as a dict
        output_schema=TermAST,      # normal form term AST when evaluation succeeds
    ),

    # Physics simulation acts
    "physics-state": ActBinding(
        handler=PhysicsStateHandler,
        input_schema=None,
        output_schema=PhysicsState,
    ),
    "flow-measure-step": ActBinding(
        handler=FlowMeasureStepHandler,
        input_schema=PhysicsState,
        output_schema=PhysicsState,
    ),

    # Profile tower acts (from Tower Interaction / topology specs)
    "build-profile-tower": ActBinding(
        handler=BuildProfileTowerHandler,
        input_schema=None,           # base_profile/height are scalar inputs
        output_schema=ProfileTower,
    ),
    "build-nested-profile-tower": ActBinding(
        handler=BuildNestedProfileTowerHandler,
        input_schema=None,           # outer_tower/inner_profile/nesting_level
        output_schema=NestedProfileTower,
    ),
    "build-composite-profile-tower": ActBinding(
        handler=BuildCompositeProfileTowerHandler,
        input_schema=None,           # towers/composition_type
        output_schema=CompositeProfileTower,
    ),

    # Modal tower acts (from modal logic / modality tower specs)
    # Here we treat box/diamond evaluations as ModalEvaluation payloads.
    "box-modality": ActBinding(
        handler=BoxModalityHandler,
        input_schema=None,
        output_schema=ModalEvaluation,
    ),
    "diamond-modality": ActBinding(
        handler=DiamondModalityHandler,
        input_schema=None,
        output_schema=ModalEvaluation,
    ),

    # Baseline / renewal stack
    "baseline-convergence": ActBinding(
        handler=BaselineConvergenceHandler,
        input_schema=None,
        output_schema=None,
    ),
    "baseline-limit": ActBinding(
        handler=BaselineLimitHandler,
        input_schema=None,
        output_schema=None,
    ),

    # Reachability / reach-measure acts
    "reach": ActBinding(
        handler=ReachActHandler,
        input_schema=None,
        output_schema=None,
    ),
}
