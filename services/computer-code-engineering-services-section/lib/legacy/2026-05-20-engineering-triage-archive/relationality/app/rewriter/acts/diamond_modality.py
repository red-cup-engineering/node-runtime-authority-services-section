from __future__ import annotations

from datetime import datetime

from app.rewriter.handlers import ActHandler, ExecutionContext, HandlerResult
from app.schemas.modality import StateGraph, PredicateVector, ModalEvaluation


class DiamondModalityHandler(ActHandler):
    """Per-act handler for ``diamond-modality``."""

    acts = ["diamond-modality"]

    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        trace_id = str(context.trace_id)
        now = datetime.utcnow().isoformat()

        graph_in = context.get_input("graph")
        base_in = context.get_input("base")

        if graph_in is None or base_in is None:
            return HandlerResult.fail("Missing required inputs: graph, base")

        graph = StateGraph.model_validate(graph_in)
        base = PredicateVector.model_validate(base_in)

        # Compute ◇P at each node: true iff some successor satisfies P.
        diamond_values: dict[str, bool] = {}
        for node in graph.nodes:
            succs = graph.edges.get(node, [])
            if not succs:
                diamond_values[node] = False
            else:
                diamond_values[node] = any(base.values.get(s, False) for s in succs)

        evaluation = ModalEvaluation(
            graph=graph,
            base=base,
            box=PredicateVector(values={}),  # untouched by this act
            diamond=PredicateVector(values=diamond_values),
        )

        persisted_id = await context.persist_recognition(
            {
                "type": "modal_evaluation",
                "act": act,
                "acts": [act],
                "trace_id": trace_id,
                "created_at": now,
                "evaluation": evaluation.model_dump(),
                "mode": "diamond",
            }
        )

        return HandlerResult.ok(
            outputs={"evaluation": evaluation.model_dump()},
            recognitions_created=[persisted_id],
            metadata={"act": act, "mode": "diamond"},
        )
