from __future__ import annotations

from typing import Any, Dict
from datetime import datetime
from uuid import uuid4

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.implication_witness import ImplicationWitness
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class IncludeRecognitionHandler(ActHandler):
    """Per-act handler for ``include-recognition``.

    Records that one recognition is included in another.

    Inputs:
      - inner: any (required)
      - outer: any (required)
    """

    acts = ["include-recognition"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        inner = context.get_input("inner")
        outer = context.get_input("outer")

        if inner is None or outer is None:
            return HandlerResult.fail("Missing required inputs: inner, outer")

        now = datetime.utcnow().isoformat()

        inclusion: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": "context",
            "title": "Include recognition",
            "act": act,
            "acts": [act],
            "inner": inner,
            "outer": outer,
            "recorded_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(inclusion)

        return HandlerResult.ok(
            outputs={"inclusion": inclusion},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )


class ExcludeRecognitionHandler(ActHandler):
    """Per-act handler for ``exclude-recognition``.

    Records that two recognitions are orthogonal / mutually excluding.

    Inputs:
      - left: any (required)
      - right: any (required)
    """

    acts = ["exclude-recognition"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        left = context.get_input("left")
        right = context.get_input("right")

        if left is None or right is None:
            return HandlerResult.fail("Missing required inputs: left, right")

        now = datetime.utcnow().isoformat()

        exclusion: Dict[str, Any] = {
            "id": str(uuid4()),
            "type": "context",
            "title": "Exclude recognition",
            "act": act,
            "acts": [act],
            "left": left,
            "right": right,
            "orthogonal": True,
            "recorded_at": now,
            "trace_id": str(context.trace_id),
        }

        persisted_id = await context.persist_recognition(exclusion)

        return HandlerResult.ok(
            outputs={"exclusion": exclusion},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )


class ImplyRecognitionHandler(ActHandler):
    """Per-act handler for ``imply-recognition``.

    Records that one recognition implies another by capturing a
    directional relationship between their act footprints.

    Inputs:
      - premise: dict (required) – recognition-like payload
      - conclusion: dict (required) – recognition-like payload
    """

    acts = ["imply-recognition"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        premise = context.get_input("premise")
        conclusion = context.get_input("conclusion")

        if premise is None or conclusion is None:
            return HandlerResult.fail("Missing required inputs: premise, conclusion")

        if not isinstance(premise, dict) or not isinstance(conclusion, dict):
            return HandlerResult.fail("premise and conclusion must be dict payloads")

        premise_acts = set(premise.get("acts", []))
        conclusion_acts = set(conclusion.get("acts", []))
        added_acts = sorted(conclusion_acts - premise_acts)

        payload = ImplicationWitness(
            premise_id=str(premise.get("id", "")),
            conclusion_id=str(conclusion.get("id", "")),
            added_acts=added_acts,
        )

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[ActTreeNode(act=act, children=[])],
            payload=payload.model_dump(),
        )
        # Use JSON mode so UUIDs are rendered as strings for persistence.
        implication: Dict[str, Any] = fibre.model_dump(mode="json")
        implication["act"] = act

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(implication)

        return HandlerResult.ok(
            outputs={"implication": implication},
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )
