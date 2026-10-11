from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.schemas.fibers.act_tree_node import ActTreeNode
from app.schemas.fibers.recognition_fiber import RecognitionFiber, RecognitionRole
from app.schemas.fibers.payloads.ground_cap_recognition import CapRecognitionPayload
from app.schemas.fibers.registry import register_fiber
from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class CapRecognitionHandler(ActHandler):
    """Per-act handler for ``cap-recognition``.

    Records a maximal recognition that witnesses a collection of traces.
    At the act level this reflects the composition
    `(Recognition CompleteTrace)`.

    Inputs:
      - traces: list[dict or str] (optional) – trace payloads or IDs.
    """

    acts = ["cap-recognition"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        traces: List[Any] = context.get_input("traces", []) or []

        # Interpret traces as recognition references when possible.
        trace_refs = []
        for t in traces:
            if isinstance(t, dict) and "id" in t:
                trace_refs.append(
                    {
                        "id": str(t["id"]),
                        "acts": t.get("acts"),
                    }
                )
        payload = CapRecognitionPayload(traces=trace_refs, traces_count=len(traces))

        fibre = RecognitionFiber(
            role=RecognitionRole.CONTEXT,
            acts=[act],
            tree=[
                ActTreeNode(act="recognition", children=[]),
                ActTreeNode(act="complete-trace", children=[]),
            ],
            payload=payload.model_dump(),
        )

        recognition: Dict[str, Any] = fibre.model_dump(mode="json")
        recognition["type"] = "context"
        recognition["title"] = "Cap recognition (⊤)"
        recognition["act"] = act
        recognition["arity"] = 2
        recognition["kind"] = "cap"
        recognition["traces"] = traces
        recognition["traces_count"] = len(traces)
        recognition["capped_at"] = datetime.utcnow().isoformat()
        recognition["trace_id"] = str(context.trace_id)

        register_fiber(fibre)

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "recognition_id": str(persisted_id),
                "cap_recognition": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act, "traces_count": len(traces)},
        )
