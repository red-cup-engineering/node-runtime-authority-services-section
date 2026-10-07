from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult


class FlowObservationHandler(ActHandler):
    """Per-act handler for ``flow-observation``.

    This act records how a closed observation trace flows through an
    evaluation context. At the current implementation level, we treat
    this as annotating an observation with a flow step, without
    changing its payload semantics.

    Inputs:
      - observation: dict (required) – an observation recognition
      - context: dict (optional) – an evaluation/context record
    """

    acts = ["flow-observation"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        observation = context.get_input("observation")
        if observation is None:
            return HandlerResult.fail("Missing required input: observation")

        eval_context = context.get_input("context")
        now = datetime.utcnow().isoformat()

        flowed = dict(observation)
        flow_info = {
            "flowed_at": now,
            "act": act,
        }
        if eval_context is not None:
            flow_info["context"] = eval_context

        metadata = dict(flowed.get("metadata", {}))
        metadata.setdefault("flow_observation", [])
        metadata["flow_observation"].append(flow_info)
        flowed["metadata"] = metadata

        recognition = {
            "id": flowed.get("id", str(uuid4())),
            "type": flowed.get("type", "observation"),
            "title": flowed.get("title", "Flowed observation"),
            "act": act,
            "acts": [act],
            "observation": flowed,
            "flowed_at": now,
            "trace_id": flowed.get("trace_id", str(context.trace_id)),
        }

        persisted_id = await context.persist_recognition(recognition)

        return HandlerResult.ok(
            outputs={
                "observation": flowed,
                "flow": flow_info,
                "flow_recognition": recognition,
            },
            recognitions_created=[persisted_id],
            metadata={"act": act},
        )

