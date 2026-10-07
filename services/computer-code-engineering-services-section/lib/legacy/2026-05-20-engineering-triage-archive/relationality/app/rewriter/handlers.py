"""Act handler registry and base classes.

Each handler implements the logic for one or more acts,
providing the concrete operations behind runbook steps.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional, Type
from uuid import UUID, uuid4


@dataclass
class HandlerResult:
    """Result of executing an act handler."""
    
    success: bool
    outputs: dict[str, Any] = field(default_factory=dict)
    recognitions_created: list[UUID] = field(default_factory=list)
    error_message: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=datetime.utcnow)
    
    @classmethod
    def ok(cls, outputs: Optional[dict[str, Any]] = None, **kwargs) -> "HandlerResult":
        return cls(success=True, outputs=outputs or {}, **kwargs)
    
    @classmethod
    def fail(cls, message: str, **kwargs) -> "HandlerResult":
        return cls(success=False, error_message=message, **kwargs)


class ExecutionContext:
    """Context passed to act handlers during execution."""
    
    def __init__(
        self,
        trace_id: UUID,
        step_id: str,
        inputs: dict[str, Any],
        db: Any = None,
        measurement_fabric: Any = None,
        known_acts: Optional[set[str]] = None,
        recognition_repo: Any = None,
        persist_recognitions: bool = True,
    ):
        self.trace_id = trace_id
        self.step_id = step_id
        self.inputs = inputs
        self.db = db
        self.measurement_fabric = measurement_fabric
        self.known_acts = known_acts or set()
        self.recognition_repo = recognition_repo
        self.persist_recognitions = persist_recognitions
        self._outputs: dict[str, dict[str, Any]] = {}
        self._recognitions: list[dict] = []
        self._persisted_ids: list[UUID] = []
    
    def get_input(self, name: str, default: Any = None) -> Any:
        """Get an input value by name."""
        return self.inputs.get(name, default)
    
    def require_input(self, name: str) -> Any:
        """Get a required input, raising if missing."""
        if name not in self.inputs:
            raise ValueError(f"Required input '{name}' not provided")
        return self.inputs[name]
    
    def set_output(self, step_id: str, name: str, value: Any) -> None:
        """Set an output value for a step."""
        if step_id not in self._outputs:
            self._outputs[step_id] = {}
        self._outputs[step_id][name] = value
    
    def get_output(self, step_id: str, name: str, default: Any = None) -> Any:
        """Get an output value from a previous step."""
        return self._outputs.get(step_id, {}).get(name, default)
    
    def add_recognition(self, recognition: dict) -> None:
        """Track a recognition created during execution."""
        self._recognitions.append(recognition)
    
    async def persist_recognition(self, recognition_data: dict) -> UUID:
        """Persist a recognition to the database if repo is available.
        
        Returns the UUID of the persisted or ephemeral recognition.
        """
        from app.schemas.recognition import TracePointCreate, TracePointRole
        
        rec_id = UUID(recognition_data.get("id", str(uuid4())))
        
        if self.persist_recognitions and self.recognition_repo:
            rec_type = recognition_data.get("type", "observation")
            try:
                rec_type_enum = TracePointRole(rec_type)
            except ValueError:
                rec_type_enum = TracePointRole.OBSERVATION
            
            create_data = TracePointCreate(
                type=rec_type_enum,
                title=recognition_data.get("title", f"{rec_type} from {self.step_id}"),
                content=recognition_data,
                acts=recognition_data.get("acts", [recognition_data.get("act", "unknown")]),
                tags=recognition_data.get("tags", []),
                metadata={
                    "trace_id": str(self.trace_id),
                    "step_id": self.step_id,
                    "persisted_at": datetime.utcnow().isoformat(),
                },
            )
            
            persisted = await self.recognition_repo.create(create_data)
            rec_id = persisted.id
            self._persisted_ids.append(rec_id)
        
        self._recognitions.append(recognition_data)
        return rec_id
    
    def get_persisted_ids(self) -> list[UUID]:
        """Get list of recognition IDs that were persisted to the database."""
        return self._persisted_ids.copy()


class ActHandler(ABC):
    """Base class for act handlers.
    
    Subclass this to implement the logic for specific acts.
    """
    
    acts: list[str] = []
    
    @abstractmethod
    async def execute(
        self,
        act: str,
        context: ExecutionContext,
    ) -> HandlerResult:
        """Execute the handler for the given act.
        
        Args:
            act: The specific act being executed.
            context: Execution context with inputs and outputs.
        
        Returns:
            HandlerResult indicating success/failure and outputs.
        """
        pass
    
    def validate_inputs(self, context: ExecutionContext) -> Optional[str]:
        """Validate inputs before execution.
        
        Returns:
            Error message if validation fails, None otherwise.
        """
        return None


class HandlerRegistry:
    """Registry of act handlers."""
    
    _instance: Optional["HandlerRegistry"] = None
    
    def __init__(self):
        self._handlers: dict[str, ActHandler] = {}
        self._handler_classes: list[Type[ActHandler]] = []
    
    @classmethod
    def get_instance(cls) -> "HandlerRegistry":
        """Get the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_builtin_handlers()
        return cls._instance
    
    def register(self, handler: ActHandler) -> None:
        """Register a handler for its acts."""
        for act in handler.acts:
            self._handlers[act] = handler
    
    def register_class(self, handler_class: Type[ActHandler]) -> None:
        """Register a handler class (instantiated on first use)."""
        self._handler_classes.append(handler_class)
        handler = handler_class()
        self.register(handler)
    
    def get_handler(self, act: str) -> Optional[ActHandler]:
        """Get the handler for an act."""
        return self._handlers.get(act)
    
    def has_handler(self, act: str) -> bool:
        """Check if a handler exists for an act."""
        return act in self._handlers
    
    def list_handled_acts(self) -> list[str]:
        """List all acts with registered handlers."""
        return sorted(self._handlers.keys())
    
    def _register_builtin_handlers(self) -> None:
        """Register the built-in handlers.

        Most handlers are registered directly here. Measurement algebra
        acts are additionally declared in `act_bindings.py` so we can
        associate them with datatypes.
        """
        from app.rewriter.builtin_handlers import (
            ValidateRecognitionHandler,
            NormalizeObservationHandler,
        )
        from app.rewriter.trace_handlers import (
            TraceSequencingHandler,
            TraceHeadTailHandler,
            TraceRenewalHandler,
            ContextBridgingHandler,
            AssignTraceHandler,
        )
        from app.rewriter.acts.measure import MeasureHandler
        from app.rewriter.acts.entropy import EntropyHandler
        from app.rewriter.acts.detailed_balance import DetailedBalanceHandler
        from app.rewriter.acts.mixing import MixingHandler
        from app.rewriter.acts.discipline import DisciplineHandler
        from app.rewriter.acts.filter_act import FilterActHandler
        from app.rewriter.acts.compose_discipline import ComposeDisciplineHandler
        from app.rewriter.acts.compose_filter_act import ComposeFilterActHandler
        from app.rewriter.acts.profile_measure import ProfileMeasureHandler
        from app.rewriter.acts.profile_integral import ProfileIntegralHandler
        from app.rewriter.acts.observation_kernel import ObservationKernelHandler
        from app.rewriter.acts.fixed_kernel import FixedKernelHandler
        from app.rewriter.acts.profile_kernel_step import ProfileKernelStepHandler
        from app.rewriter.acts.profile_kernel_chain import ProfileKernelChainHandler
        from app.rewriter.acts.fixed_chain import FixedChainHandler
        from app.rewriter.acts.traceability_view import TraceabilityViewHandler
        from app.rewriter.acts.flow_observation import FlowObservationHandler
        from app.rewriter.acts.flow_observation_equivalence import (
            FlowObservationEquivalenceHandler,
        )
        from app.rewriter.acts.seed_evaluation_context import (
            SeedEvaluationContextHandler,
        )
        from app.rewriter.acts.substitution_term import (
            SubstitutionTermHandler,
        )
        from app.rewriter.acts.reduce import ReduceHandler
        from app.rewriter.acts.build_reducible_environment import (
            BuildReducibleEnvironmentHandler,
        )
        from app.rewriter.acts.recognition_act import RecognitionActHandler
        from app.rewriter.acts.entry_act import EntryHandler
        from app.rewriter.acts.lead_entry_act import LeadEntryHandler
        from app.rewriter.acts.trail_entry_act import TrailEntryHandler
        from app.rewriter.acts.ground_recognition_act import (
            GroundRecognitionHandler,
        )
        from app.rewriter.acts.cap_recognition_act import CapRecognitionHandler
        from app.rewriter.acts.order_recognition_act import OrderRecognitionHandler
        from app.rewriter.acts.meet_recognition_act import MeetRecognitionHandler
        from app.rewriter.acts.join_recognition_act import JoinRecognitionHandler
        from app.rewriter.acts.include_exclude_imply_recognition_act import (
            IncludeRecognitionHandler,
            ExcludeRecognitionHandler,
            ImplyRecognitionHandler,
        )
        from app.rewriter.acts.shape_recognition_act import ShapeRecognitionHandler
        from app.rewriter.acts.construct_types_act import ConstructTypesHandler
        from app.rewriter.acts.collect_types_act import CollectTypesHandler
        from app.rewriter.acts.construct_terms_act import ConstructTermsHandler
        from app.rewriter.acts.collect_terms_act import CollectTermsHandler
        from app.rewriter.acts.construct_contexts_act import ConstructContextsHandler
        from app.rewriter.acts.collect_contexts_act import CollectContextsHandler
        from app.rewriter.acts.exclude_act import ExcludeHandler
        from app.rewriter.acts.articulate_act import ArticulateHandler
        from app.rewriter.acts.emerge_reflex_act import EmergeReflexHandler
        from app.rewriter.acts.reflex_act import ReflexHandler
        from app.rewriter.acts.relate_act import RelateHandler
        from app.rewriter.acts.not_relate_act import NotRelateHandler
        from app.rewriter.acts.witness_act import WitnessActHandler
        from app.rewriter.acts.something_act import SomethingHandler
        from app.rewriter.acts.nothing_act import NothingHandler
        from app.rewriter.acts.void_act import VoidHandler
        from app.rewriter.acts.first_name_act import FirstNameHandler
        from app.rewriter.acts.self_naming_act import SelfNamingHandler
        from app.rewriter.acts.relationlessness_act import RelationlessnessHandler
        from app.rewriter.acts.recognize_syntax import RecognizeSyntaxHandler
        from app.rewriter.acts.normalize_syntax import NormalizeSyntaxHandler
        from app.rewriter.acts.sound_syntax import SoundSyntaxHandler
        from app.rewriter.acts.judge_typing import JudgeTypingHandler
        from app.rewriter.acts.normalize_observation import (
            NormalizeObservationHandler as NormalizeObservationActHandler,
        )
        from app.rewriter.acts.normalize_strongly import NormalizeStronglyHandler
        from app.rewriter.acts.start_trace import StartTraceHandler
        from app.rewriter.acts.advance_trace import AdvanceTraceHandler
        from app.rewriter.acts.continue_trace import ContinueTraceHandler
        from app.rewriter.acts.trace_step import TraceStepHandler
        from app.rewriter.acts.head_trace import HeadTraceHandler
        from app.rewriter.acts.tail_trace import TailTraceHandler
        from app.rewriter.acts.bind_trace import BindTraceHandler
        from app.rewriter.acts.renew_trace import RenewTraceHandler
        from app.rewriter.acts.restep_trace import RestepTraceHandler
        from app.rewriter.acts.seed_first_context import SeedFirstContextHandler
        from app.rewriter.acts.extend_context import ExtendContextHandler
        from app.rewriter.acts.extend_first_context import ExtendFirstContextHandler
        from app.rewriter.acts.renew_context import RenewContextHandler
        from app.rewriter.acts.extend_first_context import ExtendFirstContextHandler
        from app.rewriter.acts.retrace_context import RetraceContextHandler
        from app.rewriter.acts.assign_trace import AssignTraceHandler as AssignTraceActHandler
        from app.rewriter.acts.contextualize_trace import ContextualizeTraceHandler
        from app.rewriter.acts.complete_trace import CompleteTraceHandler
        from app.rewriter.acts.seed_observation import SeedObservationHandler
        from app.rewriter.acts.seed_value import SeedValueHandler
        from app.rewriter.acts.seed_term import SeedTermHandler
        from app.rewriter.acts.recognize_value import RecognizeValueHandler
        from app.rewriter.acts.recognize_observation import (
            RecognizeObservationHandler,
        )
        from app.rewriter.acts.recognize_context import RecognizeContextHandler
        from app.rewriter.acts.witness_judgement import WitnessJudgementHandler
        from app.rewriter.acts.witness_observation import WitnessObservationHandler
        from app.rewriter.acts.witness_value import WitnessValueHandler
        from app.rewriter.acts.evaluate_observation import EvaluateObservationHandler
        from app.rewriter.acts.evaluate_judgement import EvaluateJudgementHandler
        from app.rewriter.acts.evaluate_observation_equivalence import (
            EvaluateObservationEquivalenceHandler,
        )
        from app.rewriter.acts.physics_state import PhysicsStateHandler
        from app.rewriter.acts.flow_measure_step import FlowMeasureStepHandler
        from app.rewriter.acts.build_profile_tower import BuildProfileTowerHandler
        from app.rewriter.acts.build_nested_profile_tower import (
            BuildNestedProfileTowerHandler,
        )
        from app.rewriter.acts.build_composite_profile_tower import (
            BuildCompositeProfileTowerHandler,
        )
        from app.rewriter.acts.calculate_profile_syntax import (
            CalculateProfileSyntaxHandler,
        )
        from app.rewriter.acts.calculate_composite_profile_syntax import (
            CalculateCompositeProfileSyntaxHandler,
        )
        from app.rewriter.acts.box_modality import BoxModalityHandler
        from app.rewriter.acts.diamond_modality import DiamondModalityHandler
        from app.rewriter.acts.directed_transport import DirectedTransportHandler
        from app.rewriter.acts.directed_equivalence import DirectedEquivalenceHandler
        from app.rewriter.acts.harmonic_mode import HarmonicModeHandler
        from app.rewriter.acts.spectrum_seed import SpectrumSeedHandler
        from app.rewriter.acts.flow_nucleus import FlowNucleusHandler
        from app.rewriter.acts.commute_flow_and_nucleus import (
            CommuteFlowAndNucleusHandler,
        )
        from app.rewriter.acts.commute_shuffle_flow_and_nucleus import (
            CommuteShuffleFlowAndNucleusHandler,
        )
        from app.rewriter.acts.binder_seed import BinderSeedHandler
        from app.rewriter.acts.binder_application import BinderApplicationHandler
        from app.rewriter.acts.binder_transport import BinderTransportHandler
        from app.rewriter.acts.bind_term_act import BindTermHandler
        from app.rewriter.acts.baseline_convergence import BaselineConvergenceHandler
        from app.rewriter.acts.baseline_limit import BaselineLimitHandler
        from app.rewriter.acts.reach import ReachHandler as ReachActHandler
        from app.rewriter.parametric_handlers import ParametricRuntimeHandler
        from app.rewriter.acts.build_context import BuildContextHandler
        from app.rewriter.acts.govern_regime import GovernRegimeHandler
        from app.rewriter.acts.equate_contexts_act import EquateContextsHandler
        from app.rewriter.acts.seed_judgement_triad import SeedJudgementTriadHandler
        from app.rewriter.acts.trace_judgement_triad import TraceJudgementTriadHandler

        # Core handlers.
        for handler_class in [
            ValidateRecognitionHandler,
            NormalizeObservationHandler,
            TraceSequencingHandler,
            TraceHeadTailHandler,
            TraceRenewalHandler,
            ContextBridgingHandler,
            AssignTraceHandler,
            MeasureHandler,
            EntropyHandler,
            DetailedBalanceHandler,
            MixingHandler,
            DisciplineHandler,
            FilterActHandler,
            ComposeDisciplineHandler,
            ComposeFilterActHandler,
            ProfileMeasureHandler,
            ProfileIntegralHandler,
            ObservationKernelHandler,
            FixedKernelHandler,
            ProfileKernelStepHandler,
            ProfileKernelChainHandler,
            FixedChainHandler,
            TraceabilityViewHandler,
            ProfileKernelStepHandler,
            ProfileKernelChainHandler,
            FixedChainHandler,
            FlowObservationHandler,
            FlowObservationEquivalenceHandler,
            SeedEvaluationContextHandler,
            SubstitutionTermHandler,
            ReduceHandler,
            BuildReducibleEnvironmentHandler,
            RecognitionActHandler,
            EntryHandler,
            LeadEntryHandler,
            TrailEntryHandler,
            GroundRecognitionHandler,
            CapRecognitionHandler,
            OrderRecognitionHandler,
            MeetRecognitionHandler,
            JoinRecognitionHandler,
            IncludeRecognitionHandler,
            ExcludeRecognitionHandler,
            ImplyRecognitionHandler,
            ShapeRecognitionHandler,
            ConstructTypesHandler,
            CollectTypesHandler,
            ConstructTermsHandler,
            CollectTermsHandler,
            ConstructContextsHandler,
            CollectContextsHandler,
            EquateContextsHandler,
            ExcludeHandler,
            ArticulateHandler,
            EmergeReflexHandler,
            ReflexHandler,
            RelateHandler,
            NotRelateHandler,
            WitnessActHandler,
            SomethingHandler,
            NothingHandler,
            VoidHandler,
            FirstNameHandler,
            SelfNamingHandler,
            RelationlessnessHandler,
            StartTraceHandler,
            AdvanceTraceHandler,
            ContinueTraceHandler,
            TraceStepHandler,
            HeadTraceHandler,
            TailTraceHandler,
            BindTraceHandler,
            RenewTraceHandler,
            RestepTraceHandler,
            SeedFirstContextHandler,
            ExtendFirstContextHandler,
            ExtendContextHandler,
            RenewContextHandler,
            RetraceContextHandler,
            AssignTraceActHandler,
            ContextualizeTraceHandler,
            CompleteTraceHandler,
            SeedObservationHandler,
            SeedValueHandler,
            SeedTermHandler,
            RecognizeValueHandler,
            RecognizeObservationHandler,
            RecognizeContextHandler,
            WitnessJudgementHandler,
            WitnessObservationHandler,
            WitnessValueHandler,
            EvaluateObservationHandler,
            EvaluateJudgementHandler,
            EvaluateObservationEquivalenceHandler,
            RecognizeSyntaxHandler,
            NormalizeSyntaxHandler,
            SoundSyntaxHandler,
            JudgeTypingHandler,
            NormalizeObservationActHandler,
            NormalizeStronglyHandler,
            PhysicsStateHandler,
            FlowMeasureStepHandler,
            BuildProfileTowerHandler,
            BuildNestedProfileTowerHandler,
            BuildCompositeProfileTowerHandler,
            CalculateProfileSyntaxHandler,
            CalculateCompositeProfileSyntaxHandler,
            BoxModalityHandler,
            DiamondModalityHandler,
            DirectedTransportHandler,
            DirectedEquivalenceHandler,
            HarmonicModeHandler,
            SpectrumSeedHandler,
            FlowNucleusHandler,
            CommuteFlowAndNucleusHandler,
            CommuteShuffleFlowAndNucleusHandler,
            BinderSeedHandler,
            BinderApplicationHandler,
            BinderTransportHandler,
            BindTermHandler,
            BaselineConvergenceHandler,
            BaselineLimitHandler,
            ReachActHandler,
            BuildContextHandler,
            ParametricRuntimeHandler,
            GovernRegimeHandler,
            SeedJudgementTriadHandler,
            TraceJudgementTriadHandler,
        ]:
            self.register_class(handler_class)


def register_handler(handler_class: Type[ActHandler]) -> Type[ActHandler]:
    """Decorator to register a handler class."""
    HandlerRegistry.get_instance().register_class(handler_class)
    return handler_class
